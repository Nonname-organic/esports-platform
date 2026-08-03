"""ranking_snapshots — 週次ランキングスナップショット（順位変動表示の基準点）

Revision ID: 023
Revises: 022
Create Date: 2026-08-03 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ranking_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", sa.String(10), nullable=False),
        sa.Column("season", sa.String(10), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("rp", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.Date(), nullable=False),
    )
    op.create_index(
        "ix_ranking_snapshots_lookup", "ranking_snapshots", ["scope", "season", "captured_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_ranking_snapshots_lookup", table_name="ranking_snapshots")
    op.drop_table("ranking_snapshots")
