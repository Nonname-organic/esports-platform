"""試合の進行まわりの回帰テスト。

- 対戦チームによる結果報告 → 相手チームの確認・異議（主催者の直接確定と両立する）
- 確定済み試合の再開（次の試合へ送ったチームも取り除く）
- Discord Bot の不戦勝（結果登録と勝ち上がりまで行う）
- ダブルエリミネーションの敗者側進行
- 参加の辞退、大会進行状況の表示
- RC2: 再開時の古い報告の解消、選手成績の重複防止、異議の理由の公開範囲、辞退ボタンの表示
"""
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models.discord import DiscordLink
from app.models.enums import (
    GameType,
    MatchStatus,
    MemberRole,
    RegistrationStatus,
    TournamentFormat,
    TournamentStatus,
    UserRole,
)
from app.models.match import Map, Match, MatchGame, MatchResult, PlayerMatchStats
from app.models.match_report import MatchResultReport
from app.models.tournament import TournamentRegistration
from app.schemas.match import GamePlayerStatsUpdate, GameStatsCreate, MatchResultCreate, PlayerStatsCreate
from app.services.match import MatchService
from app.services.tournament import TournamentService
from tests import factories as f


class _Cache:
    async def get(self, *a, **k): return None
    async def set(self, *a, **k): pass
    async def delete(self, *a, **k): pass
    async def delete_pattern(self, *a, **k): return 0
    async def acquire_lock(self, *a, **k): return True
    async def release_lock(self, *a, **k): pass
    async def publish(self, *a, **k): pass


def _h(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id), {'role': user.role.value})}"}


async def _setup(db, *, n=4, fmt=TournamentFormat.SINGLE_ELIMINATION, generate=True):
    org = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=org, status=TournamentStatus.ONGOING, format=fmt)
    owners, teams = [], []
    for i in range(n):
        owner = await f.make_user(db)
        team = await f.make_team(db, owner=owner, name=f"Flow {fmt.value[:4]} {i}", tag=f"F{i}{fmt.value[:2]}")
        await f.register_team(db, tournament=tour, team=team)
        owners.append(owner)
        teams.append(team)
    if generate:
        await TournamentService(db, _Cache()).generate_bracket(tour.id, org)
    return org, tour, owners, teams


async def _round1(db, tour):
    return (await db.execute(
        select(Match).where(Match.tournament_id == tour.id, Match.round_number == 1)
        .order_by(Match.match_number)
    )).scalars().all()


def _owner_of(team_id, owners, teams):
    return owners[[t.id for t in teams].index(team_id)]


