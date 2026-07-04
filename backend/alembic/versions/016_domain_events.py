"""add domain_events (Event Log + Transactional Outbox / ADR-0001)

Revision ID: 016
Revises: 015
Create Date: 2026-07-04 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_events",
        # 識別・版
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        # 実行主体
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(16), nullable=False, server_default="user"),
        sa.Column("actor_ip", postgresql.INET(), nullable=True),
        # 発生元
        sa.Column("producer", sa.String(24), nullable=False, server_default="core"),
        sa.Column("service", sa.String(16), nullable=False, server_default="api"),
        # 対象
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        # 変更内容
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        # 相関・冪等
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=True),
        # 可視性
        sa.Column("visibility", sa.String(16), nullable=False, server_default="internal"),
        # Outbox
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatch_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Outbox キュー（未dispatch のみ）: 部分Index
    op.create_index(
        "ix_events_undispatched", "domain_events", ["created_at"],
        postgresql_where=sa.text("dispatched_at IS NULL"),
    )
    # 対象別（監査/活動ビュー）
    op.create_index(
        "ix_events_entity", "domain_events", ["entity_type", "entity_id", "created_at"],
    )
    # 可視性別（監査 internal / 活動 public）
    op.create_index(
        "ix_events_visibility", "domain_events", ["visibility", "type", "created_at"],
    )
    # 冪等キー（存在する行のみ一意）
    op.create_index(
        "ix_events_idem", "domain_events", ["idempotency_key"], unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_events_idem", "domain_events")
    op.drop_index("ix_events_visibility", "domain_events")
    op.drop_index("ix_events_entity", "domain_events")
    op.drop_index("ix_events_undispatched", "domain_events")
    op.drop_table("domain_events")
