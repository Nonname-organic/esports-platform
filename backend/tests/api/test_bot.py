"""BOT-*: /bot/* サービス認証。

注: settings.BOT_API_TOKEN がテスト環境で未設定の場合、verify_bot_secret は常に401。
よって「secret必須」「誤り拒否」を最低限保証する（権威RBACの結合は §integration で）。
"""

import pytest
from httpx import AsyncClient


@pytest.mark.security
@pytest.mark.asyncio
async def test_bot001_resolve_requires_secret(client: AsyncClient):
    assert (await client.get("/api/v1/bot/resolve")).status_code == 401


@pytest.mark.security
@pytest.mark.asyncio
async def test_bot002_wrong_secret_rejected(client: AsyncClient):
    r = await client.get("/api/v1/bot/resolve", headers={"X-Bot-Secret": "definitely-wrong"})
    assert r.status_code == 401


@pytest.mark.security
@pytest.mark.asyncio
async def test_bot_router_mounted_not_404(client: AsyncClient):
    """/bot/* ルータがマウントされている（401であって404ではない＝ルート存在）。"""
    r = await client.get("/api/v1/bot/resolve")
    assert r.status_code != 404