class TestResultReport:
    @pytest.mark.asyncio
    async def test_報告して相手が確認すると確定し勝者が次へ進む(self, client: AsyncClient, db):
        _org, tour, owners, teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        a, b = _owner_of(m.team1_id, owners, teams), _owner_of(m.team2_id, owners, teams)

        res = await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(a), json={"winner_id": str(m.team1_id)})
        assert res.json()["data"]["status"] == "pending", res.text
        state = (await client.get(f"/api/v1/matches/{m.id}/report", headers=_h(b))).json()["data"]
        assert state["can_confirm"] and state["can_dispute"] and state["report"]["status"] == "pending"
        # 報告した側は自分で確認できない
        assert (await client.post(f"/api/v1/matches/{m.id}/report/confirm", headers=_h(a))).status_code == 403

        res = await client.post(f"/api/v1/matches/{m.id}/report/confirm", headers=_h(b))
        assert res.status_code == 200, res.text
        await db.refresh(m)
        assert (m.status, m.winner_id) == (MatchStatus.COMPLETED, m.team1_id)
        nxt = await db.get(Match, m.next_match_id)
        assert m.team1_id in (nxt.team1_id, nxt.team2_id)

    @pytest.mark.asyncio
    async def test_異議は主催者の結果登録で決着する(self, client: AsyncClient, db):
        org, tour, owners, teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        a, b = _owner_of(m.team1_id, owners, teams), _owner_of(m.team2_id, owners, teams)
        await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(a), json={"winner_id": str(m.team1_id)})
        res = await client.post(f"/api/v1/matches/{m.id}/report/dispute", headers=_h(b), json={"reason": "スコアが違う"})
        assert res.json()["data"]["status"] == "disputed", res.text
        # 異議中は報告し直せない
        res = await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(a), json={"winner_id": str(m.team1_id)})
        assert res.status_code == 400

        assert (await client.patch(f"/api/v1/matches/{m.id}/start", headers=_h(org))).status_code == 204
        res = await client.post(f"/api/v1/matches/{m.id}/result", headers=_h(org), json={"winner_id": str(m.team2_id)})
        assert res.status_code == 204, res.text
        report = (await db.execute(select(MatchResultReport).where(MatchResultReport.match_id == m.id))).scalar_one()
        assert report.status == "superseded"
        await db.refresh(m)
        assert m.winner_id == m.team2_id

    @pytest.mark.asyncio
    async def test_両チームの報告が食い違うと異議になり一致すれば確定(self, client: AsyncClient, db):
        _org, tour, owners, teams = await _setup(db)
        m1, m2 = (await _round1(db, tour))[:2]
        a, b = _owner_of(m1.team1_id, owners, teams), _owner_of(m1.team2_id, owners, teams)
        await client.post(f"/api/v1/matches/{m1.id}/report", headers=_h(a), json={"winner_id": str(m1.team1_id)})
        res = await client.post(f"/api/v1/matches/{m1.id}/report", headers=_h(b), json={"winner_id": str(m1.team2_id)})
        assert res.json()["data"]["status"] == "disputed"

        c, d = _owner_of(m2.team1_id, owners, teams), _owner_of(m2.team2_id, owners, teams)
        await client.post(f"/api/v1/matches/{m2.id}/report", headers=_h(c), json={"winner_id": str(m2.team2_id)})
        res = await client.post(f"/api/v1/matches/{m2.id}/report", headers=_h(d), json={"winner_id": str(m2.team2_id)})
        assert res.json()["data"]["status"] == "confirmed"
        await db.refresh(m2)
        assert m2.winner_id == m2.team2_id

    @pytest.mark.asyncio
    async def test_報告できるのはオーナーかキャプテンと主催者(self, client: AsyncClient, db):
        org, tour, _owners, teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        team1 = next(t for t in teams if t.id == m.team1_id)
        member_user = await f.make_user(db)
        captain_user = await f.make_user(db)
        outsider = await f.make_user(db)
        await f.add_member(db, team=team1, player=await f.make_player(db, user=member_user), role=MemberRole.PLAYER)
        await f.add_member(db, team=team1, player=await f.make_player(db, user=captain_user), role=MemberRole.CAPTAIN)
        body = {"winner_id": str(m.team1_id)}
        for u in (member_user, outsider):
            assert (await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(u), json=body)).status_code == 403
        res = await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(captain_user), json=body)
        assert res.json()["data"]["status"] == "pending", res.text
        # 主催者の報告はその場で確定する
        res = await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(org), json=body)
        assert res.json()["data"]["status"] == "confirmed", res.text


