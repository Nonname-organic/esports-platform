"""SEC-*: OWASP/認可/JWT/SQLi/Bot secret。"""

import pytest
from httpx import AsyncClient


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec001_protected_requires_auth(client: AsyncClient):
    """SEC-001: token無しで保護APIは401。"""
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await client.get("/api/v1/notifications")).status_code == 401
    assert (await client.get("/api/v1/tournaments/mine")).status_code == 401


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec002_rbac_player_cannot_organizer(client: AsyncClient, player_token: str):
    """SEC-002: playerはorganizer専用APIで403。"""
    r = await client.get("/api/v1/tournaments/mine", headers=_h(player_token))
    assert r.status_code == 403


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec002b_admin_only_forbidden_for_player(client: AsyncClient, player_token: str):
    r = await client.get("/api/v1/admin/dashboard", headers=_h(player_token))
    assert r.status_code == 403


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec005_jwt_tampered_rejected(client: AsyncClient):
    """SEC-005: 改ざん/不正JWTは401。"""
    for bad in ("not.a.jwt", "Bearer", "a.b.c", ""):
        r = await client.get("/api/v1/auth/me", headers=_h(bad))
        assert r.status_code == 401


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec003_sql_injection_safe(client: AsyncClient):
    """SEC-003: SQLiペイロードでも500/漏洩なし（ORMパラメタ化）。"""
    r = await client.get("/api/v1/tournaments", params={"game": "' OR 1=1--"})
    assert r.status_code in (200, 422)  # enum検証 or 空。500は不可
    r2 = await client.get("/api/v1/tournaments", params={"q": "'; DROP TABLE tournaments;--"})
    assert r2.status_code in (200, 422)


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec009_bot_requires_secret(client: AsyncClient):
    """SEC-009/BOT-001/002: /bot/* はX-Bot-Secret必須・誤りは401。"""
    assert (await client.get("/api/v1/bot/resolve")).status_code == 401
    r = await client.get("/api/v1/bot/resolve", headers={"X-Bot-Secret": "wrong-secret"})
    assert r.status_code == 401
