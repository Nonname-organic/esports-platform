"""BRKT — ブラケット生成の回帰テスト。

回帰対象（本番不具合）:
- 日程ベース自動ステータスで大会が ONGOING になった後、organizer がブラケットを
  生成できなかった（サービスが ONGOING を拒否していた）。フロントは ONGOING で
  生成ボタンを活性化していたため「生成できない」状態になっていた。
- ONGOING を許可。さらに二重生成を防ぐ冪等ガードを追加。
"""

import uuid

import pytest

from app.core.exceptions import BusinessRuleError
from app.models.enums import TournamentStatus, UserRole
from app.services.tournament import TournamentService
from tests import factories as f


class _Cache:
    async def get(self, *a, **k): return None
    async def set(self, *a, **k): pass
    async def delete(self, *a, **k): pass
    async def delete_pattern(self, *a, **k): return 0


async def _setup_ongoing_tournament(db, n_teams=4):
    organizer = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=organizer, status=TournamentStatus.ONGOING)
    for i in range(n_teams):
        team = await f.make_team(db, owner=organizer, name=f"BR Team {i}", tag=f"BR{i}")
        await f.register_team(db, tournament=tour, team=team)
    return organizer, tour


@pytest.mark.asyncio
async def test_brkt001_generate_allowed_when_ongoing(db):
    """ONGOING でもブラケット生成できる（回帰: 以前は拒否されていた）。"""
    organizer, tour = await _setup_ongoing_tournament(db, n_teams=4)
    svc = TournamentService(db, _Cache())

    res = await svc.generate_bracket(tour.id, organizer)

    assert res.rounds, "ブラケットのラウンドが生成されること"
    # 4チーム → 2回戦 (R1: 2試合, R2: 1試合)
    assert 1 in res.rounds
    assert len(res.rounds[1]) == 2


@pytest.mark.asyncio
async def test_brkt002_idempotent_no_duplicate(db):
    """二重生成は BusinessRuleError（冪等ガード）。"""
    organizer, tour = await _setup_ongoing_tournament(db, n_teams=4)
    svc = TournamentService(db, _Cache())

    await svc.generate_bracket(tour.id, organizer)
    with pytest.raises(BusinessRuleError):
        await svc.generate_bracket(tour.id, organizer)


@pytest.mark.asyncio
async def test_brkt003_rejected_before_registration_closed(db):
    """受付中(REGISTRATION_OPEN)など早すぎる状態では生成不可。"""
    organizer = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=organizer, status=TournamentStatus.REGISTRATION_OPEN)
    for i in range(2):
        team = await f.make_team(db, owner=organizer, name=f"E Team {i}", tag=f"E{i}")
        await f.register_team(db, tournament=tour, team=team)
    svc = TournamentService(db, _Cache())

    with pytest.raises(BusinessRuleError):
        await svc.generate_bracket(tour.id, organizer)
