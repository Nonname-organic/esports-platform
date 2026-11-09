"""同じ試合への並行した操作（結果の二重確定・成績の二重登録・状態の上書き）。

通常の db フィクスチャは1つのセッションを共有するため、ここでは別々のセッション
（別々のトランザクション）でコミットまで行い、試合の行ロックで1件ずつ処理される
ことを確かめる。Redis のロックは通す設定にして、DB のロックだけで守れることを見る。
"""
import asyncio
import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import BusinessRuleError
from app.models.enums import (
    GameType,
    MatchStatus,
    MemberRole,
    TournamentStatus,
    UserRole,
)
from app.models.match import Map, Match, MatchResult, PlayerMatchStats
from app.schemas.match import (
    GamePlayerStatsUpdate,
    MatchResultCreate,
    PlayerStatsCreate,
)
from app.services.match import MatchService, lock_match
from tests import factories as f
from tests.conftest import TestSessionLocal


class _Cache:
    async def get(self, *a, **k): return None
    async def set(self, *a, **k): pass
    async def delete(self, *a, **k): pass
    async def delete_pattern(self, *a, **k): return 0
    async def acquire_lock(self, *a, **k): return True  # DB の行ロックだけで守れることを確かめる
    async def release_lock(self, *a, **k): pass
    async def publish(self, *a, **k): pass


async def _committed_match(status=MatchStatus.ONGOING):
    """別セッションから見えるよう、試合・選手・マップをコミットしておく。"""
    async with TestSessionLocal() as s:
        org = await f.make_user(s, role=UserRole.ORGANIZER)
        tour = await f.make_tournament(s, organizer=org, status=TournamentStatus.ONGOING)
        teams, rows = [], []
        for i in range(2):
            team = await f.make_team(s, owner=await f.make_user(s), name=f"Conc {uuid.uuid4().hex[:4]}", tag=f"C{i}")
            teams.append(team)
            for j in range(2):
                player = await f.make_player(s, user=await f.make_user(s), in_game_name=f"c{i}{j}")
                await f.add_member(s, team=team, player=player, role=MemberRole.PLAYER)
                rows.append(PlayerStatsCreate(player_id=player.id, team_id=team.id, kills=10))
        match = Match(tournament_id=tour.id, round_number=1, match_number=1, status=status,
                      team1_id=teams[0].id, team2_id=teams[1].id)
        mp = Map(game=GameType.VALORANT, internal_name=f"conc-{uuid.uuid4().hex[:6]}", display_name="Conc")
        s.add_all([match, mp])
        await s.commit()
        return org, match, mp, rows


async def _in_own_session(fn):
    """1件の操作を自分のトランザクションで行い、コミットする。"""
    async with TestSessionLocal() as s:
        try:
            await fn(MatchService(s, _Cache()))
            await s.commit()
            return "ok"
        except BusinessRuleError as e:
            await s.rollback()
            return e


class TestMatchRowLock:
    @pytest.mark.asyncio
    async def test_ロック中の試合は他のトランザクションから操作できない(self, db):
        _org, match, _mp, _rows = await _committed_match()
        async with TestSessionLocal() as s1, TestSessionLocal() as s2:
            assert (await lock_match(s1, match.id)).id == match.id
            await s2.execute(text("SET LOCAL lock_timeout = '300ms'"))
            with pytest.raises(DBAPIError, match="lock"):
                await lock_match(s2, match.id)
            await s2.rollback()
            await s1.commit()  # 解放すれば取れる
            assert (await lock_match(s2, match.id)).id == match.id
            await s2.rollback()

    @pytest.mark.asyncio
    async def test_同時に結果を登録しても確定は1件だけ(self, db):
        org, match, _mp, _rows = await _committed_match()

        def register(winner):
            return lambda svc: svc.register_result(match.id, MatchResultCreate(winner_id=winner), org)

        outcomes = await asyncio.gather(
            _in_own_session(register(match.team1_id)), _in_own_session(register(match.team2_id)))
        assert sorted(type(o).__name__ for o in outcomes) == ["BusinessRuleError", "str"]
        async with TestSessionLocal() as s:
            results = (await s.execute(select(MatchResult).where(MatchResult.match_id == match.id))).scalars().all()
            final = await s.get(Match, match.id)
            assert len(results) == 1 and final.status == MatchStatus.COMPLETED
            assert final.winner_id == results[0].winner_id  # 後から来た側が勝者を書き換えていない

    @pytest.mark.asyncio
    async def test_同じマップの成績を同時に保存しても二重にならない(self, db):
        org, match, mp, rows = await _committed_match()
        body = GamePlayerStatsUpdate(map_id=str(mp.id), team1_score=13, team2_score=9, player_stats=rows)

        outcomes = await asyncio.gather(*(
            _in_own_session(lambda svc: svc.save_game_player_stats(match.id, 1, body, org)) for _ in range(4)))
        assert outcomes == ["ok"] * 4
        async with TestSessionLocal() as s:
            count = await s.scalar(select(func.count()).select_from(PlayerMatchStats))
            assert count == len(rows)

    @pytest.mark.asyncio
    async def test_開始と確定が同時でも確定した状態を上書きしない(self, db):
        org, match, _mp, _rows = await _committed_match(status=MatchStatus.SCHEDULED)

        async def start_then_finish(svc):
            await svc.start_match(match.id, org)
            await svc.register_result(match.id, MatchResultCreate(winner_id=match.team1_id), org)

        outcomes = await asyncio.gather(
            _in_own_session(start_then_finish), _in_own_session(lambda svc: svc.start_match(match.id, org)))
        assert sum(o == "ok" for o in outcomes) >= 1
        async with TestSessionLocal() as s:
            final = await s.get(Match, match.id)
            results = await s.scalar(select(func.count()).select_from(MatchResult))
            # どちらが先でも「確定済みなのに進行中」「結果があるのに未確定」にはならない
            assert (final.status == MatchStatus.COMPLETED) == (results == 1)