class TestReopenAndForfeit:
    @pytest.mark.asyncio
    async def test_再開すると結果と次の試合への進出が取り消される(self, client: AsyncClient, db):
        org, tour, _owners, _teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        svc = MatchService(db, _Cache())
        await svc.start_match(m.id, org)
        await svc.register_result(m.id, MatchResultCreate(winner_id=m.team1_id), org)

        other_org = await f.make_user(db, role=UserRole.ORGANIZER)
        assert (await client.post(f"/api/v1/matches/{m.id}/reopen", headers=_h(other_org))).status_code == 403
        assert (await client.post(f"/api/v1/matches/{m.id}/reopen", headers=_h(org))).status_code == 204
        await db.refresh(m)
        assert (m.status, m.winner_id) == (MatchStatus.ONGOING, None)
        nxt = await db.get(Match, m.next_match_id)
        assert m.team1_id not in (nxt.team1_id, nxt.team2_id)
        assert (await db.execute(select(MatchResult).where(MatchResult.match_id == m.id))).first() is None

    @pytest.mark.asyncio
    async def test_次の試合が始まっていたら再開できない(self, client: AsyncClient, db):
        org, tour, _owners, _teams = await _setup(db)
        m1, m2 = (await _round1(db, tour))[:2]
        svc = MatchService(db, _Cache())
        for m in (m1, m2):
            await svc.start_match(m.id, org)
            await svc.register_result(m.id, MatchResultCreate(winner_id=m.team1_id), org)
        await svc.start_match(m1.next_match_id, org)
        assert (await client.post(f"/api/v1/matches/{m1.id}/reopen", headers=_h(org))).status_code == 400

    @pytest.mark.asyncio
    async def test_Botの不戦勝は結果を登録して勝者を次へ送る(self, client: AsyncClient, db):
        org, tour, _owners, _teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        db.add(DiscordLink(user_id=org.id, discord_user_id="900001", linked_at=datetime.now(UTC)))
        await db.flush()
        res = await client.post(
            f"/api/v1/bot/matches/{m.id}/forfeit", json={"winner_id": str(m.team2_id)},
            headers={"X-Bot-Secret": "ci-bot-secret", "X-Discord-User-Id": "900001"},
        )
        assert res.status_code == 200, res.text
        await db.refresh(m)
        assert (m.status, m.winner_id) == (MatchStatus.COMPLETED, m.team2_id)
        result = (await db.execute(select(MatchResult).where(MatchResult.match_id == m.id))).scalar_one()
        assert result.was_forfeit
        nxt = await db.get(Match, m.next_match_id)
        assert m.team2_id in (nxt.team1_id, nxt.team2_id)


class TestDoubleElimination:
    @pytest.mark.asyncio
    async def test_敗者側へ送られグランドファイナルまで進む(self, db):
        org, tour, _owners, _teams = await _setup(db, fmt=TournamentFormat.DOUBLE_ELIMINATION)
        svc = MatchService(db, _Cache())

        async def play(match_id, winner_slot):
            m = await db.get(Match, match_id)
            await db.refresh(m)
            winner = m.team1_id if winner_slot == 1 else m.team2_id
            loser = m.team2_id if winner_slot == 1 else m.team1_id
            await svc.start_match(m.id, org)
            await svc.register_result(m.id, MatchResultCreate(winner_id=winner), org)
            return m, winner, loser

        w1, w2 = (await _round1(db, tour))[:2]
        m1, _a, b = await play(w1.id, 1)
        _m2, _c, d = await play(w2.id, 1)
        lb1 = await db.get(Match, m1.loser_next_match_id)
        await db.refresh(lb1)
        assert {lb1.team1_id, lb1.team2_id} == {b, d}  # 1回戦の敗者2チーム

        wf, a2, c2 = await play(m1.next_match_id, 1)  # 勝者側決勝
        _lb1m, b2, _ = await play(lb1.id, 1)
        lb2 = await db.get(Match, wf.loser_next_match_id)
        await db.refresh(lb2)
        assert {lb2.team1_id, lb2.team2_id} == {c2, b2}  # 勝者側決勝の敗者が敗者側へ
        lbf, lb_winner, _ = await play(lb2.id, 1)
        gf = await db.get(Match, wf.next_match_id)
        await db.refresh(gf)
        assert {gf.team1_id, gf.team2_id} == {a2, lb_winner}
        assert lbf.next_match_id == gf.id


