"""match evidence (screenshots) for Discord match rooms

Revision ID: 009
Revises: 008
Create Date: 2026-06-09 01:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="screenshot"),
        sa.Column("submitted_by_discord", sa.String(50), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_match_evidence_match", "match_evidence", ["match_id"])


def downgrade() -> None:
    op.drop_index("idx_match_evidence_match", "match_evidence")
    op.drop_table("match_evidence")
