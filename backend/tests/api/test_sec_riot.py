"""Riot 連携の回帰テスト（Riot API はすべてモック）。

- 他人のプレイヤーに Riot ID を紐付け・同期できた（IDOR）。
- 別プレイヤーが紐付け済みの Riot アカウントで 500、不正な UUID で 500 になった。
- Riot ID をそのまま URL パスに埋めていた。プロフィール取得で puuid が誰にでも見えた。
"""
from datetime import UTC, datetime

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.riot import RiotProfile
from app.services import riot_service
from app.services.riot_service import RiotAPIClient
from tests import factories as f
from tests.conftest import auth_headers


def _token(user) -> str:
    return create_access_token(str(user.id), {"role": user.role.value})


async def _player(db, **kw):
    user = await f.make_user(db)
    return user, await f.make_player(db, user=user, **kw)


@pytest.fixture
def fixed_puuid(monkeypatch):
    async def resolve(self, game_name, tag_line):
        return "PUUID-SAME-ACCOUNT"
    monkeypatch.setattr(RiotAPIClient, "resolve_puuid", resolve)


class TestOwnership:
    @pytest.mark.asyncio
    async def test_他人のプレイヤーには紐付けも同期もできない(self, client: AsyncClient, db, fixed_puuid):
        _, victim = await _player(db)
        attacker, _ = await _player(db)
        h = auth_headers(_token(attacker))

        res = await client.post("/api/v1/riot/link", json={"player_id": str(victim.id), "riot_id": "Evil#666"}, headers=h)
        assert res.status_code == 403, res.text
        res = await client.post(f"/api/v1/riot/sync/{victim.id}", headers=h)
        assert res.status_code == 403, res.text
        assert await db.scalar(select(RiotProfile).where(RiotProfile.player_id == victim.id)) is None

    @pytest.mark.asyncio
    async def test_本人と管理者は紐付けられる(self, client: AsyncClient, db, fixed_puuid, admin_token):
        user, player = await _player(db)
        res = await client.post("/api/v1/riot/link", json={"player_id": str(player.id), "riot_id": "Me#JP1"},
                                headers=auth_headers(_token(user)))
        assert res.status_code == 200, res.text
        res = await client.post("/api/v1/riot/link", json={"player_id": str(player.id), "riot_id": "Me#JP2"},
                                headers=auth_headers(admin_token))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["riot_id"] == "Me#JP2"


class TestInputAndConflicts:
    @pytest.mark.asyncio
    async def test_不正なUUIDは422(self, client: AsyncClient, db):
        user, _ = await _player(db)
        res = await client.post("/api/v1/riot/link", json={"player_id": "not-a-uuid", "riot_id": "A#B"},
                                headers=auth_headers(_token(user)))
        assert res.status_code == 422, res.text

    @pytest.mark.asyncio
    async def test_別プレイヤーが紐付け済みのRiotアカウントは409(self, client: AsyncClient, db, fixed_puuid):
        u1, p1 = await _player(db)
        u2, p2 = await _player(db)
        res = await client.post("/api/v1/riot/link", json={"player_id": str(p1.id), "riot_id": "Same#JP1"},
                                headers=auth_headers(_token(u1)))
        assert res.status_code == 200, res.text
        res = await client.post("/api/v1/riot/link", json={"player_id": str(p2.id), "riot_id": "Same#JP1"},
                                headers=auth_headers(_token(u2)))
        assert res.status_code == 409, res.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("riot_id,status", [
        ("NoTag", 400), ("..#JP1", 400), ("Name#..", 400), (".#JP1", 400), ("#JP1", 400),
        ("a" * 51 + "#JP1", 400), ("Name#" + "T" * 11, 400), ("a" * 62, 422),
    ])
    async def test_RiotIDの形式と長さ(self, client: AsyncClient, db, fixed_puuid, riot_id, status):
        user, player = await _player(db)
        res = await client.post("/api/v1/riot/link", json={"player_id": str(player.id), "riot_id": riot_id},
                                headers=auth_headers(_token(user)))
        assert res.status_code == status, res.text

    @pytest.mark.asyncio
    async def test_RiotIDはURLパスへエンコードして渡す(self, monkeypatch):
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            return httpx.Response(200, json={"puuid": "p"})

        real = httpx.AsyncClient
        monkeypatch.setattr(riot_service.httpx, "AsyncClient",
                            lambda *a, **k: real(transport=httpx.MockTransport(handler)))
        monkeypatch.setattr(settings, "RIOT_API_KEY", "test-key")

        assert await RiotAPIClient(object()).resolve_puuid("a/../b c", "x?y#z") == "p"
        assert seen[0].url.raw_path.endswith(b"/by-riot-id/a%2F..%2Fb%20c/x%3Fy%23z")


class TestProfileExposure:
    @pytest.mark.asyncio
    async def test_プロフィールにpuuidを含めない(self, client: AsyncClient, db):
        _, player = await _player(db)
        db.add(RiotProfile(player_id=player.id, game_name="Pub", tag_line="JP1", puuid="SECRET-PUUID",
                           created_at=datetime.now(UTC)))
        await db.flush()
        res = await client.get(f"/api/v1/riot/profile/{player.id}")
        assert res.status_code == 200, res.text
        assert "puuid" not in res.json()["data"]
        assert "SECRET-PUUID" not in res.text

    @pytest.mark.asyncio
    async def test_詳細スタッツ非公開なら本人と管理者以外には見せない(self, client: AsyncClient, db, admin_token):
        owner, player = await _player(db, stats_public=False)
        stranger, _ = await _player(db)
        url = f"/api/v1/riot/profile/{player.id}"
        assert (await client.get(url)).status_code == 403
        assert (await client.get(url, headers=auth_headers(_token(stranger)))).status_code == 403
        assert (await client.get(url, headers=auth_headers(_token(owner)))).status_code == 200
        assert (await client.get(url, headers=auth_headers(admin_token))).status_code == 200
