"""
Discord連携 API
- 大会Discordセットアップ
- OAuth連携 / コード連携
"""

import secrets
import string
import uuid

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.dependencies import Cache, CurrentUser, DBSession, OrganizerUser
from app.schemas.common import Response
from app.services.discord_service import DiscordService

router = APIRouter(prefix="/discord", tags=["Discord連携"])

LINK_CODE_TTL = 300  # 連携コードの有効期間（秒）


class SetupRequest(BaseModel):
    guild_id: str


class OAuthCallbackRequest(BaseModel):
    code: str


@router.post("/link-code")
async def issue_link_code(db: DBSession, cache: Cache, current_user: CurrentUser):
    """Discordコード連携用のワンタイムコードを発行（Webログインユーザー）。

    ユーザーはこのコードを Discord で `/link code:XXXX` として入力し、
    自分のDiscordアカウントとプラットフォームアカウントを紐付ける。
    """
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    await cache.set(f"discord_link_code:{code}", {"user_id": str(current_user.id)}, ttl=LINK_CODE_TTL)
    return {"data": {"code": code, "expires_in": LINK_CODE_TTL}}


@router.get("/oauth/login")
async def oauth_login_url(db: DBSession, cache: Cache, current_user: CurrentUser):
    """Discord認可URLを返す"""
    service = DiscordService(db, cache)
    return {"data": {"url": service.oauth_login_url()}}


@router.post("/oauth/callback")
async def oauth_callback(
    data: OAuthCallbackRequest, db: DBSession, cache: Cache, current_user: CurrentUser
):
    """OAuth codeを交換してDiscordアカウントを紐付け"""
    service = DiscordService(db, cache)
    link = await service.exchange_oauth_code(current_user.id, data.code)
    return {"data": {
        "discord_user_id": link.discord_user_id,
        "discord_username": link.discord_username,
    }}


@router.get("/link")
async def get_link(db: DBSession, cache: Cache, current_user: CurrentUser):
    """Discord紐付け状態"""
    service = DiscordService(db, cache)
    link = await service.get_link(current_user.id)
    if not link:
        return {"data": None}
    return {"data": {
        "discord_user_id": link.discord_user_id,
        "discord_username": link.discord_username,
        "linked_at": link.linked_at.isoformat(),
    }}


@router.delete("/link", status_code=204)
async def unlink_discord(db: DBSession, cache: Cache, current_user: CurrentUser):
    """Discord連携を解除（自分の連携を削除）。"""
    from sqlalchemy import select as _select

    from app.models.discord import DiscordLink
    link = await db.scalar(_select(DiscordLink).where(DiscordLink.user_id == current_user.id))
    if link:
        await db.delete(link)
        await db.flush()


@router.post("/setup/{tournament_id}", status_code=201)
async def setup_discord(
    tournament_id: uuid.UUID, data: SetupRequest,
    db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    """大会用Discordサーバーのテンプレート生成を依頼"""
    service = DiscordService(db, cache)
    server = await service.setup_tournament(tournament_id, data.guild_id)
    return {"data": {
        "id": str(server.id),
        "tournament_id": str(server.tournament_id),
        "guild_id": server.guild_id,
        "status": server.status,
    }}


@router.get("/setup/{tournament_id}")
async def get_discord_setup(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    """大会のDiscord設定状態"""
    service = DiscordService(db, cache)
    server = await service.get_server(tournament_id)
    if not server:
        return {"data": None}
    return {"data": {
        "id": str(server.id),
        "guild_id": server.guild_id,
        "status": server.status,
        "role_ids": server.role_ids,
        "category_ids": server.category_ids,
    }}
