"""TEAM-*: チーム作成（presigned長URL/banner_url 回帰）・詳細。"""

import pytest
from httpx import AsyncClient


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_team001_create_with_long_banner_url(client: AsyncClient, player_token: str):
    """TEAM-001 回帰: presigned風の長いlogo/banner URL(>500字)でも作成成功。

    （schema max_length 2048 + Team.banner_url カラム追加の回帰）
    """
    long_url = "https://bucket.s3.amazonaws.com/x.png?" + "a=1&" * 250  # ~1000+ 文字
    r = await client.post(
        "/api/v1/teams",
        headers=_h(player_token),
        json={
            "name": "Regression FC",
            "tag": "RGF",
            "game": "VALORANT",
            "logo_url": long_url,
            "banner_url": long_url,
            "description": "banner_url regression",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["banner_url"] == long_url
    assert data["logo_url"] == long_url


@pytest.mark.asyncio
async def test_team001b_tag_validation(client: AsyncClient, player_token: str):
    """tag は英数字のみ・長さ制約 → 不正は422。"""
    r = await client.post(
        "/api/v1/teams", headers=_h(player_token),
        json={"name": "Bad Tag", "tag": "あ！#", "game": "VALORANT"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_team002_detail_and_members(client: AsyncClient, player_token: str):
    """TEAM-002: 作成→詳細→メンバー一覧 200。"""
    created = await client.post(
        "/api/v1/teams", headers=_h(player_token),
        json={"name": "Detail Team", "tag": "DTL", "game": "CS2"},
    )
    assert created.status_code == 201
    tid = created.json()["data"]["id"]

    detail = await client.get(f"/api/v1/teams/{tid}")
    assert detail.status_code == 200
    assert detail.json()["data"]["tag"] == "DTL"

    members = await client.get(f"/api/v1/teams/{tid}/members")
    assert members.status_code == 200