class TestWithdrawAndProgress:
    @pytest.mark.asyncio
    async def test_組み合わせ生成前なら辞退できる(self, client: AsyncClient, db):
        org = await f.make_user(db, role=UserRole.ORGANIZER)
        tour = await f.make_tournament(db, organizer=org)
        owner, member = await f.make_user(db), await f.make_user(db)
        team = await f.make_team(db, owner=owner, name="Withdraw Team", tag="WDR")
        await f.add_member(db, team=team, player=await f.make_player(db, user=member), role=MemberRole.PLAYER)
        await f.register_team(db, tournament=tour, team=team, status=RegistrationStatus.PENDING)

        assert (await client.post(f"/api/v1/tournaments/{tour.id}/withdraw", headers=_h(member))).status_code == 403
        res = await client.post(f"/api/v1/tournaments/{tour.id}/withdraw", headers=_h(owner))
        assert res.json()["data"]["status"] == "withdrawn", res.text
        reg = (await db.execute(select(TournamentRegistration).where(
            TournamentRegistration.team_id == team.id))).scalar_one()
        assert reg.status == RegistrationStatus.WITHDRAWN

    @pytest.mark.asyncio
    async def test_組み合わせ生成後は辞退できない(self, client: AsyncClient, db):
        _org, tour, owners, _teams = await _setup(db)
        res = await client.post(f"/api/v1/tournaments/{tour.id}/withdraw", headers=_h(owners[0]))
        assert res.status_code == 400, res.text

    @pytest.mark.asyncio
    async def test_進行状況とMatchCenterが表示できる(self, client: AsyncClient, db):
        org, tour, _owners, _teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        svc = MatchService(db, _Cache())
        await svc.start_match(m.id, org)
        for path in ("overview", "live", "statistics", "bracket"):
            res = await client.get(f"/api/v1/tournaments/{tour.id}/{path}")
            assert res.status_code == 200, (path, res.text)
        detail = (await client.get(f"/api/v1/matches/{m.id}")).json()["data"]
        assert detail["status"] == "ongoing" and detail["team1"]["id"] == str(m.team1_id)
        live = (await client.get(f"/api/v1/tournaments/{tour.id}/live")).json()["data"]
        assert live  # 進行中の試合を含む集計が返る


# ══ RC2: 再開時の古い報告・成績の重複・異議の理由の公開範囲・辞退ボタン ══════════════

async def _finish(db, svc, org, match_id, winner_slot=1):
    m = await db.get(Match, match_id)
    await db.refresh(m)
    if m.status == MatchStatus.SCHEDULED:
        await svc.start_match(m.id, org)
    winner = m.team1_id if winner_slot == 1 else m.team2_id
    await svc.register_result(m.id, MatchResultCreate(winner_id=winner), org)
    return winner


async def _report_state(client, match_id, user) -> dict:
    res = await client.get(f"/api/v1/matches/{match_id}/report", headers=_h(user))
    assert res.status_code == 200, res.text
    return res.json()["data"]


