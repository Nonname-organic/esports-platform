"""
Notification Service
- 通知のCRUD
- WebSocket Push（Redis Pub/Sub経由）
- 型は既存 NotificationType enum を再利用しつつ、汎用通知は general を使用
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.models.enums import NotificationType, NotificationChannel
from app.models.tournament import Notification


# 要件の通知種別 → 既存enum へのマッピング
NOTIFICATION_TYPE_MAP = {
    "tournament_invite": NotificationType.GENERAL,
    "team_invite": NotificationType.GENERAL,
    "application_approved": NotificationType.REGISTRATION_APPROVED,
    "application_rejected": NotificationType.REGISTRATION_REJECTED,
    "match_reminder": NotificationType.MATCH_SCHEDULED,
    "checkin_reminder": NotificationType.CHECK_IN_REMINDER,
    "result_updated": NotificationType.MATCH_RESULT,
    "ranking_updated": NotificationType.GENERAL,
    "system_notice": NotificationType.GENERAL,
}


class NotificationService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    async def create(
        self,
        user_id: uuid.UUID,
        ntype: str,
        title: str,
        body: Optional[str] = None,
        action_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Notification:
        enum_type = NOTIFICATION_TYPE_MAP.get(ntype, NotificationType.GENERAL)
        notif = Notification(
            user_id=user_id,
            type=enum_type,
            channel=NotificationChannel.IN_APP,
            title=title,
            body=body or "",
            action_url=action_url,
            extra_data={**(metadata or {}), "subtype": ntype},
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(notif)
        await self._db.flush()

        # WebSocket Push（Redis Pub/Sub）
        await self._publish_push(user_id, notif)
        return notif

    async def _publish_push(self, user_id: uuid.UUID, notif: Notification) -> None:
        try:
            redis = self._cache._redis if hasattr(self._cache, "_redis") else None
            payload = {
                "type": "notification",
                "data": {
                    "id": str(notif.id),
                    "title": notif.title,
                    "body": notif.body,
                    "action_url": notif.action_url,
                    "created_at": notif.created_at.isoformat(),
                },
            }
            import json
            if redis:
                await redis.publish(f"notifications:{user_id}", json.dumps(payload))
        except Exception:
            pass  # Push失敗は通知作成を妨げない

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        only_unread: bool = False,
        search: Optional[str] = None,
        limit: int = 30,
        cursor: Optional[uuid.UUID] = None,
    ) -> tuple[list[Notification], bool]:
        q = select(Notification).where(Notification.user_id == user_id)
        if only_unread:
            q = q.where(Notification.is_read == False)
        if search:
            q = q.where(Notification.title.ilike(f"%{search}%"))
        if cursor:
            ref = await self._db.scalar(select(Notification).where(Notification.id == cursor))
            if ref:
                q = q.where(Notification.created_at < ref.created_at)
        q = q.order_by(Notification.created_at.desc()).limit(limit + 1)

        result = await self._db.execute(q)
        rows = list(result.scalars().all())
        has_next = len(rows) > limit
        return rows[:limit], has_next

    async def unread_count(self, user_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar_one()

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        await self._db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        await self._db.flush()

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        result = await self._db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        await self._db.flush()
        return result.rowcount or 0

    async def delete(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        notif = await self._db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        if notif:
            await self._db.delete(notif)
            await self._db.flush()

    @staticmethod
    def to_schema(n: Notification) -> dict:
        subtype = (n.extra_data or {}).get("subtype") if n.extra_data else None
        return {
            "id": n.id,
            "type": subtype or (n.type.value if hasattr(n.type, "value") else str(n.type)),
            "title": n.title,
            "body": n.body,
            "is_read": n.is_read,
            "action_url": n.action_url,
            "metadata": n.extra_data,
            "created_at": n.created_at,
        }
