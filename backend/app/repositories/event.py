"""EventRepository — domain_events の永続化・読み取り（3層維持）。

P0-3: 追記(add) と対象別読み取り。
P0-4: Outbox の claim/dispatch 更新メソッドをここに追加する（本Repositoryを拡張）。
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_event import DomainEvent
from app.repositories.base import BaseRepository

# Outbox 再試行上限（ADR-0007）。到達したイベントは Terminal Failure として
# 取得クエリから除外され、再試行されない（キューを塞がない）。
MAX_DISPATCH_ATTEMPTS = 10

# ロックが stale とみなされるまでの秒数（worker クラッシュ時の回収）。
_LOCK_STALE_SECONDS = 300


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventRepository(BaseRepository[DomainEvent]):
    def __init__(self, db: AsyncSession):
        super().__init__(DomainEvent, db)

    async def add(self, event: DomainEvent) -> DomainEvent:
        """呼び出し元と同一トランザクションで INSERT（commit しない）。"""
        self._db.add(event)
        await self._db.flush()   # id採番・制約違反をこの時点で顕在化。commit は呼び出し側Tx
        return event

    # ── Outbox（P0-4 / ADR-0007） ───────────────────────────────────────────
    async def claim_undispatched(self, worker_id: str, limit: int = 100) -> list[DomainEvent]:
        """未dispatch かつ再試行上限未満の行を FOR UPDATE SKIP LOCKED で取得しロックする。

        Terminal Failure（dispatch_attempts >= MAX）は除外（再試行しない/キューを塞がない）。
        stale ロック（worker クラッシュ）は回収する。commit は呼び出し側（relay）が行う。
        """
        stale_before = _utcnow() - timedelta(seconds=_LOCK_STALE_SECONDS)
        q = (
            select(DomainEvent)
            .where(
                DomainEvent.dispatched_at.is_(None),
                DomainEvent.dispatch_attempts < MAX_DISPATCH_ATTEMPTS,
                or_(DomainEvent.locked_at.is_(None), DomainEvent.locked_at < stale_before),
            )
            .order_by(DomainEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = list((await self._db.execute(q)).scalars().all())
        now = _utcnow()
        for r in rows:
            r.locked_at = now
            r.locked_by = worker_id
        await self._db.flush()
        return rows

    async def mark_dispatched(self, event: DomainEvent) -> None:
        event.dispatched_at = _utcnow()
        event.locked_at = None
        event.locked_by = None
        await self._db.flush()

    async def mark_failed(self, event: DomainEvent, error: str) -> bool:
        """失敗を記録し attempts を +1。Terminal（上限到達）なら True を返す。"""
        event.dispatch_attempts += 1
        event.last_error = (error or "")[:1000]
        event.locked_at = None
        event.locked_by = None
        await self._db.flush()
        return event.dispatch_attempts >= MAX_DISPATCH_ATTEMPTS

    # ── 読み取り: 監査（internal限定 / ADR-0011） ─────────────────────────
    async def list_audit(
        self, *, entity_type: Optional[str] = None, entity_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None, event_type: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> list[DomainEvent]:
        """監査ビュー。**visibility='internal' に限定**（公開イベントは含めない）。"""
        q = select(DomainEvent).where(DomainEvent.visibility == "internal")
        if entity_type:
            q = q.where(DomainEvent.entity_type == entity_type)
        if entity_id:
            q = q.where(DomainEvent.entity_id == entity_id)
        if actor_id:
            q = q.where(DomainEvent.actor_id == actor_id)
        if event_type:
            q = q.where(DomainEvent.type == event_type)
        q = q.order_by(DomainEvent.created_at.desc()).limit(limit).offset(offset)
        return list((await self._db.execute(q)).scalars().all())

    # ── 読み取り: 活動（public限定・漏洩防止を1箇所で保証 / ADR-0011） ────
    async def list_activity(
        self, *, entity_type: Optional[str] = None, entity_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None, limit: int = 30, offset: int = 0,
    ) -> list[DomainEvent]:
        """公開タイムライン。**visibility='public' に限定**（internal 監査は絶対に含めない）。"""
        q = select(DomainEvent).where(DomainEvent.visibility == "public")
        if entity_type:
            q = q.where(DomainEvent.entity_type == entity_type)
        if entity_id:
            q = q.where(DomainEvent.entity_id == entity_id)
        if actor_id:
            q = q.where(DomainEvent.actor_id == actor_id)
        q = q.order_by(DomainEvent.created_at.desc()).limit(limit).offset(offset)
        return list((await self._db.execute(q)).scalars().all())

    # P0-4 で追加予定:
    #   async def claim_undispatched(self, worker_id, limit) -> list[DomainEvent]
    #   async def mark_dispatched(self, event) / mark_failed(self, event, error)