class TestReopenResetsReports:
    @pytest.mark.asyncio
    async def test_再開すると次の試合の古い報告が消え入れ替わった相手だけでは確定できない(self, client: AsyncClient, db):
        org, tour, owners, teams = await _setup(db)
        m1, m2 = (await _round1(db, tour))[:2]
        svc = MatchService(db, _Cache())
        a = await _finish(db, svc, org, m1.id)  # m1 は team1（A）の勝ち
        c = await _finish(db, svc, org, m2.id)  # m2 は team1（C）の勝ち
        final = await db.get(Match, m1.next_match_id)
        await db.refresh(final)
        assert {final.team1_id, final.team2_id} == {a, c}

        # 決勝の開始前に、A が「C の勝ち」と報告しておく（確認待ち）
        res = await client.post(f"/api/v1/matches/{final.id}/report", headers=_h(_owner_of(a, owners, teams)),
                                json={"winner_id": str(c)})
        assert res.json()["data"]["status"] == "pending", res.text

        # 主催者が m1 を再開し、B の勝ちに直す。決勝の相手は A から B に入れ替わる
        assert (await client.post(f"/api/v1/matches/{m1.id}/reopen", headers=_h(org))).status_code == 204
        assert (await db.execute(select(MatchResultReport).where(
            MatchResultReport.match_id == final.id))).first() is None
        b = await _finish(db, svc, org, m1.id, winner_slot=2)
        await db.refresh(final)
        assert {final.team1_id, final.team2_id} == {b, c}

        # A の古い報告を、C だけの確認で確定させることはできない
        res = await client.post(f"/api/v1/matches/{final.id}/report/confirm",
                                headers=_h(_owner_of(c, owners, teams)))
        assert res.status_code == 400, res.text
        await db.refresh(final)
        assert (final.status, final.winner_id) == (MatchStatus.SCHEDULED, None)
        state = await _report_state(client, final.id, _owner_of(b, owners, teams))
        assert state["report"] is None and state["can_report"]

    @pytest.mark.asyncio
    async def test_再開した試合の報告と異議は消えて両チームが報告し直せる(self, client: AsyncClient, db):
        org, tour, owners, teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        a, b = _owner_of(m.team1_id, owners, teams), _owner_of(m.team2_id, owners, teams)
        await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(a), json={"winner_id": str(m.team1_id)})
        await client.post(f"/api/v1/matches/{m.id}/report/dispute", headers=_h(b), json={"reason": "スコアが違う"})
        await _finish(db, MatchService(db, _Cache()), org, m.id, winner_slot=2)  # 主催者が B の勝ちで裁定

        assert (await client.post(f"/api/v1/matches/{m.id}/reopen", headers=_h(org))).status_code == 204
        state = await _report_state(client, m.id, a)
        assert state["report"] is None and state["can_report"] and not state["can_confirm"]

        res = await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(a), json={"winner_id": str(m.team1_id)})
        assert res.json()["data"]["status"] == "pending", res.text
        res = await client.post(f"/api/v1/matches/{m.id}/report/confirm", headers=_h(b))
        assert res.json()["data"]["status"] == "confirmed", res.text
        await db.refresh(m)
        assert (m.status, m.winner_id) == (MatchStatus.COMPLETED, m.team1_id)


async def _with_players(db, teams):
    mp = Map(game=GameType.VALORANT, internal_name=f"map-{uuid.uuid4().hex[:6]}", display_name="RC2 Map")
    db.add(mp)
    await db.flush()
    roster = {}
    for team in teams:
        roster[team.id] = []
        for i in range(2):
            player = await f.make_player(db, user=await f.make_user(db), in_game_name=f"{team.tag}-{i}")
            await f.add_member(db, team=team, player=player, role=MemberRole.PLAYER)
            roster[team.id].append(player)
    return mp, roster


def _player_rows(roster, team_ids, kills):
    return [PlayerStatsCreate(player_id=p.id, team_id=t, kills=kills) for t in team_ids for p in roster[t]]


async def _stats(db, match_id) -> list[PlayerMatchStats]:
    return list((await db.execute(
        select(PlayerMatchStats).join(MatchGame, MatchGame.id == PlayerMatchStats.match_game_id)
        .where(MatchGame.match_id == match_id)
    )).scalars().all())


