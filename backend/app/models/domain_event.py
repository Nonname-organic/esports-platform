"""DomainEvent — Event Log 兼 Transactional Outbox（単一テーブル / ADR-0001）。

設計: docs/architecture/PHASED_ARCHITECTURE.md §5, §7
- Envelope 列（§3）+ Outbox 列（§5）を1テーブルに持つ。
- `id` = event_id（Envelope と同一）。
- 監査/活動は `visibility`（internal/public）で論理分離（物理分離は将来トリガーで）。
- P0-4（OutboxRelay）が `dispatched_at IS NULL` の行を拾って dispatch する。
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DomainEvent(Base):
    __tablename__ = "domain_events"

    # ── 識別・版（Envelope） ──────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # ── 実行主体 ──────────────────────────────────────────────────────────
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    actor_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)

    # ── 発生元 ────────────────────────────────────────────────────────────
    producer: Mapped[str] = mapped_column(String(24), nullable=False, default="core")
    service: Mapped[str] = mapped_column(String(16), nullable=False, default="api")

    # ── 対象 ──────────────────────────────────────────────────────────────
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ── 変更内容（PII 非格納：user_id 参照） ─────────────────────────────
    before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # "metadata" は SQLAlchemy Declarative の予約語のため属性名を変更（DBカラム名は維持）
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # ── 相関・冪等 ────────────────────────────────────────────────────────
    # trace_id/correlation_id は受信ヘッダ由来で非UUIDもあり得るため String で保持（堅牢性）
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # ── 可視性（監査 or 公開活動） ───────────────────────────────────────
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="internal")

    # ── Outbox（P0-4 で利用） ────────────────────────────────────────────
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatch_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    def from_envelope(cls, e, *, needs_dispatch: bool) -> "DomainEvent":
        """EventEnvelope から行を生成。

        needs_dispatch=False（純監査など consumer 不要）は dispatched_at を即時に埋め、
        Outbox キュー（dispatched_at IS NULL）に載せない。True は NULL のまま＝要 dispatch。
        """
        return cls(
            id=uuid.UUID(e.event_id),
            event_version=e.event_version,
            type=e.type,
            occurred_at=e.occurred_at,
            actor_id=uuid.UUID(e.actor_id) if e.actor_id else None,
            actor_type=e.actor_type.value,
            actor_ip=e.actor_ip,
            producer=e.producer,
            service=e.service,
            entity_type=e.entity_type,
            entity_id=uuid.UUID(str(e.entity_id)),
            before=e.before,
            after=e.after,
            event_metadata=e.metadata,
            trace_id=e.trace_id,
            correlation_id=e.correlation_id,
            idempotency_key=e.idempotency_key,
            visibility=e.visibility.value,
            dispatched_at=None if needs_dispatch else _utcnow(),
        )
