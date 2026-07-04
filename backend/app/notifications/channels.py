"""Channel Provider — 通知チャネルの実装（ADR-0005 / Matrix の channels）。

現在: BrowserChannel(in-app + WSプッシュ) / DiscordChannel(連携ユーザーへDM) / EmailChannel(将来stub)。
新チャネル追加 = ChannelProvider を実装し ChannelRegistry に register するだけ。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.models.enums import NotificationChannel, NotificationType
from app.models.tournament import Notification
from app.services.notification_service import NOTIFICATION_TYPE_MAP

logger = structlog.get_logger()


@dataclass
class Message:
    """1通知の内容（受信者非依存）。"""
    subtype: str
    title: str
    body: str
    action_url: Optional[str] = None
    metadata: Optional[dict] = None


class ChannelProvider(Protocol):
    name: str
    async def send(self, db: AsyncSession, user_id: uuid.UUID, msg: Message) -> bool: ...


class BrowserChannel:
    """アプリ内通知（notifications 行）+ WebSocket プッシュ（Redis pub/sub）。"""
    name = "browser"

    def __init__(self, cache: RedisCache):
        self._cache = cache

    async def send(self, db: AsyncSession, user_id: uuid.UUID, msg: Message) -> bool:
        enum_type = NOTIFICATION_TYPE_MAP.get(msg.subtype, NotificationType.GENERAL)
        notif = Notification(
            user_id=user_id,
            type=enum_type,
            channel=NotificationChannel.IN_APP,
            title=msg.title,
            body=msg.body or "",
            action_url=msg.action_url,
            extra_data={**(msg.metadata or {}), "subtype": msg.subtype},
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notif)
        await db.flush()
        # WebSocket プッシュ（失敗は通知作成を妨げない）
        try:
            redis = getattr(self._cache, "_redis", None)
            if redis:
                await redis.publish(f"notifications:{user_id}", json.dumps({
                    "type": "notification",
                    "data": {
                        "id": str(notif.id), "title": notif.title, "body": notif.body,
                        "action_url": notif.action_url, "created_at": notif.created_at.isoformat(),
                    },
                }))
        except Exception:
            logger.warning("browser_ws_push_failed", user_id=str(user_id))
        return True


class DiscordChannel:
    """Discord 連携済みユーザーへ Bot 経由で DM。"""
    name = "discord"

    def __init__(self, cache: RedisCache):
        self._cache = cache

    async def send(self, db: AsyncSession, user_id: uuid.UUID, msg: Message) -> bool:
        from app.models.discord import DiscordLink
        link = await db.scalar(select(DiscordLink).where(DiscordLink.user_id == user_id))
        if not link:
            return False  # 未連携 = このチャネルは対象外（skip）
        from app.services.discord_service import DiscordEventPublisher
        await DiscordEventPublisher(self._cache).publish("notify_user", {
            "discord_user_id": link.discord_user_id,
            "title": msg.title, "body": msg.body, "action_url": msg.action_url,
        })
        return True


class EmailChannel:
    """メール通知（将来: SES 等）。現在は未設定として no-op。"""
    name = "email"

    async def send(self, db: AsyncSession, user_id: uuid.UUID, msg: Message) -> bool:
        logger.debug("email_channel_not_configured", user_id=str(user_id), subtype=msg.subtype)
        return False


class ChannelRegistry:
    def __init__(self, providers: list[ChannelProvider] | None = None):
        self._by_name: dict[str, ChannelProvider] = {}
        for p in (providers or []):
            self.register(p)

    def register(self, provider: ChannelProvider) -> None:
        self._by_name[provider.name] = provider

    def get(self, name: str) -> Optional[ChannelProvider]:
        return self._by_name.get(name)