class TestStatsAreNotDuplicated:
    @pytest.mark.asyncio
    async def test_再開して登録し直しても選手成績は二重にならない(self, client: AsyncClient, db):
        org, tour, _owners, teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        mp, roster = await _with_players(db, teams)
        svc = MatchService(db, _Cache())
        ids = (m.team1_id, m.team2_id)

        def result(kills):
            return MatchResultCreate(winner_id=m.team1_id, game_stats=[GameStatsCreate(
                game_number=1, map_id=str(mp.id), team1_score=13, team2_score=7, winner_id=m.team1_id,
                player_stats=_player_rows(roster, ids, kills))])

        await svc.start_match(m.id, org)
        await svc.register_result(m.id, result(10), org)
        assert len(await _stats(db, m.id)) == 4

        await svc.reopen_match(m.id, org)
        await svc.register_result(m.id, result(25), org)
        rows = await _stats(db, m.id)
        assert len(rows) == 4  # 置き換え（以前は 8 行になっていた）
        assert {r.kills for r in rows} == {25}
        games = (await db.execute(
            select(func.count()).select_from(MatchGame).where(MatchGame.match_id == m.id))).scalar_one()
        assert games == 1

    @pytest.mark.asyncio
    async def test_マップごとに保存した成績の後で結果を登録しても二重にならない(self, client: AsyncClient, db):
        org, tour, _owners, teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        mp, roster = await _with_players(db, teams)
        svc = MatchService(db, _Cache())
        ids = (m.team1_id, m.team2_id)
        await svc.start_match(m.id, org)
        await svc.save_game_player_stats(m.id, 1, GamePlayerStatsUpdate(
            map_id=str(mp.id), team1_score=13, team2_score=7, player_stats=_player_rows(roster, ids, 5)), org)
        assert len(await _stats(db, m.id)) == 4

        await svc.register_result(m.id, MatchResultCreate(winner_id=m.team1_id, game_stats=[GameStatsCreate(
            game_number=1, map_id=str(mp.id), team1_score=13, team2_score=7, winner_id=m.team1_id,
            player_stats=_player_rows(roster, ids, 9))]), org)
        rows = await _stats(db, m.id)
        assert len(rows) == 4 and {r.kills for r in rows} == {9}


class TestReportStateVisibility:
    @pytest.mark.asyncio
    async def test_異議の理由は両チームと主催者と管理者にだけ返る(self, client: AsyncClient, db):
        org, tour, owners, teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        team1 = next(t for t in teams if t.id == m.team1_id)
        team2 = next(t for t in teams if t.id == m.team2_id)
        a, b = _owner_of(team1.id, owners, teams), _owner_of(team2.id, owners, teams)
        member1, member2, captain2 = await f.make_user(db), await f.make_user(db), await f.make_user(db)
        await f.add_member(db, team=team1, player=await f.make_player(db, user=member1), role=MemberRole.PLAYER)
        await f.add_member(db, team=team2, player=await f.make_player(db, user=member2), role=MemberRole.PLAYER)
        await f.add_member(db, team=team2, player=await f.make_player(db, user=captain2), role=MemberRole.CAPTAIN)
        admin = await f.make_user(db, role=UserRole.ADMIN)
        outsider = await f.make_user(db)
        other_org = await f.make_user(db, role=UserRole.ORGANIZER)
        third_team_owner = next(o for o, t in zip(owners, teams) if t.id not in (team1.id, team2.id))

        await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(a), json={"winner_id": str(m.team1_id)})
        reason = "相手チームのスコアが違う（第2マップ）"
        res = await client.post(f"/api/v1/matches/{m.id}/report/dispute", headers=_h(b), json={"reason": reason})
        assert res.json()["data"]["status"] == "disputed", res.text

        for viewer in (a, b, member1, member2, captain2, org, admin):
            state = await _report_state(client, m.id, viewer)
            assert state["report"]["dispute_reason"] == reason, viewer.username
        for viewer in (outsider, other_org, third_team_owner):
            state = await _report_state(client, m.id, viewer)
            assert state["report"]["status"] == "disputed"
            assert state["report"]["dispute_reason"] is None, viewer.username
            assert reason not in str(state)
        assert (await client.get(f"/api/v1/matches/{m.id}/report")).status_code == 401
        # 公開の試合詳細にも理由は出ない
        assert reason not in (await client.get(f"/api/v1/matches/{m.id}")).text

    @pytest.mark.asyncio
    async def test_異議中はチームからは報告できず主催者は裁定できる(self, client: AsyncClient, db):
        org, tour, owners, teams = await _setup(db)
        m = (await _round1(db, tour))[0]
        a, b = _owner_of(m.team1_id, owners, teams), _owner_of(m.team2_id, owners, teams)
        await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(a), json={"winner_id": str(m.team1_id)})
        await client.post(f"/api/v1/matches/{m.id}/report/dispute", headers=_h(b), json={"reason": "違う"})
        for team_user in (a, b):
            state = await _report_state(client, m.id, team_user)
            assert not state["can_report"] and not state["can_confirm"] and not state["can_dispute"]
        assert (await _report_state(client, m.id, org))["can_report"]
        res = await client.post(f"/api/v1/matches/{m.id}/report", headers=_h(org), json={"winner_id": str(m.team2_id)})
        assert res.json()["data"]["status"] == "confirmed", res.text


