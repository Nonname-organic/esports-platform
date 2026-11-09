"""パスワードの変更・再設定で、それ以前に発行したトークンを失効させる（RC3 の S9）。

トークンにはパスワードのハッシュから作る印（pwv）が入っていて、認証と更新のたびに
今のハッシュの印と比べる。変更した本人の端末のトークンも、別の端末のトークンも通らない。
"""
import uuid

import pytest
from httpx import AsyncClient

from app.core.dependencies import get_cache
from app.core.security import create_access_token, create_refresh_token
from app.main import app
from tests import factories as f
from tests.conftest import auth_headers

PW, NEW_PW = "Passw0rd1", "NewPassw0rd2"


class _DictCache:
    """再設定トークンを覚えておけるキャッシュ（テストの既定のキャッシュは何も覚えない）。"""

    def __init__(self):
        self.data: dict = {}

    async def get(self, key): return self.data.get(key)
    async def set(self, key, value, ttl=None): self.data[key] = value
    async def delete(self, key): self.data.pop(key, None)
    async def delete_pattern(self, pattern): return 0
    async def acquire_lock(self, key, ttl=10): return True
    async def release_lock(self, key): pass
    async def publish(self, channel, message): pass


async def _login(client: AsyncClient, email: str, password: str):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _me(client: AsyncClient, access: str) -> int:
    return (await client.get("/api/v1/auth/me", headers=auth_headers(access))).status_code


async def _refresh(client: AsyncClient, refresh: str):
    return await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})


async def _sessions(client: AsyncClient, email: str, n: int) -> list[dict]:
    """同じ利用者が n 台の端末でログインした状態。"""
    out = []
    for _ in range(n):
        res = await _login(client, email, PW)
        assert res.status_code == 200, res.text
        out.append(res.json())
    return out


def _assert_revoked(status: int) -> None:
    assert status == 401


class TestPasswordChangeRevokesSessions:
    @pytest.mark.asyncio
    async def test_変更前のセッションは本人の端末も別の端末も通らない(self, client: AsyncClient, db):
        user = await f.make_user(db, email="s9-change@example.com", password=PW)
        mine, other = await _sessions(client, user.email, 2)
        assert await _me(client, mine["access_token"]) == 200 and await _me(client, other["access_token"]) == 200

        res = await client.patch("/api/v1/auth/password", headers=auth_headers(mine["access_token"]),
                                 json={"current_password": PW, "new_password": NEW_PW})
        assert res.status_code == 204, res.text

        for s in (mine, other):
            _assert_revoked(await _me(client, s["access_token"]))
            res = await _refresh(client, s["refresh_token"])
            _assert_revoked(res.status_code)
            assert "もう一度ログイン" in res.json()["detail"]
        # 失効したトークンでは、もう一度パスワードを変えることもできない
        res = await client.patch("/api/v1/auth/password", headers=auth_headers(other["access_token"]),
                                 json={"current_password": NEW_PW, "new_password": "Another3Pass"})
        _assert_revoked(res.status_code)

        assert (await _login(client, user.email, PW)).status_code == 401  # 古いパスワード
        res = await _login(client, user.email, NEW_PW)
        assert res.status_code == 200, res.text
        fresh = res.json()
        assert await _me(client, fresh["access_token"]) == 200
        res = await _refresh(client, fresh["refresh_token"])
        assert res.status_code == 200, res.text
        assert await _me(client, res.json()["access_token"]) == 200

    @pytest.mark.asyncio
    async def test_再設定でも変更前のセッションは通らない(self, client: AsyncClient, db):
        cache = _DictCache()
        app.dependency_overrides[get_cache] = lambda: cache
        user = await f.make_user(db, email="s9-reset@example.com", password=PW)
        (session,) = await _sessions(client, user.email, 1)
        token = uuid.uuid4().hex
        cache.data[f"pwreset:{token}"] = str(user.id)

        res = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": NEW_PW})
        assert res.status_code == 204, res.text

        _assert_revoked(await _me(client, session["access_token"]))
        _assert_revoked((await _refresh(client, session["refresh_token"])).status_code)
        res = await _login(client, user.email, NEW_PW)
        assert res.status_code == 200 and await _me(client, res.json()["access_token"]) == 200

    @pytest.mark.asyncio
    async def test_公開APIでは失効したトークンを未ログインとして扱う(self, client: AsyncClient, db):
        """任意認証（OptionalUser）の経路も同じ確認を通る。詳細スタッツ非公開の本人で確かめる。"""
        user = await f.make_user(db, email="s9-optional@example.com", password=PW)
        player = await f.make_player(db, user=user, stats_public=False)
        (session,) = await _sessions(client, user.email, 1)
        url = f"/api/v1/players/{player.id}/career"
        assert (await client.get(url, headers=auth_headers(session["access_token"]))).status_code == 200

        await client.patch("/api/v1/auth/password", headers=auth_headers(session["access_token"]),
                           json={"current_password": PW, "new_password": NEW_PW})
        assert (await client.get(url, headers=auth_headers(session["access_token"]))).status_code == 403
        fresh = (await _login(client, user.email, NEW_PW)).json()
        assert (await client.get(url, headers=auth_headers(fresh["access_token"]))).status_code == 200


class TestSessionsStillWork:
    @pytest.mark.asyncio
    async def test_パスワードを変えなければ更新はこれまでどおり続けられる(self, client: AsyncClient, db):
        user = await f.make_user(db, email="s9-refresh@example.com", password=PW)
        (session,) = await _sessions(client, user.email, 1)
        refresh = session["refresh_token"]
        for _ in range(3):  # 更新のたびに新しい組を受け取り、続けて使える
            res = await _refresh(client, refresh)
            assert res.status_code == 200, res.text
            assert await _me(client, res.json()["access_token"]) == 200
            refresh = res.json()["refresh_token"]
        assert await _me(client, session["access_token"]) == 200  # 期限内の元のトークンも通る

    @pytest.mark.asyncio
    async def test_印の無い以前のトークンは通らない(self, client: AsyncClient, db):
        """この仕組みより前に発行したトークン。デプロイ後は一度ログインし直しになる。"""
        user = await f.make_user(db, email="s9-legacy@example.com", password=PW)
        _assert_revoked(await _me(client, create_access_token(str(user.id), {"role": user.role.value})))
        _assert_revoked((await _refresh(client, create_refresh_token(str(user.id)))).status_code)
        _assert_revoked(await _me(client, create_access_token(str(user.id), {"role": "player", "pwv": "x" * 32})))
