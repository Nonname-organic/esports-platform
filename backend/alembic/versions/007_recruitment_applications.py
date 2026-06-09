"""recruitment applications + scout profile activity

Revision ID: 007
Revises: 006
Create Date: 2026-06-02 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── recruitment_applications (応募/招待) ──────────────────────────────────
    op.create_table(
        "recruitment_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("recruitment_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_player_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("applicant_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(10), nullable=False, server_default="apply"),  # apply / invite
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),  # pending/accepted/rejected/withdrawn
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("post_id", "applicant_id", name="uq_application_post_applicant"),
    )
    op.create_index("idx_applications_post", "recruitment_applications", ["post_id", "status"])
    op.create_index("idx_applications_applicant", "recruitment_applications", ["applicant_id"])

    # ── scout_profiles に検索用カラム追加 ─────────────────────────────────────
    op.add_column("scout_profiles", sa.Column("scout_rating", sa.Float, nullable=True))
    op.add_column("scout_profiles", sa.Column("age", sa.Integer, nullable=True))
    op.create_index("idx_scout_profiles_rating", "scout_profiles", ["scout_rating"])


def downgrade() -> None:
    op.drop_index("idx_scout_profiles_rating", "scout_profiles")
    op.drop_column("scout_profiles", "age")
    op.drop_column("scout_profiles", "scout_rating")
    op.drop_index("idx_applications_applicant", "recruitment_applications")
    op.drop_index("idx_applications_post", "recruitment_applications")
    op.drop_table("recruitment_applications")