class TestWithdrawDisplay:
    @pytest.mark.asyncio
    async def test_辞退ボタンはオーナーとキャプテンにだけ出て主催者は辞退を取り消せる(self, client: AsyncClient, db):
        org = await f.make_user(db, role=UserRole.ORGANIZER)
        tour = await f.make_tournament(db, organizer=org)
        owner, captain, member = await f.make_user(db), await f.make_user(db), await f.make_user(db)
        team = await f.make_team(db, owner=owner, name="Withdraw Display", tag="WDD")
        await f.add_member(db, team=team, player=await f.make_player(db, user=captain), role=MemberRole.CAPTAIN)
        await f.add_member(db, team=team, player=await f.make_player(db, user=member), role=MemberRole.PLAYER)
        reg = await f.register_team(db, tournament=tour, team=team, status=RegistrationStatus.PENDING)

        async def mine(user):
            res = await client.get(f"/api/v1/tournaments/{tour.id}/my-registration", headers=_h(user))
            assert res.status_code == 200, res.text
            return res.json()["data"]

        assert (await mine(owner))["can_withdraw"] and (await mine(captain))["can_withdraw"]
        assert (await mine(member))["can_withdraw"] is False

        res = await client.post(f"/api/v1/tournaments/{tour.id}/withdraw", headers=_h(captain))
        assert res.json()["data"]["status"] == "withdrawn", res.text
        state = await mine(owner)
        assert (state["status"], state["can_withdraw"]) == ("withdrawn", False)

        # 辞退の取り消しは主催者が承認し直す（他の主催者はできない）
        other_org = await f.make_user(db, role=UserRole.ORGANIZER)
        url = f"/api/v1/tournaments/{tour.id}/registrations/{reg.id}?status=approved"
        assert (await client.patch(url, headers=_h(other_org))).status_code == 403
        res = await client.patch(url, headers=_h(org))
        assert res.status_code == 200, res.text
        state = await mine(owner)
        assert (state["status"], state["can_withdraw"]) == ("approved", True)

    @pytest.mark.asyncio
    async def test_2チームで関わっていても有効な方の登録を表示して辞退できる(self, client: AsyncClient, db):
        org = await f.make_user(db, role=UserRole.ORGANIZER)
        tour = await f.make_tournament(db, organizer=org)
        owner = await f.make_user(db)
        old_team = await f.make_team(db, owner=owner, name="Old Team", tag="OLD")
        new_team = await f.make_team(db, owner=owner, name="New Team", tag="NEW")
        await f.register_team(db, tournament=tour, team=old_team, status=RegistrationStatus.WITHDRAWN)
        await f.register_team(db, tournament=tour, team=new_team, status=RegistrationStatus.PENDING)

        res = await client.get(f"/api/v1/tournaments/{tour.id}/my-registration", headers=_h(owner))
        data = res.json()["data"]
        assert (data["team_id"], data["status"], data["can_withdraw"]) == (str(new_team.id), "pending", True)

        res = await client.post(f"/api/v1/tournaments/{tour.id}/withdraw", headers=_h(owner))
        assert res.json()["data"]["status"] == "withdrawn", res.text
        regs = {r.team_id: r.status for r in (await db.execute(select(TournamentRegistration).where(
            TournamentRegistration.tournament_id == tour.id))).scalars()}
        assert regs == {old_team.id: RegistrationStatus.WITHDRAWN, new_team.id: RegistrationStatus.WITHDRAWN}
