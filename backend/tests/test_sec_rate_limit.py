"""レート制限の識別子の回帰テスト。

Bearer ヘッダの末尾16文字を検証せずに識別子にしていたため、リクエストごとに
でたらめなトークンを付けるだけで毎回新しい枠になり、/auth/login の総当たりを含む
すべての制限をすり抜けられた。
"""
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from redis.exceptions import RedisError
from starlette.requests import Request

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import create_access_token, create_refresh_token
from app.middleware.rate_limit import RateLimitMiddleware

IP = "203.0.113.7"


def _identifier(path: str, auth: str | None) -> str:
    headers = [(b"x-real-ip", IP.encode())]
    if auth is not None:
        headers.append((b"authorization", auth.encode()))
    request = Request({"type": "http", "method": "GET", "path": path, "query_string": b"",
                       "headers": headers, "client": ("10.0.0.1", 1234)})
    return RateLimitMiddleware(app=None)._get_identifier(request)


class TestIdentifier:
    def test_検証できたアクセストークンだけユーザー単位で数える(self):
        sub = str(uuid.uuid4())
        assert _identifier("/api/v1/teams", f"Bearer {create_access_token(sub)}") == f"user:{sub}"
        # 同じユーザーなら別のトークンでも同じ枠
        later = create_access_token(sub, {"role": "player"})
        assert _identifier("/api/v1/teams", f"Bearer {later}") == f"user:{sub}"

    @pytest.mark.parametrize("auth", [
        "Bearer " + secrets.token_urlsafe(24),
        "Bearer a.b.c",
        "Bearer ",
        "Bearer " + jwt.encode({"sub": "x", "type": "access"}, "not-the-secret", algorithm="HS256"),
        "Bearer " + jwt.encode({"sub": "x", "type": "access",
                                "exp": datetime.now(UTC) - timedelta(minutes=1)},
                               settings.SECRET_KEY, algorithm=settings.ALGORITHM),
        "Bearer " + create_refresh_token("x"),
    ])
    def test_検証できないトークンはIPで数える(self, auth):
        assert _identifier("/api/v1/teams", auth) == f"ip:{IP}"

    @pytest.mark.parametrize("path", ["/api/v1/auth/login", "/api/v1/auth/register",
                                      "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password"])
    def test_認証系は正しいトークンが付いていてもIPで数える(self, path):
        assert _identifier(path, f"Bearer {create_access_token(str(uuid.uuid4()))}") == f"ip:{IP}"


async def _redis_or_skip() -> None:
    try:
        await (await get_redis()).ping()
    except (RedisError, OSError):
        pytest.skip("Redis が無いとレート制限は素通しになる（意図した縮退）")


def _fresh_ip() -> str:
    """他のテストや再実行と枠を共有しないよう、毎回別の送信元にする。"""
    return f"test-{uuid.uuid4().hex}"


class TestFakeTokensDoNotGetFreshBuckets:
    @pytest.mark.asyncio
    async def test_でたらめなトークンを付け替えても同じ枠で429になる(self, client: AsyncClient, monkeypatch):
        await _redis_or_skip()
        monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", 3)
        ip = _fresh_ip()
        statuses = [
            (await client.get("/api/v1/players/roles",
                              headers={"Authorization": f"Bearer {secrets.token_urlsafe(24)}", "X-Real-IP": ip})
             ).status_code
            for _ in range(4)
        ]
        assert statuses == [200, 200, 200, 429]

    @pytest.mark.asyncio
    async def test_ログインはトークンの有無や真偽に関係なくIPの枠を共有する(self, client: AsyncClient, monkeypatch):
        await _redis_or_skip()
        monkeypatch.setitem(RateLimitMiddleware.COSTLY_SUFFIXES, "/auth/login", 2)
        ip = _fresh_ip()
        body = {"email": "nobody@test.com", "password": "wrong-password"}
        auths = [f"Bearer {create_access_token(str(uuid.uuid4()))}", f"Bearer {secrets.token_urlsafe(24)}", None]
        statuses = []
        for auth in auths:
            headers = {"X-Real-IP": ip} | ({"Authorization": auth} if auth else {})
            statuses.append((await client.post("/api/v1/auth/login", json=body, headers=headers)).status_code)
        assert statuses[:2] == [401, 401]
        assert statuses[2] == 429
