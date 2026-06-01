"""tournament extended tables

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tournaments テーブル拡張 ────────────────────────────────────────────────
    op.add_column("tournaments", sa.Column("subtitle", sa.String(200), nullable=True))
    op.add_column("tournaments", sa.Column("thumbnail_url", sa.Text, nullable=True))
    op.add_column("tournaments", sa.Column("season", sa.String(50), nullable=True))
    op.add_column("tournaments", sa.Column("split", sa.String(50), nullable=True))
    op.add_column("tournaments", sa.Column("tier", sa.String(20), nullable=True, server_default="community"))
    op.add_column("tournaments", sa.Column("visibility", sa.String(20), nullable=False, server_default="public"))
    op.add_column("tournaments", sa.Column("invite_code", sa.String(50), nullable=True))
    op.add_column("tournaments", sa.Column("seeding_type", sa.String(20), nullable=False, server_default="auto"))
    op.add_column("tournaments", sa.Column("age_restriction", postgresql.JSONB, nullable=True))
    op.add_column("tournaments", sa.Column("region_restriction", postgresql.JSONB, nullable=True))
    op.add_column("tournaments", sa.Column("rank_restriction", postgresql.JSONB, nullable=True))
    op.add_column("tournaments", sa.Column("require_team_membership", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("tournaments", sa.Column("analytics_enabled", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("tournaments", sa.Column("player_stats_enabled", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("tournaments", sa.Column("ranking_enabled", sa.Boolean, nullable=False, server_default="true"))

    # ── tournament_rules (ゲーム別競技設定) ───────────────────────────────────
    op.create_table(
        "tournament_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("game_settings", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── tournament_prizes (賞金配分) ──────────────────────────────────────────
    op.create_table(
        "tournament_prizes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank_position", sa.Integer, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="JPY"),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_tournament_prizes_tournament", "tournament_prizes", ["tournament_id"])

    # ── tournament_sponsors ───────────────────────────────────────────────────
    op.create_table(
        "tournament_sponsors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("website_url", sa.Text, nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_tournament_sponsors_tournament", "tournament_sponsors", ["tournament_id"])

    # ── tournament_streams (配信情報) ─────────────────────────────────────────
    op.create_table(
        "tournament_streams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("is_streamed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("twitch_url", sa.Text, nullable=True),
        sa.Column("youtube_url", sa.Text, nullable=True),
        sa.Column("commentators", postgresql.JSONB, nullable=True),
        sa.Column("casters", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── tournament_discord ────────────────────────────────────────────────────
    op.create_table(
        "tournament_discord",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("invite_url", sa.Text, nullable=True),
        sa.Column("webhook_url", sa.Text, nullable=True),
        sa.Column("notify_entry", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notify_checkin", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notify_match_start", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notify_match_end", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── tournament_contacts ───────────────────────────────────────────────────
    op.create_table(
        "tournament_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("discord", sa.String(100), nullable=True),
        sa.Column("twitter", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── tournament_settings (分析設定) ────────────────────────────────────────
    op.create_table(
        "tournament_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("season", sa.String(50), nullable=True),
        sa.Column("split", sa.String(50), nullable=True),
        sa.Column("region", sa.String(20), nullable=True),
        sa.Column("tier", sa.String(20), nullable=True),
        sa.Column("ranking_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("player_stats_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tournament_settings")
    op.drop_table("tournament_contacts")
    op.drop_table("tournament_discord")
    op.drop_table("tournament_streams")
    op.drop_index("idx_tournament_sponsors_tournament", "tournament_sponsors")
    op.drop_table("tournament_sponsors")
    op.drop_index("idx_tournament_prizes_tournament", "tournament_prizes")
    op.drop_table("tournament_prizes")
    op.drop_table("tournament_rules")

    for col in ["subtitle", "thumbnail_url", "season", "split", "tier", "visibility",
                "invite_code", "seeding_type", "age_restriction", "region_restriction",
                "rank_restriction", "require_team_membership", "analytics_enabled",
                "player_stats_enabled", "ranking_enabled"]:
        op.drop_column("tournaments", col)
