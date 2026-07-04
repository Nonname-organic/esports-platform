"""AuditService — 監査ログ閲覧（機能① / ADR-0012）。

list_audit（internal限定）を読み、正規化 DTO（AuditLogItem）へ変換する。
actor_id → username は一括解決して N+1 を避ける。before/after/IP は権限保持者向け（監査は
internal 権限者しか到達しないため DTO 全体を返す）。
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_event import DomainEvent
from app.models.user import User
from app.repositories.event import EventRepository


class AuditService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._repo = EventRepository(db)

    async def list(
        self, *, entity_type: Optional[str] = None, entity_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None, action: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> list[dict]:
        events = await self._repo.list_audit(
            entity_type=entity_type, entity_id=entity_id,
            actor_id=actor_id, event_type=action, limit=limit, offset=offset,
        )
        names = await self._resolve_actor_names(events)
        return [self._to_item(e, names) for e in events]

    async def _resolve_actor_names(self, events: list[DomainEvent]) -> dict[uuid.UUID, str]:
        """actor_id を一括で username 解決（N+1回避）。"""
        ids = {e.actor_id for e in events if e.actor_id}
        if not ids:
            return {}
        rows = (await self._db.execute(
            select(User.id, User.username).where(User.id.in_(ids))
        )).all()
        return {uid: uname for uid, uname in rows}

    @staticmethod
    def _to_item(e: DomainEvent, names: dict) -> dict:
        return {
            "id": str(e.id),
            "action": e.type,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "actor_name": names.get(e.actor_id) if e.actor_id else None,
            "actor_type": e.actor_type,
            "actor_ip": str(e.actor_ip) if e.actor_ip else None,
            "entity_type": e.entity_type,
            "entity_id": str(e.entity_id),
            "before": e.before,
            "after": e.after,
            "created_at": (e.occurred_at or e.created_at).isoformat(),
        }
