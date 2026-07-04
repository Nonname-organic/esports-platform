"""add tournaments.attachments (file attachments for description)

Revision ID: 014
Revises: 013
Create Date: 2026-07-04 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tournaments",
        sa.Column("attachments", postgresql.JSONB(), nullable=True, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("tournaments", "attachments")
