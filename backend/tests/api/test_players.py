"""PLYR-*: プレイヤー詳細・stats(新規=0 回帰)・career。"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import make_player, make_user


@pytest.mark.asyncio
async def test_plyr003_detail(client: AsyncClient, db: AsyncSession):
    """PLYR-003: プレイヤー詳細 200。"""
    u = await make_user(db, username="ign_user")
    p = await make_player(db, user=u, in_game_name="ProAim")
    r = await client.get(f"/api/v1/players/{p.id}")
    assert r.status_code == 200
    assert r.json()["data"]["in_game_name"] == "ProAim"


@pytest.mark.asyncio
async def test_plyr004_stats_zero_for_new_player(client: AsyncClient, db: AsyncSession):
    """PLYR-004 回帰: 実績ゼロの新規プレイヤーでも /stats は200でゼロ値（404にしない）。"""
    u = await make_user(db)
    p = await make_player(db, user=u, in_game_name="Rookie")
    r = await client.get(f"/api/v1/players/{p.id}/stats")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    # フロントの PlayerCareerStats 形に必須キーが揃う（描画クラッシュ防止）
    for k in ("total_matches", "win_rate", "avg_kda", "avg_kills", "avg_deaths"):
        assert k in d


@pytest.mark.asyncio
async def test_plyr003b_detail_404(client: AsyncClient):
    """存在しないプレイヤーは404。"""
    r = await client.get("/api/v1/players/00000000-0000-0000-0000-0000000000ff")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_plyr005_career_endpoints(client: AsyncClient, db: AsyncSession):
    """PLYR-005: career/achievements/rating-history が200。"""
    u = await make_user(db)
    p = await make_player(db, user=u)
    assert (await client.get(f"/api/v1/players/{p.id}/career")).status_code == 200
    assert (await client.get(f"/api/v1/players/{p.id}/achievements")).status_code == 200
    assert (await client.get(f"/api/v1/players/{p.id}/rating-history")).status_code == 200
