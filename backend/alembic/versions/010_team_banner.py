"""add teams.banner_url (schema/service referenced it but column was missing)

Revision ID: 010
Revises: 009
Create Date: 2026-06-14 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("banner_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("teams", "banner_url")
