"""
Riot Integration API (VALORANT)
- Riot ID 紐付け
- 手動同期
- プロフィール / 試合データ取得
"""

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.v1.analytics import _require_player_stats_public
from app.core.dependencies import Cache, CurrentUser, DBSession, OptionalUser
from app.services.riot_service import RiotService

router = APIRouter(prefix="/riot", tags=["Riot連携"])


class RiotLinkRequest(BaseModel):
    player_id: uuid.UUID
    riot_id: str = Field(..., max_length=61, description="Name#TAG形式")


@router.post("/link")
async def link_riot(
    data: RiotLinkRequest, db: DBSession, cache: Cache, current_user: CurrentUser
):
    """Riot IDをプレイヤーに紐付け（本人・管理者のみ）"""
    service = RiotService(db, cache)
    await service.require_own_player(data.player_id, current_user)
    profile = await service.link(data.player_id, data.riot_id)
    return {"data": {
        "player_id": str(profile.player_id),
        "riot_id": profile.riot_id,
        "puuid": profile.puuid,
        "region": profile.region,
        "synced_at": profile.synced_at.isoformat() if profile.synced_at else None,
    }}


@router.post("/sync/{player_id}")
async def sync_riot(
    player_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser
):
    """Riot APIから試合データを手動同期（本人・管理者のみ）"""
    service = RiotService(db, cache)
    await service.require_own_player(player_id, current_user)
    result = await service.sync(player_id)
    return {"data": result}


@router.get("/profile/{player_id}")
async def get_riot_profile(
    player_id: uuid.UUID, db: DBSession, cache: Cache, viewer: OptionalUser,
) -> dict[str, dict[str, Any] | None]:
    """Riotプロフィール + 取得済み試合データ（詳細スタッツ非公開の選手は本人・管理者のみ）"""
    await _require_player_stats_public(db, player_id, viewer)
    service = RiotService(db, cache)
    profile = await service.get_profile(player_id)
    if not profile:
        return {"data": None}
    matches = await service.get_riot_matches(player_id)
    return {"data": {
        "player_id": str(profile.player_id),
        "riot_id": profile.riot_id,
        "region": profile.region,
        "current_rank": profile.current_rank,
        "peak_rank": profile.peak_rank,
        "synced_at": profile.synced_at.isoformat() if profile.synced_at else None,
        "matches": matches,
    }}
