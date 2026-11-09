"""Discord 連携の回帰テスト（Discord API はすべてモック）。

- OAuth に state が無く、他人の認可コードを被害者に送らせて Discord を紐付けさせられた（CSRF）。
- 大会の Discord セットアップは organizer ロールだけで通り、他人の大会・他人のサーバーを指定できた。
- セットアップ状態の取得でサーバー/ロール ID が誰にでも見えた。
"""
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import get_cache
from app.core.security import create_access_token
from app.main import app
from app.models.discord import DiscordLink, DiscordServer
from app.models.enums import UserRole
from app.services import discord_service
from tests import factories as f
from tests.conftest import auth_headers


class _MemCache:
    def __init__(self):
        self.d = {}

    async def get(self, k): return self.d.get(k)
    async def set(self, k, v, ttl): self.d[k] = v
    async def delete(self, k): self.d.pop(k, None)


def _token(user) -> str:
    return create_access_token(str(user.id), {"role": user.role.value})


@pytest.fixture
def mem_cache(client):  # client の FakeRedisCache（何も保存しない）を上書きする
    cache = _MemCache()
    app.dependency_overrides[get_cache] = lambda: cache
    return cache


@pytest.fixture
def discord_api(monkeypatch):
    """Discord API への HTTP をモックし、届いたリクエストを記録する。"""
    calls: list[httpx.Request] = []
    routes: dict[str, httpx.Response] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        for suffix, res in routes.items():
            if request.url.path.endswith(suffix):
                return res
        return httpx.Response(404)

    real = httpx.AsyncClient
    monkeypatch.setattr(discord_service.httpx, "AsyncClient",
                        lambda *a, **k: real(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(settings, "DISCORD_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "DISCORD_CLIENT_SECRET", "csecret")
    monkeypatch.setattr(settings, "DISCORD_REDIRECT_URI", "http://localhost/discord/callback")
    return calls, routes


async def _issue_state(client, user) -> str:
    res = await client.get("/api/v1/discord/oauth/login", headers=auth_headers(_token(user)))
    assert res.status_code == 200, res.text
    return parse_qs(urlparse(res.json()["data"]["url"]).query)["state"][0]


class TestOAuthState:
    @pytest.mark.asyncio
    async def test_認可URLに本人へ紐付いたstateが付く(self, client: AsyncClient, db, mem_cache, discord_api):
        user = await f.make_user(db)
        state = await _issue_state(client, user)
        assert len(state) >= 32
        assert mem_cache.d[f"discord_oauth_state:{state}"] == {"user_id": str(user.id)}

    @pytest.mark.asyncio
    async def test_stateなしのコールバックは受け付けない(self, client: AsyncClient, db, mem_cache, discord_api):
        user = await f.make_user(db)
        res = await client.post("/api/v1/discord/oauth/callback", json={"code": "c"},
                                headers=auth_headers(_token(user)))
        assert res.status_code == 422, res.text

    @pytest.mark.asyncio
    async def test_他人のstateでは紐付けずDiscordにも問い合わせない(self, client: AsyncClient, db, mem_cache, discord_api):
        calls, _ = discord_api
        attacker, victim = await f.make_user(db), await f.make_user(db)
        state = await _issue_state(client, attacker)

        res = await client.post("/api/v1/discord/oauth/callback", json={"code": "attacker-code", "state": state},
                                headers=auth_headers(_token(victim)))
        assert res.status_code == 400, res.text
        assert calls == []
        assert await db.scalar(select(DiscordLink).where(DiscordLink.user_id == victim.id)) is None

    @pytest.mark.asyncio
    async def test_正しいstateで紐付きstateは1回限り(self, client: AsyncClient, db, mem_cache, discord_api):
        calls, routes = discord_api
        routes["/oauth2/token"] = httpx.Response(200, json={"access_token": "at", "refresh_token": "rt"})
        routes["/users/@me"] = httpx.Response(200, json={"id": "123456789012345678", "username": "neo"})
        user = await f.make_user(db)
        state = await _issue_state(client, user)

        body = {"code": "good-code", "state": state}
        res = await client.post("/api/v1/discord/oauth/callback", json=body, headers=auth_headers(_token(user)))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["discord_username"] == "neo"

        res = await client.post("/api/v1/discord/oauth/callback", json=body, headers=auth_headers(_token(user)))
        assert res.status_code == 400, res.text
        assert len([c for c in calls if c.url.path.endswith("/oauth2/token")]) == 1


async def _organizer_with_tournament(db, *, token="at"):
    owner = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=owner)
    if token:
        db.add(DiscordLink(user_id=owner.id, discord_user_id="1", access_token=token,
                           linked_at=datetime.now(UTC)))
        await db.flush()
    return owner, tour


class TestTournamentSetup:
    @pytest.mark.asyncio
    async def test_存在しない大会は404(self, client: AsyncClient, db, mem_cache, discord_api):
        owner, _ = await _organizer_with_tournament(db)
        res = await client.post("/api/v1/discord/setup/00000000-0000-0000-0000-000000000000",
                                json={"guild_id": "123"}, headers=auth_headers(_token(owner)))
        assert res.status_code == 404, res.text

    @pytest.mark.asyncio
    async def test_他の主催者の大会には設定できない(self, client: AsyncClient, db, mem_cache, discord_api):
        _, tour = await _organizer_with_tournament(db)
        other, _ = await _organizer_with_tournament(db)
        res = await client.post(f"/api/v1/discord/setup/{tour.id}", json={"guild_id": "123"},
                                headers=auth_headers(_token(other)))
        assert res.status_code == 403, res.text
        assert discord_api[0] == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("guild_id", ["abc", "12 3", "1" * 21, "", "../1"])
    async def test_サーバーIDは数字のみ(self, client: AsyncClient, db, mem_cache, discord_api, guild_id):
        owner, tour = await _organizer_with_tournament(db)
        res = await client.post(f"/api/v1/discord/setup/{tour.id}", json={"guild_id": guild_id},
                                headers=auth_headers(_token(owner)))
        assert res.status_code == 422, res.text

    @pytest.mark.asyncio
    async def test_Discord未連携なら連携を促して403(self, client: AsyncClient, db, mem_cache, discord_api):
        owner, tour = await _organizer_with_tournament(db, token=None)
        res = await client.post(f"/api/v1/discord/setup/{tour.id}", json={"guild_id": "123"},
                                headers=auth_headers(_token(owner)))
        assert res.status_code == 403, res.text
        assert "連携" in res.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("guilds", [
        [],                                                        # そのサーバーに居ない
        [{"id": "123", "owner": False, "permissions": "8192"}],    # 管理権限なし（MANAGE_MESSAGES のみ）
        [{"id": "999", "owner": True, "permissions": "32"}],       # 別のサーバー
    ])
    async def test_管理権限の無いサーバーは403(self, client: AsyncClient, db, mem_cache, discord_api, guilds):
        _, routes = discord_api
        routes["/users/@me/guilds"] = httpx.Response(200, json=guilds)
        owner, tour = await _organizer_with_tournament(db)
        res = await client.post(f"/api/v1/discord/setup/{tour.id}", json={"guild_id": "123"},
                                headers=auth_headers(_token(owner)))
        assert res.status_code == 403, res.text

    @pytest.mark.asyncio
    async def test_トークン失効時は再連携を促して403(self, client: AsyncClient, db, mem_cache, discord_api):
        _, routes = discord_api
        routes["/users/@me/guilds"] = httpx.Response(401, json={"message": "401: Unauthorized"})
        owner, tour = await _organizer_with_tournament(db)
        res = await client.post(f"/api/v1/discord/setup/{tour.id}", json={"guild_id": "123"},
                                headers=auth_headers(_token(owner)))
        assert res.status_code == 403, res.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("guild", [
        {"id": "123", "owner": False, "permissions": str(0x20)},
        {"id": "123", "owner": True, "permissions": "0"},
    ])
    async def test_主催者がサーバー管理権限を持てば設定できる(self, client: AsyncClient, db, mem_cache, discord_api, guild):
        calls, routes = discord_api
        routes["/users/@me/guilds"] = httpx.Response(200, json=[guild])
        owner, tour = await _organizer_with_tournament(db, token="owner-token")
        res = await client.post(f"/api/v1/discord/setup/{tour.id}", json={"guild_id": "123"},
                                headers=auth_headers(_token(owner)))
        assert res.status_code == 201, res.text
        assert res.json()["data"]["guild_id"] == "123"
        assert calls[-1].headers["Authorization"] == "Bearer owner-token"

    @pytest.mark.asyncio
    async def test_管理者でもDiscord側のサーバー管理権限が無ければ設定できない(self, client: AsyncClient, db, mem_cache, discord_api):
        # アプリの管理者（ADMIN ロール）と、Discord サーバーの管理権限は別物。管理者も Discord 側で確かめる
        calls, routes = discord_api
        _, tour = await _organizer_with_tournament(db)  # 他人の大会
        admin = await f.make_user(db, role=UserRole.ADMIN)
        url, body, headers = f"/api/v1/discord/setup/{tour.id}", {"guild_id": "123"}, auth_headers(_token(admin))

        res = await client.post(url, json=body, headers=headers)  # Discord 未連携
        assert res.status_code == 403 and "連携" in res.json()["detail"], res.text

        db.add(DiscordLink(user_id=admin.id, discord_user_id="2", access_token="admin-token",
                           linked_at=datetime.now(UTC)))
        await db.flush()
        routes["/users/@me/guilds"] = httpx.Response(200, json=[{"id": "123", "owner": False, "permissions": "8192"}])
        res = await client.post(url, json=body, headers=headers)  # 連携済みでもサーバー管理権限なし
        assert res.status_code == 403, res.text
        assert calls[-1].headers["Authorization"] == "Bearer admin-token"
        assert (await db.execute(select(DiscordServer).where(DiscordServer.tournament_id == tour.id))).first() is None

        routes["/users/@me/guilds"] = httpx.Response(200, json=[{"id": "123", "owner": False, "permissions": str(0x20)}])
        res = await client.post(url, json=body, headers=headers)
        assert res.status_code == 201, res.text

    @pytest.mark.asyncio
    async def test_設定状態のIDは主催者と管理者にだけ見える(self, client: AsyncClient, db, mem_cache, admin_token):
        owner, tour = await _organizer_with_tournament(db, token=None)
        db.add(DiscordServer(tournament_id=tour.id, guild_id="123", status="ready",
                             role_ids={"admin": "1"}, category_ids={"ARCHIVE": "2"},
                             created_at=datetime.now(UTC)))
        await db.flush()
        stranger = await f.make_user(db)
        url = f"/api/v1/discord/setup/{tour.id}"

        for headers in ({}, auth_headers(_token(stranger)), {"Authorization": "Bearer garbage"}):
            data = (await client.get(url, headers=headers)).json()["data"]
            assert data["status"] == "ready"
            assert not {"guild_id", "role_ids", "category_ids"} & data.keys()

        for token in (_token(owner), admin_token):
            data = (await client.get(url, headers=auth_headers(token))).json()["data"]
            assert data["guild_id"] == "123" and data["role_ids"] == {"admin": "1"}
