"""add tags + taggables (normalized tagging / ADR-0014)

Revision ID: 020
Revises: 019
Create Date: 2026-07-05 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("category", sa.String(30), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_tags_slug"),
    )
    op.create_table(
        "taggables",
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tag_id", "entity_type", "entity_id"),
    )
    op.create_index("ix_taggables_entity", "taggables", ["entity_type", "entity_id"])
    op.create_index("ix_taggables_tag_type", "taggables", ["tag_id", "entity_type"])


def downgrade() -> None:
    op.drop_index("ix_taggables_tag_type", "taggables")
    op.drop_index("ix_taggables_entity", "taggables")
    op.drop_table("taggables")
    op.drop_table("tags")
