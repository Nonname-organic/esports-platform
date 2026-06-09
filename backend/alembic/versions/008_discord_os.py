"""Discord Tournament OS: command metrics, bot error logs, match disputes,
registration check-in fields, discord_links lookup index

Revision ID: 008
Revises: 007
Create Date: 2026-06-09 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tournament_registrations に check-in 列を追加（登録単位の出欠） ──────────
    op.add_column(
        "tournament_registrations",
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tournament_registrations",
        sa.Column("checked_in_via", sa.String(20), nullable=True),  # discord / web / admin
    )

    # ── discord_links: discord_user_id の逆引きインデックスは 006 で作成済みのため
    #    ここでは作成しない（重複作成を避ける）。

    # ── command_metrics（コマンド利用履歴） ─────────────────────────────────────
    op.create_table(
        "command_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("guild_id", sa.String(50), nullable=True),
        sa.Column("discord_user_id", sa.String(50), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("command", sa.String(64), nullable=False),
        sa.Column("success", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("error_type", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_command_metrics_command", "command_metrics", ["command"])
    op.create_index("idx_command_metrics_guild", "command_metrics", ["guild_id"])
    op.create_index("idx_command_metrics_user", "command_metrics", ["discord_user_id"])
    op.create_index("idx_command_metrics_created", "command_metrics", ["created_at"])

    # ── bot_error_logs（Botエラーログ） ─────────────────────────────────────────
    op.create_table(
        "bot_error_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("guild_id", sa.String(50), nullable=True),
        sa.Column("discord_user_id", sa.String(50), nullable=True),
        sa.Column("command", sa.String(64), nullable=True),
        sa.Column("error_type", sa.String(128), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("traceback", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_bot_error_logs_created", "bot_error_logs", ["created_at"])

    # ── match_disputes（結果異議） ──────────────────────────────────────────────
    op.create_table(
        "match_disputes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raised_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("discord_user_id", sa.String(50), nullable=True),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_match_disputes_match", "match_disputes", ["match_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_match_disputes_match", "match_disputes")
    op.drop_table("match_disputes")
    op.drop_index("idx_bot_error_logs_created", "bot_error_logs")
    op.drop_table("bot_error_logs")
    op.drop_index("idx_command_metrics_created", "command_metrics")
    op.drop_index("idx_command_metrics_user", "command_metrics")
    op.drop_index("idx_command_metrics_guild", "command_metrics")
    op.drop_index("idx_command_metrics_command", "command_metrics")
    op.drop_table("command_metrics")
    op.drop_column("tournament_registrations", "checked_in_via")
    op.drop_column("tournament_registrations", "checked_in_at")
