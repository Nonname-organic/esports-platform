"""SCOUT-*: 検索（公開）。"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import make_player, make_user


@pytest.mark.asyncio
async def test_scout001_search_players(client: AsyncClient, db: AsyncSession):
    """SCOUT-001: 選手検索は公開・200・list。"""
    u = await make_user(db)
    await make_player(db, user=u, in_game_name="ScoutMe")
    r = await client.get("/api/v1/scout/players", params={"limit": 10})
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


@pytest.mark.asyncio
async def test_scout002_search_teams(client: AsyncClient):
    r = await client.get("/api/v1/scout/teams")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


@pytest.mark.asyncio
async def test_scout_recruitment_list_public(client: AsyncClient):
    r = await client.get("/api/v1/scout/recruitment")
    assert r.status_code == 200
