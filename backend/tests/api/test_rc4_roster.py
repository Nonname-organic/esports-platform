"""RC4 の規則の API テスト（設計: docs/release/RC4_FINAL_DESIGN.md）。

招待と本人の承諾（D6・D7）、名簿（D10・D25）、開始での出場登録の固定（Q04・D14）、開始を経ない
不戦勝（Q04）、旧方式（legacy）の大会の制限（Q01・Q18）、ワーカー（Q01・Q17）、交代とマップごとの
実出場（C1・Q09）、出場の異議（C5）、管理者の訂正（Q15）、個人の帰属（S8-2・Q11・Q12・D9）。
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import issue_tokens
from app.models.enums import MatchStatus, MemberRole, RegistrationStatus, TournamentStatus, UserRole
from app.models.match import Match, MatchGame, MatchResult, PlayerMatchStats
from app.models.roster import AdminCorrection, MatchLineupEntry, ParticipationDispute, TournamentRosterEntry
from app.models.team import TeamMember
from app.models.tournament_report import TournamentReport
from tests import factories as f

API = "/api/v1"


def _now():
    return datetime.now(timezone.utc)


def _h(user) -> dict:
    return {"Authorization": f"Bearer {issue_tokens(user)[0]}"}


async def _person(db, name: str):
    """ユーザーと選手のプロフィールを 1 組作る。"""
    user = await f.make_user(db)
    return user, await f.make_player(db, user=user, in_game_name=name)


def _row(player, team_id, kills=1) -> dict:
    return {"player_id": str(player.id), "team_id": str(team_id), "kills": kills}


def _stats(rows) -> dict:
    return {"team1_score": 13, "team2_score": 7, "player_stats": rows}


# ── 招待と本人の承諾（第 1 段）──────────────────────────────────────────────

class TestInvitations:
    @pytest.mark.asyncio
    async def test_メンバーを直接足す経路は410(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        res = await client.post(f"{API}/teams/{team.id}/members", headers=_h(owner), json={})
        assert res.status_code == 410, res.text

    @pytest.mark.asyncio
    async def test_招待は本人が承認したときだけ所属になる(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        invitee, _player = await _person(db, "Invitee")
        stranger = await f.make_user(db)

        url = f"{API}/teams/{team.id}/invitations"
        assert (await client.post(url, headers=_h(stranger), json={"username": invitee.username})).status_code == 403
        res = await client.post(url, headers=_h(owner), json={"username": invitee.username})
        assert res.status_code == 201, res.text
        inv_id = res.json()["data"]["id"]
        listed = (await client.get(url, headers=_h(owner))).json()["data"]
        assert [(i["id"], i["invitee_username"], i["status"]) for i in listed] == [(inv_id, invitee.username, "pending")]
        assert (await client.get(url, headers=_h(stranger))).status_code == 403

        inbox = (await client.get(f"{API}/me/team-invitations", headers=_h(invitee))).json()["data"]
        assert [i["id"] for i in inbox] == [inv_id]
        # 本人のほかは返事ができない（オーナーも代われない）
        for other in (stranger, owner):
            res = await client.post(f"{API}/team-invitations/{inv_id}/accept", headers=_h(other))
            assert res.status_code == 403, res.text
        assert (await client.post(f"{API}/team-invitations/{inv_id}/accept", headers=_h(invitee))).status_code == 200

        mine = (await client.get(f"{API}/me/memberships", headers=_h(invitee))).json()["data"]["items"]
        assert [(m["team_id"], m["consent"], m["formal"]) for m in mine] == [(str(team.id), "invitation", True)]
        res = await client.post(url, headers=_h(owner), json={"username": invitee.username})
        assert res.status_code == 409, res.text  # 既にメンバー

    @pytest.mark.asyncio
    async def test_断った招待は7日たつまで送り直せない(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        invitee, _player = await _person(db, "Decliner")
        url = f"{API}/teams/{team.id}/invitations"
        inv_id = (await client.post(url, headers=_h(owner), json={"username": invitee.username})).json()["data"]["id"]
        assert (await client.post(f"{API}/team-invitations/{inv_id}/decline", headers=_h(invitee))).status_code == 204
        res = await client.post(url, headers=_h(owner), json={"username": invitee.username})
        assert res.status_code == 409, res.text

    @pytest.mark.asyncio
    async def test_移行前の所属は本人が確認か否認をして_否認は管理者が理由つきで戻せる(
            self, client: AsyncClient, db, admin_user):
        owner = await f.make_user(db)
        user, player = await _person(db, "Legacy member")
        a = await f.make_team(db, owner=owner, name="RC4 A")
        b = await f.make_team(db, owner=owner, name="RC4 B")
        ma = await f.add_member(db, team=a, player=player, consent="unconfirmed")
        mb = await f.add_member(db, team=b, player=player, consent="unconfirmed")

        assert (await client.post(f"{API}/me/memberships/{ma.id}/confirm", headers=_h(owner))).status_code == 403
        res = await client.post(f"{API}/me/memberships/{ma.id}/confirm", headers=_h(user))
        assert res.status_code == 200 and res.json()["data"]["consent"] == "confirmed", res.text
        res = await client.post(f"{API}/me/memberships/{mb.id}/reject", headers=_h(user))
        assert res.status_code == 200 and res.json()["data"]["consent"] == "rejected", res.text
        await db.refresh(mb)
        assert mb.left_at is not None and mb.rejected_at is not None

        url = f"{API}/admin/memberships/{mb.id}/unreject"
        assert (await client.post(url, headers=_h(user), json={"reason": "x"})).status_code == 403
        res = await client.post(url, headers=_h(admin_user), json={"reason": "本人から誤操作の連絡"})
        assert res.status_code == 200 and res.json()["data"]["consent"] == "unconfirmed", res.text
        assert await db.scalar(select(AdminCorrection.kind).where(AdminCorrection.membership_id == mb.id)) \
            == "membership_unreject"


# ── 名簿（第 2 段）────────────────────────────────────────────────────────

async def _roster_world(db, *, lineup_size=1, roster_max=2, consent="invitation", mode="roster"):
    org = await f.make_user(db, role=UserRole.ORGANIZER)
    make = f.make_legacy_tournament if mode == "legacy" else f.make_tournament
    tour = await make(db, organizer=org, status=TournamentStatus.REGISTRATION_OPEN,
                      lineup_size=lineup_size, roster_max=roster_max)
    owner = await f.make_user(db)
    team = await f.make_team(db, owner=owner, name=f"Roster {tour.id.hex[:4]}")
    user, player = await _person(db, "Roster player")
    await f.add_member(db, team=team, player=player, consent=consent)
    reg = await f.register_team(db, tournament=tour, team=team, status=RegistrationStatus.PENDING)
    url = f"{API}/tournaments/{tour.id}/registrations/{reg.id}/roster"
    return {"org": org, "tour": tour, "owner": owner, "team": team, "user": user, "player": player,
            "reg": reg, "url": url}


class TestRoster:
    @pytest.mark.asyncio
    async def test_チームが名簿に載せ_本人が承認する(self, client: AsyncClient, db):
        w = await _roster_world(db)
        stranger = await f.make_user(db)
        res = await client.post(w["url"], headers=_h(stranger), json={"player_id": str(w["player"].id)})
        assert res.status_code == 403, res.text
        # 参加登録が承認待ち（pending）でも名簿は作れる（D25）
        res = await client.post(w["url"], headers=_h(w["owner"]), json={"player_id": str(w["player"].id)})
        assert res.status_code == 201 and res.json()["data"]["status"] == "invited", res.text
        entry_id = res.json()["data"]["id"]
        mine = (await client.get(f"{API}/tournaments/{w['tour'].id}/my-registration", headers=_h(w["owner"]))).json()["data"]
        assert (mine["registration_id"], mine["can_manage_roster"]) == (str(w["reg"].id), True)

        assert (await client.get(w["url"], headers=_h(stranger))).status_code == 403  # D18
        assert len((await client.get(w["url"], headers=_h(w["owner"]))).json()["data"]) == 1
        assert (await client.post(f"{API}/roster-entries/{entry_id}/accept", headers=_h(w["owner"]))).status_code == 403
        res = await client.post(f"{API}/roster-entries/{entry_id}/accept", headers=_h(w["user"]))
        assert res.status_code == 200 and res.json()["data"]["status"] == "accepted", res.text

        # 名簿の固定の後は本人も取り下げられない
        w["tour"].roster_locked_at = _now()
        await db.flush()
        res = await client.post(f"{API}/roster-entries/{entry_id}/withdraw", headers=_h(w["user"]))
        assert res.status_code == 409, res.text

    @pytest.mark.asyncio
    async def test_本人未確認の所属は名簿に載せられない(self, client: AsyncClient, db):
        w = await _roster_world(db, consent="unconfirmed")
        res = await client.post(w["url"], headers=_h(w["owner"]), json={"player_id": str(w["player"].id)})
        assert res.status_code == 400, res.text

    @pytest.mark.asyncio
    async def test_同じ大会で2チームの名簿には載らず_上限を超えられない(self, client: AsyncClient, db):
        w = await _roster_world(db, roster_max=2)
        other = await f.make_team(db, owner=w["owner"], name=f"Roster other {w['tour'].id.hex[:4]}")
        await f.add_member(db, team=other, player=w["player"])
        reg2 = await f.register_team(db, tournament=w["tour"], team=other)
        assert (await client.post(w["url"], headers=_h(w["owner"]),
                                  json={"player_id": str(w["player"].id)})).status_code == 201
        res = await client.post(f"{API}/tournaments/{w['tour'].id}/registrations/{reg2.id}/roster",
                                headers=_h(w["owner"]), json={"player_id": str(w["player"].id)})
        assert res.status_code == 409, res.text  # D10

        for i in range(2):
            _u, p = await _person(db, f"Extra {i}")
            await f.add_member(db, team=w["team"], player=p)
            res = await client.post(w["url"], headers=_h(w["owner"]), json={"player_id": str(p.id)})
            assert res.status_code == (201 if i == 0 else 409), res.text

    @pytest.mark.asyncio
    async def test_旧方式の大会は名簿を作れず_主催者が未開始のうちに切り替える(self, client: AsyncClient, db):
        w = await _roster_world(db, mode="legacy")
        res = await client.post(w["url"], headers=_h(w["owner"]), json={"player_id": str(w["player"].id)})
        assert res.status_code == 409, res.text
        mode_url = f"{API}/tournaments/{w['tour'].id}/roster-mode"
        assert (await client.post(mode_url, headers=_h(w["owner"]))).status_code == 403
        res = await client.post(mode_url, headers=_h(w["org"]))
        assert res.status_code == 200 and res.json()["data"]["roster_mode"] == "roster", res.text
        assert (await client.post(mode_url, headers=_h(w["org"]))).status_code == 409  # 一方向
        res = await client.post(w["url"], headers=_h(w["owner"]), json={"player_id": str(w["player"].id)})
        assert res.status_code == 201, res.text


# ── 試合: 開始での固定・不戦勝・旧方式の制限 ─────────────────────────────────

async def _match_world(db, *, lineup_size=1, players=(1, 1), mode="roster", status=TournamentStatus.ONGOING):
    """2 チームの予定の試合。players はチームごとの承認済みの名簿の選手の数。"""
    org = await f.make_user(db, role=UserRole.ORGANIZER)
    make = f.make_legacy_tournament if mode == "legacy" else f.make_tournament
    tour = await make(db, organizer=org, status=status, lineup_size=lineup_size, roster_max=lineup_size + 2)
    teams, owners, squads = [], [], []
    for i, n in enumerate(players):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner, name=f"RC4 M{i} {tour.id.hex[:4]}", tag=f"M{i}")
        await f.register_team(db, tournament=tour, team=team)
        squad = []
        for k in range(n):
            user = await f.make_user(db)
            squad.append((user, await f.roster_player(db, tournament=tour, team=team, name=f"M{i}-{k}", user=user)))
        teams.append(team)
        owners.append(owner)
        squads.append(squad)
    match = Match(tournament_id=tour.id, round_number=1, match_number=1, status=MatchStatus.SCHEDULED,
                  team1_id=teams[0].id, team2_id=teams[1].id)
    db.add(match)
    await db.flush()
    return {"org": org, "tour": tour, "teams": teams, "owners": owners, "squads": squads, "match": match}


class TestStartLocksLineups:
    @pytest.mark.asyncio
    async def test_スターターが足りないと理由が要り_返事の無い名簿の招待は期限切れになる(self, client: AsyncClient, db):
        w = await _match_world(db, lineup_size=2, players=(1, 2))
        _u, waiting = await _person(db, "No answer")
        await f.add_member(db, team=w["teams"][0], player=waiting)
        await f.add_roster(db, tournament=w["tour"], team=w["teams"][0], player=waiting, status="invited")
        url = f"{API}/matches/{w['match'].id}/start"
        res = await client.patch(url, headers=_h(w["org"]))
        assert res.status_code == 400, res.text  # D14
        res = await client.patch(url, headers=_h(w["org"]), json={"reason": "1 人が回線の不調で欠場"})
        assert res.status_code == 204, res.text

        await db.refresh(w["match"])
        await db.refresh(w["tour"])
        assert w["match"].lineup_locked_at is not None and w["tour"].roster_locked_at is not None
        lineup = (await client.get(f"{API}/matches/{w['match'].id}/lineups")).json()["data"]
        starters = {(e["team_id"], e["slot"]) for e in lineup["entries"]}
        assert starters == {(str(w["teams"][0].id), "starter"), (str(w["teams"][1].id), "starter")}
        assert len(lineup["entries"]) == 3
        status = await db.scalar(select(TournamentRosterEntry.status).where(TournamentRosterEntry.player_id == waiting.id))
        assert status == "expired"

    @pytest.mark.asyncio
    async def test_スターターのいないチームがあると開始できない(self, client: AsyncClient, db):
        w = await _match_world(db, players=(1, 0))
        res = await client.patch(f"{API}/matches/{w['match'].id}/start", headers=_h(w["org"]), json={"reason": "x"})
        assert res.status_code == 409, res.text
        await db.refresh(w["match"])
        assert w["match"].status == MatchStatus.SCHEDULED

    @pytest.mark.asyncio
    async def test_固定の後はチームは出場登録を変えられず_主催者は理由つきで変える(self, client: AsyncClient, db):
        w = await _match_world(db, players=(2, 1))
        (_u1, p1), (_u2, p2) = w["squads"][0]
        team1 = w["teams"][0]
        url = f"{API}/matches/{w['match'].id}/lineups/{team1.id}"
        body = {"starters": [str(p2.id)], "bench": [str(p1.id)]}
        assert (await client.put(url, headers=_h(w["owners"][0]), json=body)).status_code == 200  # 開始の前
        assert (await client.patch(f"{API}/matches/{w['match'].id}/start", headers=_h(w["org"]))).status_code == 204

        body = {"starters": [str(p1.id)], "bench": [str(p2.id)]}
        assert (await client.put(url, headers=_h(w["owners"][0]), json=body)).status_code == 409
        assert (await client.put(url, headers=_h(w["org"]), json=body)).status_code == 400
        res = await client.put(url, headers=_h(w["org"]), json={**body, "reason": "登録の誤り"})
        assert res.status_code == 200, res.text
        starters = [e["player_id"] for e in res.json()["data"]["entries"]
                    if e["team_id"] == str(team1.id) and e["slot"] == "starter"]
        assert starters == [str(p1.id)]


class TestForfeitWithoutStart:
    @pytest.mark.asyncio
    async def test_開始せずに不戦勝にして_再開すると予定に戻る(self, client: AsyncClient, db):
        w = await _match_world(db)
        m, team1 = w["match"], w["teams"][0]
        url = f"{API}/matches/{m.id}/forfeit"
        body = {"winner_id": str(team1.id), "reason": "相手チームが集合時刻に来なかった"}
        assert (await client.post(url, headers=_h(w["owners"][0]), json=body)).status_code == 403
        assert (await client.post(url, headers=_h(w["org"]), json=body)).status_code == 204
        await db.refresh(m)
        assert (m.status, m.winner_id, m.started_at, m.lineup_locked_at) == (MatchStatus.COMPLETED, team1.id, None, None)
        assert await db.scalar(select(MatchResult.was_forfeit).where(MatchResult.match_id == m.id)) is True
        assert not await db.scalar(select(MatchLineupEntry.id).where(MatchLineupEntry.match_id == m.id).limit(1))

        assert (await client.post(f"{API}/matches/{m.id}/reopen", headers=_h(w["org"]))).status_code == 204
        await db.refresh(m)
        assert (m.status, m.winner_id) == (MatchStatus.SCHEDULED, None)


class TestLegacyTournaments:
    @pytest.mark.asyncio
    async def test_旧方式の大会は試合を開始できず_開催中にも完了にもできない(self, client: AsyncClient, db):
        w = await _match_world(db, players=(0, 0), mode="legacy", status=TournamentStatus.REGISTRATION_CLOSED)
        assert (await client.patch(f"{API}/matches/{w['match'].id}/start", headers=_h(w["org"]))).status_code == 409
        body = {"winner_id": str(w["teams"][0].id), "reason": "x"}
        assert (await client.post(f"{API}/matches/{w['match'].id}/forfeit", headers=_h(w["org"]), json=body)).status_code == 409
        url = f"{API}/tournaments/{w['tour'].id}/status"
        for status in ("ongoing", "completed"):
            res = await client.patch(url, headers=_h(w["org"]), json={"status": status})
            assert res.status_code == 409, (status, res.text)
        res = await client.patch(f"{API}/tournaments/{w['tour'].id}", headers=_h(w["org"]), json={"status": "ongoing"})
        assert res.status_code in (409, 422), res.text
        await db.refresh(w["tour"])
        assert w["tour"].status == TournamentStatus.REGISTRATION_CLOSED

    @pytest.mark.asyncio
    async def test_始まった試合がある旧方式の大会は切り替えられない(self, client: AsyncClient, db):
        w = await _match_world(db, players=(0, 0), mode="legacy", status=TournamentStatus.CHECK_IN)
        w["match"].status = MatchStatus.COMPLETED
        await db.flush()
        res = await client.post(f"{API}/tournaments/{w['tour'].id}/roster-mode", headers=_h(w["org"]))
        assert res.status_code == 409, res.text
        w["match"].status = MatchStatus.SCHEDULED
        w["tour"].status = TournamentStatus.ONGOING
        await db.flush()
        res = await client.post(f"{API}/tournaments/{w['tour'].id}/roster-mode", headers=_h(w["org"]))
        assert res.status_code == 409, res.text


class TestStatusWorker:
    @pytest.mark.asyncio
    async def test_旧方式の大会は開催中にせず_受付の終了は続け_1件の失敗で他を戻さない(self, db, monkeypatch):
        import app.services.registration_lottery as lottery
        import app.services.roster as roster
        from app.workers import sqs_consumer

        async def no_redis():
            return None

        async def no_lottery(*_a, **_k):
            return 0

        monkeypatch.setattr(sqs_consumer, "get_redis", no_redis)
        monkeypatch.setattr(lottery, "run_registration_lottery", no_lottery)
        org = await f.make_user(db, role=UserRole.ORGANIZER)
        now = _now()
        closed = TournamentStatus.REGISTRATION_CLOSED
        legacy_start = await f.make_legacy_tournament(db, organizer=org, status=closed)
        legacy_close = await f.make_legacy_tournament(db, organizer=org, status=TournamentStatus.REGISTRATION_OPEN)
        broken = await f.make_tournament(db, organizer=org, status=closed)
        fine = await f.make_tournament(db, organizer=org, status=closed)
        for t in (legacy_start, broken, fine):  # 開始の時刻を過ぎた
            t.start_at, t.end_at = now - timedelta(hours=1), now + timedelta(days=1)
        legacy_close.registration_end_at = now - timedelta(hours=1)  # 受付の終了の時刻を過ぎた
        await db.flush()

        real_lock = roster.lock_roster
        broken_id = broken.id  # 失敗させた大会は、戻した後に期限切れになる（属性を読み直すと I/O）

        async def lock_or_fail(session, t):
            if t.id == broken_id:
                raise RuntimeError("boom")
            await real_lock(session, t)

        monkeypatch.setattr(roster, "lock_roster", lock_or_fail)
        changed = await sqs_consumer.apply_tournament_status_transitions(db, now)
        assert changed == 2
        for t in (legacy_start, legacy_close, broken, fine):
            await db.refresh(t)
        assert legacy_start.status == TournamentStatus.REGISTRATION_CLOSED  # Q01: 開催中にしない
        assert legacy_close.status == TournamentStatus.REGISTRATION_CLOSED  # 受付の終了は続ける
        assert broken.status == TournamentStatus.REGISTRATION_CLOSED  # 失敗した大会だけ戻る（Q17）
        assert fine.status == TournamentStatus.ONGOING and fine.roster_locked_at is not None


# ── 交代・マップごとの実出場・異議・管理者の訂正 ─────────────────────────────

async def _started(client, db):
    """出場人数 1。チーム 1 は 2 人（スターターと控え）、チーム 2 は 1 人。開始済み。"""
    w = await _match_world(db, players=(2, 1))
    res = await client.patch(f"{API}/matches/{w['match'].id}/start", headers=_h(w["org"]))
    assert res.status_code == 204, res.text
    (w["u1"], w["p1"]), (w["u2"], w["p2"]) = w["squads"][0]
    (w["u3"], w["q1"]), = w["squads"][1]
    return w


class TestSubstitutions:
    @pytest.mark.asyncio
    async def test_マップの間の交代で_そのマップの成績を書ける選手が入れ替わる(self, client: AsyncClient, db):
        w = await _started(client, db)
        m, t1, t2 = w["match"], w["teams"][0].id, w["teams"][1].id
        game = lambda n: f"{API}/matches/{m.id}/games/{n}/player-stats"  # noqa: E731
        assert (await client.post(game(1), headers=_h(w["org"]),
                                  json=_stats([_row(w["p1"], t1), _row(w["q1"], t2)]))).status_code == 204
        res = await client.post(game(1), headers=_h(w["org"]), json=_stats([_row(w["p2"], t1)]))
        assert res.status_code == 400, res.text  # 控えはマップ 1 に出ていない

        sub_url = f"{API}/matches/{m.id}/games/2/substitutions"
        body = {"team_id": str(t1), "kind": "between_maps", "out_player_id": str(w["p1"].id),
                "in_player_id": str(w["p2"].id)}
        assert (await client.post(sub_url, headers=_h(w["org"]), json=body)).status_code == 400  # 理由が要る
        res = await client.post(sub_url, headers=_h(w["org"]), json={**body, "reason": "体調不良"})
        assert res.status_code == 201 and res.json()["data"]["status"] == "approved", res.text

        assert (await client.post(game(2), headers=_h(w["org"]),
                                  json=_stats([_row(w["p2"], t1), _row(w["q1"], t2)]))).status_code == 204
        res = await client.post(game(2), headers=_h(w["org"]), json=_stats([_row(w["p1"], t1)]))
        assert res.status_code == 400, res.text
        lineup = (await client.get(f"{API}/matches/{m.id}/lineups")).json()["data"]
        p2_entry = next(e["id"] for e in lineup["entries"] if e["player_id"] == str(w["p2"].id))
        assert lineup["participants_by_game"]["2"][str(t1)] == [str(p2_entry)]

    @pytest.mark.asyncio
    async def test_チームの交代の申請は主催者が承認し_途中の交代には理由が要る(self, client: AsyncClient, db):
        w = await _started(client, db)
        m, t1 = w["match"], w["teams"][0].id
        sub_url = f"{API}/matches/{m.id}/games/1/substitutions"
        body = {"team_id": str(t1), "kind": "between_maps", "out_player_id": str(w["p1"].id),
                "in_player_id": str(w["p2"].id)}
        res = await client.post(sub_url, headers=_h(w["owners"][0]), json=body)
        assert res.status_code == 201 and res.json()["data"]["status"] == "requested", res.text
        sub_id = res.json()["data"]["id"]
        decide = f"{API}/matches/{m.id}/substitutions/{sub_id}/approve"
        assert (await client.post(decide, headers=_h(w["owners"][0]))).status_code == 403
        res = await client.post(decide, headers=_h(w["org"]))
        assert res.status_code == 200 and res.json()["data"]["status"] == "approved", res.text

        mid = {"team_id": str(t1), "kind": "mid_map", "out_player_id": str(w["p2"].id),
               "in_player_id": str(w["p1"].id)}
        assert (await client.post(f"{API}/matches/{m.id}/games/2/substitutions", headers=_h(w["owners"][0]),
                                  json=mid)).status_code == 400


class TestDisputesAndCorrections:
    @pytest.mark.asyncio
    async def test_出場登録の本人だけが異議を出し_管理者が裁定する(self, client: AsyncClient, db, admin_user):
        w = await _started(client, db)
        url = f"{API}/me/participation-disputes"
        body = {"match_id": str(w["match"].id), "reason": "この試合には出ていない"}
        outsider, _p = await _person(db, "Outsider")
        assert (await client.post(url, headers=_h(outsider), json=body)).status_code == 403
        res = await client.post(url, headers=_h(w["u2"]), json=body)  # 控え（出場登録には載っている）
        assert res.status_code == 201, res.text
        assert (await client.post(url, headers=_h(w["u2"]), json=body)).status_code == 409
        dispute_id = res.json()["data"]["id"]

        assert (await client.get(f"{API}/admin/participation-disputes", headers=_h(w["org"]))).status_code == 403
        listed = (await client.get(f"{API}/admin/participation-disputes?status=open", headers=_h(admin_user))).json()
        assert [d["id"] for d in listed["data"]] == [dispute_id]
        resolve = f"{API}/admin/participation-disputes/{dispute_id}"
        assert (await client.patch(resolve, headers=_h(w["org"]), json={"status": "upheld"})).status_code == 403
        res = await client.patch(resolve, headers=_h(admin_user), json={"status": "upheld", "note": "確認した"})
        assert res.status_code == 200 and res.json()["data"]["status"] == "upheld", res.text

    @pytest.mark.asyncio
    async def test_完了した大会は管理者だけが理由つきで直せる(self, client: AsyncClient, db, admin_user):
        w = await _started(client, db)
        m, t1 = w["match"], w["teams"][0].id
        url = f"{API}/matches/{m.id}/games/1/player-stats"
        assert (await client.post(url, headers=_h(w["org"]), json=_stats([_row(w["p1"], t1)]))).status_code == 204
        w["tour"].status = TournamentStatus.COMPLETED
        await db.flush()

        assert (await client.post(url, headers=_h(w["org"]), json=_stats([_row(w["p1"], t1, 9)]))).status_code == 409
        assert (await client.post(url, headers=_h(admin_user), json=_stats([_row(w["p1"], t1, 9)]))).status_code == 400
        res = await client.post(url, headers=_h(admin_user),
                                json={**_stats([_row(w["p1"], t1, 9)]), "correction_reason": "スコアボードの読み違い"})
        assert res.status_code == 204, res.text
        kills = await db.scalar(select(PlayerMatchStats.kills).join(MatchGame).where(MatchGame.match_id == m.id))
        assert kills == 9
        assert await db.scalar(select(AdminCorrection.kind).where(AdminCorrection.match_id == m.id)) == "stats_change"
        # 主催者は完了した大会の試合を再開できない。管理者は理由が要る
        m.status, m.winner_id, m.ended_at = MatchStatus.COMPLETED, t1, _now()
        await db.flush()
        reopen = f"{API}/matches/{m.id}/reopen"
        assert (await client.post(reopen, headers=_h(w["org"]), json={"reason": "x"})).status_code == 409
        assert (await client.post(reopen, headers=_h(admin_user))).status_code == 400


# ── 個人の帰属（S8-2）─────────────────────────────────────────────────────

def _report(champion, runner_up) -> dict:
    return {"champion": {"team_id": str(champion.id), "team_name": champion.name},
            "runner_up": {"team_id": str(runner_up.id), "team_name": runner_up.name},
            "standings": [{"team_id": str(champion.id), "wins": 1, "losses": 0},
                          {"team_id": str(runner_up.id), "wins": 0, "losses": 1}]}


class TestAttribution:
    @pytest.mark.asyncio
    async def test_名簿の大会は1マップ以上出た選手だけで_異議が認められると外れる(self, client: AsyncClient, db):
        w = await _started(client, db)
        m, t1, t2 = w["match"], w["teams"][0], w["teams"][1]
        res = await client.post(f"{API}/matches/{m.id}/games/1/player-stats", headers=_h(w["org"]),
                                json=_stats([_row(w["p1"], t1.id), _row(w["q1"], t2.id)]))
        assert res.status_code == 204, res.text
        m.status, m.winner_id, m.ended_at = MatchStatus.COMPLETED, t1.id, _now()
        w["tour"].status, w["tour"].end_at = TournamentStatus.COMPLETED, _now()
        db.add(TournamentReport(tournament_id=w["tour"].id, data=_report(t1, t2)))
        await db.flush()

        async def history(player):
            res = await client.get(f"{API}/players/{player.id}/history")
            assert res.status_code == 200, res.text
            return [(h["tournament_id"], h["placement"]) for h in res.json()["data"]]

        assert await history(w["p1"]) == [(str(w["tour"].id), "champion")]
        assert await history(w["q1"]) == [(str(w["tour"].id), "runner_up")]
        assert await history(w["p2"]) == []  # 控えで出ていない（Q11）

        db.add(ParticipationDispute(match_id=m.id, player_id=w["p1"].id, reason="出ていない", status="upheld",
                                    resolved_at=_now()))
        await db.flush()
        assert await history(w["p1"]) == []  # D9・C5

    @pytest.mark.asyncio
    async def test_既存の大会で2チームに当たる選手は良い方の1回だけ数える(self, client: AsyncClient, db):
        org = await f.make_user(db, role=UserRole.ORGANIZER)
        tour = await f.make_legacy_tournament(db, organizer=org, status=TournamentStatus.COMPLETED)
        owner = await f.make_user(db)
        champ = await f.make_team(db, owner=owner, name="RC4 Champ")
        second = await f.make_team(db, owner=owner, name="RC4 Second")
        _u, player = await _person(db, "Two teams")
        for team in (second, champ):
            await f.register_team(db, tournament=tour, team=team)
            member = await f.add_member(db, team=team, player=player)
            member.joined_at = _now() - timedelta(days=60)
        db.add(TournamentReport(tournament_id=tour.id, data=_report(champ, second)))
        await db.flush()
        res = await client.get(f"{API}/players/{player.id}/history")
        assert [(h["tournament_id"], h["placement"], h["team_name"]) for h in res.json()["data"]] == [
            (str(tour.id), "champion", "RC4 Champ")]
        # 否認した所属は数えない（D4）
        await db.execute(TeamMember.__table__.update().where(TeamMember.team_id == champ.id).values(
            consent="rejected", rejected_at=_now()))
        res = await client.get(f"{API}/players/{player.id}/history")
        assert [(h["placement"], h["team_name"]) for h in res.json()["data"]] == [("runner_up", "RC4 Second")]


# ── 独立レビューの指摘（2026-11-11）の回帰テスト ─────────────────────────────

def test_出場の計算は実在するマップの番号だけを回す():
    """番号の大きさで回数が増えない（大きな番号のマップで API が止まらない）。"""
    from types import SimpleNamespace as N
    from app.services.roster import compute_timeline
    a, b = N(id="a", team_id="t", slot="starter"), N(id="b", team_id="t", slot="bench")
    sub = N(team_id="t", game_number=2, kind="between_maps", out_lineup_entry_id="a", in_lineup_entry_id="b")
    out = compute_timeline([a, b], [sub], {1, 2_000_000_000})
    assert [out[("t", g)]["participants"] for g in (1, 2, 2_000_000_000)] == [{"a"}, {"b"}, {"b"}]
    assert len(out) == 3


class TestReviewFindings:
    @pytest.mark.asyncio
    async def test_マップの番号は1から9まで(self, client: AsyncClient, db):
        w = await _started(client, db)
        for n in (0, 10, 2147483647):
            res = await client.post(f"{API}/matches/{w['match'].id}/games/{n}/score", headers=_h(w["org"]),
                                    json={"team1_score": 1, "team2_score": 0})
            assert res.status_code == 422, (n, res.text)
            res = await client.post(f"{API}/matches/{w['match'].id}/games/{n}/player-stats", headers=_h(w["org"]),
                                    json=_stats([]))
            assert res.status_code == 422, (n, res.text)

    @pytest.mark.asyncio
    async def test_完了した大会の状態と結果は管理者だけが理由つきで変えられる(self, client: AsyncClient, db, admin_user):
        w = await _started(client, db)
        m = w["match"]
        w["tour"].status = TournamentStatus.COMPLETED
        await db.flush()
        status_url = f"{API}/tournaments/{w['tour'].id}/status"
        assert (await client.patch(status_url, headers=_h(w["org"]), json={"status": "ongoing"})).status_code == 409
        result = {"winner_id": str(w["teams"][0].id)}
        assert (await client.post(f"{API}/matches/{m.id}/result", headers=_h(w["org"]), json=result)).status_code == 409
        score = f"{API}/matches/{m.id}/games/1/score"
        body = {"team1_score": 13, "team2_score": 5}
        assert (await client.post(score, headers=_h(w["org"]), json=body)).status_code == 409
        assert (await client.post(score, headers=_h(admin_user), json=body)).status_code == 400
        res = await client.post(score, headers=_h(admin_user), json={**body, "correction_reason": "入力の誤り"})
        assert res.status_code == 204, res.text
        res = await client.post(f"{API}/matches/{m.id}/result", headers=_h(admin_user),
                                json={**result, "correction_reason": "入力の誤り"})
        assert res.status_code == 204, res.text
        kinds = list((await db.execute(select(AdminCorrection.kind).where(AdminCorrection.match_id == m.id))).scalars())
        assert kinds == ["result_change", "result_change"]
        assert (await client.patch(status_url, headers=_h(admin_user), json={"status": "ongoing"})).status_code == 200

    @pytest.mark.asyncio
    async def test_大会の開始の前はチームの確定で試合を開始しない(self, client: AsyncClient, db):
        w = await _match_world(db, status=TournamentStatus.CHECK_IN)
        m, (a, _b) = w["match"], w["teams"]
        url = f"{API}/matches/{m.id}/report"
        assert (await client.post(url, headers=_h(w["owners"][0]), json={"winner_id": str(a.id)})).status_code == 200
        res = await client.post(url, headers=_h(w["owners"][1]), json={"winner_id": str(a.id)})
        assert res.status_code == 400, res.text  # 一致すると確定になるが、開始は主催者が行う
        await db.refresh(m)
        await db.refresh(w["tour"])
        assert m.status == MatchStatus.SCHEDULED and w["tour"].roster_locked_at is None

    @pytest.mark.asyncio
    async def test_開始を経ない不戦勝の試合に出場登録も成績も足せない(self, client: AsyncClient, db):
        w = await _match_world(db)
        m, team1 = w["match"], w["teams"][0]
        (_u1, p1), = w["squads"][0]
        res = await client.post(f"{API}/matches/{m.id}/forfeit", headers=_h(w["org"]),
                                json={"winner_id": str(team1.id), "reason": "相手が来なかった"})
        assert res.status_code == 204, res.text
        res = await client.put(f"{API}/matches/{m.id}/lineups/{team1.id}", headers=_h(w["org"]),
                               json={"starters": [str(p1.id)], "reason": "後から足す"})
        assert res.status_code == 409, res.text
        res = await client.post(f"{API}/matches/{m.id}/games/1/player-stats", headers=_h(w["org"]),
                                json=_stats([_row(p1, team1.id)]))
        assert res.status_code == 400, res.text

    @pytest.mark.asyncio
    async def test_キャプテンでなくなった人は自分の送った招待も取り消せない(self, client: AsyncClient, db):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner)
        cap_user, cap_player = await _person(db, "Captain")
        await f.add_member(db, team=team, player=cap_player, role=MemberRole.CAPTAIN)
        invitee, _p = await _person(db, "Invitee two")
        res = await client.post(f"{API}/teams/{team.id}/invitations", headers=_h(cap_user),
                                json={"username": invitee.username})
        assert res.status_code == 201, res.text
        inv_id = res.json()["data"]["id"]
        await db.execute(TeamMember.__table__.update().where(TeamMember.player_id == cap_player.id)
                         .values(role=MemberRole.PLAYER))
        url = f"{API}/teams/{team.id}/invitations/{inv_id}"
        assert (await client.delete(url, headers=_h(cap_user))).status_code == 403
        assert (await client.delete(url, headers=_h(owner))).status_code == 204

    @pytest.mark.asyncio
    async def test_交代の一覧は主催者だけが見られ_外された出場登録では異議を出せない(self, client: AsyncClient, db):
        w = await _started(client, db)
        m, t1 = w["match"], w["teams"][0].id
        url = f"{API}/matches/{m.id}/substitutions"
        assert (await client.get(url)).status_code in (401, 403)
        assert (await client.get(url, headers=_h(w["owners"][0]))).status_code == 403
        assert (await client.get(url, headers=_h(w["org"]))).status_code == 200
        res = await client.put(f"{API}/matches/{m.id}/lineups/{t1}", headers=_h(w["org"]),
                               json={"starters": [str(w["p1"].id)], "bench": [], "reason": "登録の誤り"})
        assert res.status_code == 200, res.text
        res = await client.post(f"{API}/me/participation-disputes", headers=_h(w["u2"]),
                                json={"match_id": str(m.id), "reason": "出ていない"})
        assert res.status_code == 403, res.text
