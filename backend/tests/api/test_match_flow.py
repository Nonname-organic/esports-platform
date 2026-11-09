"""試合の進行まわりの回帰テスト。

- 対戦チームによる結果報告 → 相手チームの確認・異議（主催者の直接確定と両立する）
- 確定済み試合の再開（次の試合へ送ったチームも取り除く）
- Discord Bot の不戦勝（結果登録と勝ち上がりまで行う）
- ダブルエリミネーションの敗者側進行
- 参加の辞退、大会進行状況の表示
"""
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.discord import DiscordLink
from app.models.enums import (
    MatchStatus,
    MemberRole,
    RegistrationStatus,
    TournamentFormat,
    TournamentStatus,
    UserRole,
)
from app.models.match import Match, MatchResult
from app.models.match_report import MatchResultReport
from app.models.tournament import TournamentRegistration
from app.schemas.match import MatchResultCreate
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
