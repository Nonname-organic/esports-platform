"""EventRepository — domain_events の永続化・読み取り（3層維持）。

P0-3: 追記(add) と対象別読み取り。
P0-4: Outbox の claim/dispatch 更新メソッドをここに追加する（本Repositoryを拡張）。
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_event import DomainEvent
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[DomainEvent]):
    def __init__(self, db: AsyncSession):
        super().__init__(DomainEvent, db)

    async def add(self, event: DomainEvent) -> DomainEvent:
        """呼び出し元と同一トランザクションで INSERT（commit しない）。"""
        self._db.add(event)
        await self._db.flush()   # id採番・制約違反をこの時点で顕在化。commit は呼び出し側Tx
        return event

    # ── 読み取り（監査/活動ビュー・P2でUI化） ──────────────────────────
    async def list_by_entity(
        self, entity_type: str, entity_id: uuid.UUID,
        *, visibility: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> list[DomainEvent]:
        q = select(DomainEvent).where(
            DomainEvent.entity_type == entity_type,
            DomainEvent.entity_id == entity_id,
        )
        if visibility:
            q = q.where(DomainEvent.visibility == visibility)
        q = q.order_by(DomainEvent.created_at.desc()).limit(limit).offset(offset)
        return list((await self._db.execute(q)).scalars().all())

    # P0-4 で追加予定:
    #   async def claim_undispatched(self, worker_id, limit) -> list[DomainEvent]
    #   async def mark_dispatched(self, event) / mark_failed(self, event, error)
