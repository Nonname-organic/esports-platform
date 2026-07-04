"""add tournaments.rules_doc (section-structured markdown rules / feature 8)

Revision ID: 022
Revises: 021
Create Date: 2026-07-05 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # rules_doc = {"sections": [{"id": "general", "title": "...", "body_md": "...", "order": 0}, ...]}
    op.add_column("tournaments", sa.Column("rules_doc", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("tournaments", "rules_doc")
