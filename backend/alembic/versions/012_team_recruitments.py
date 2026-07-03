"""add teams_recruitments table for LFP (Looking for Players)

Revision ID: 012
Revises: 011
Create Date: 2026-07-04 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams_recruitments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("roles", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("headcount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("min_rank", sa.String(50), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("activity_time", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("activity_level", sa.String(30), nullable=True),
        sa.Column("tournaments", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("age_requirement", sa.String(30), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("team_intro", sa.Text(), nullable=True),
        sa.Column("discord", sa.String(100), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_recruitments_team_id", "teams_recruitments", ["team_id"])
    op.create_index("ix_teams_recruitments_status", "teams_recruitments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_teams_recruitments_status", "teams_recruitments")
    op.drop_index("ix_teams_recruitments_team_id", "teams_recruitments")
    op.drop_table("teams_recruitments")
