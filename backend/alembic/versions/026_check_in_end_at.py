"""チェックイン終了時刻を追加

チェックインは「開始〜終了の時間幅の間だけ」受け付ける仕様にするため、
既存の check_in_start_at と対になる終了時刻を持たせる。

Revision ID: 026_check_in_end_at
Revises: 025_tournament_approval_mode
"""
from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tournaments",
        sa.Column("check_in_end_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tournaments", "check_in_end_at")
