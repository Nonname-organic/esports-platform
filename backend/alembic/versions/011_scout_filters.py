"""add scout filter fields to scout_profiles and teams

Revision ID: 011
Revises: 010
Create Date: 2026-07-04 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # scout_profiles: Team Discovery filter fields
    op.add_column("scout_profiles", sa.Column("activity_level", sa.String(20), nullable=True))
    op.add_column("scout_profiles", sa.Column("active_hours", sa.String(20), nullable=True))
    op.add_column("scout_profiles", sa.Column("team_min_age", sa.Integer(), nullable=True))
    op.add_column("scout_profiles", sa.Column("team_max_age", sa.Integer(), nullable=True))
    op.add_column("scout_profiles", sa.Column("premier_active", sa.Boolean(), nullable=False, server_default="false"))

    # teams: region field (country was used before)
    op.add_column("teams", sa.Column("region", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("scout_profiles", "activity_level")
    op.drop_column("scout_profiles", "active_hours")
    op.drop_column("scout_profiles", "team_min_age")
    op.drop_column("scout_profiles", "team_max_age")
    op.drop_column("scout_profiles", "premier_active")
    op.drop_column("teams", "region")
