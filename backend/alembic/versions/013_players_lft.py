"""add players_lft table for LFT (Looking for Team)

Revision ID: 013
Revises: 012
Create Date: 2026-07-04 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "players_lft",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("roles", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("current_rank", sa.String(50), nullable=False),
        sa.Column("peak_rank", sa.String(50), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("activity_time", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("experience", sa.String(30), nullable=True),
        sa.Column("premier", sa.String(20), nullable=True),
        sa.Column("agents", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("discord", sa.String(100), nullable=True),
        sa.Column("twitter", sa.String(100), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_players_lft_player_id", "players_lft", ["player_id"])
    op.create_index("ix_players_lft_status", "players_lft", ["status"])


def downgrade() -> None:
    op.drop_index("ix_players_lft_status", "players_lft")
    op.drop_index("ix_players_lft_player_id", "players_lft")
    op.drop_table("players_lft")
