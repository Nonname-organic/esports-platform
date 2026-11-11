"""対戦チームによる試合結果の報告（相手チームの確認待ち）を保存する表

これまで Discord Bot だけが Redis に24時間保持していた。Web からも報告・確認
できるようにし、再起動や期限切れで報告が消えないよう DB に置く。

Revision ID: 029_match_result_reports
Revises: 028_sync_tournament_visibility
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "match_result_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", UUID(as_uuid=True),
                  sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("winner_id", UUID(as_uuid=True),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reported_by_team_id", UUID(as_uuid=True),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reported_by_user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("dispute_reason", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("match_result_reports")
