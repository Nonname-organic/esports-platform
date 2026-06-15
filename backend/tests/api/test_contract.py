"""CONTRACT — OpenAPI 契約スナップショット。

破壊的変更（重要エンドポイントの削除・メソッド喪失）を検知する。
クライアント(frontend / discord-bot)が依存する契約を固定する。
"""

import pytest
from httpx import AsyncClient

# クライアントが依存する重要エンドポイント（path, method）。削除=破壊的変更。
CRITICAL_CONTRACT = [
    ("/api/v1/auth/register", "post"),
    ("/api/v1/auth/login", "post"),
    ("/api/v1/auth/me", "get"),
    ("/api/v1/tournaments", "get"),
    ("/api/v1/tournaments", "post"),
    ("/api/v1/tournaments/{tournament_id}", "get"),
    ("/api/v1/tournaments/{tournament_id}/bracket", "get"),
    ("/api/v1/matches/{match_id}", "get"),
    ("/api/v1/teams", "get"),
    ("/api/v1/players", "get"),
    ("/api/v1/scout/players", "get"),
    ("/api/v1/notifications", "get"),
    ("/api/v1/analytics/maps/stats", "get"),
]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_openapi_served(client: AsyncClient):
    res = await client.get("/openapi.json")
    assert res.status_code == 200
    spec = res.json()
    assert spec.get("openapi", "").startswith("3.")
    assert "paths" in spec and spec["paths"]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_critical_endpoints_present(client: AsyncClient):
    spec = (await client.get("/openapi.json")).json()
    paths = spec["paths"]
    missing = []
    for path, method in CRITICAL_CONTRACT:
        if path not in paths or method not in paths[path]:
            missing.append(f"{method.upper()} {path}")
    assert not missing, f"契約破壊（消失したエンドポイント）: {missing}"
