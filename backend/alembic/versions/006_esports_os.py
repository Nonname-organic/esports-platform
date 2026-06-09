"""eSports OS - careers, notifications, discord, riot, recruitment

Revision ID: 006
Revises: 005
Create Date: 2026-06-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── player_careers (選手横断集計) ─────────────────────────────────────────
    op.create_table(
        "player_careers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("total_matches", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_wins", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_losses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("championships", sa.Integer, nullable=False, server_default="0"),
        sa.Column("runner_ups", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tournaments_played", sa.Integer, nullable=False, server_default="0"),
        sa.Column("mvp_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("peak_rating", sa.Float, nullable=True),
        sa.Column("avg_kda", sa.Float, nullable=True),
        sa.Column("avg_acs", sa.Float, nullable=True),
        sa.Column("team_history", postgresql.JSONB, nullable=True),  # [{team_id,name,from,to}]
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── team_careers (チーム横断集計) ─────────────────────────────────────────
    op.create_table(
        "team_careers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("total_matches", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_wins", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_losses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("championships", sa.Integer, nullable=False, server_default="0"),
        sa.Column("runner_ups", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tournaments_played", sa.Integer, nullable=False, server_default="0"),
        sa.Column("peak_rating", sa.Float, nullable=True),
        sa.Column("roster_history", postgresql.JSONB, nullable=True),
        sa.Column("rivals", postgresql.JSONB, nullable=True),  # [{team_id,name,matches,wins}]
        sa.Column("map_performance", postgresql.JSONB, nullable=True),
        sa.Column("agent_trends", postgresql.JSONB, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── notifications は既存テーブル(migration 001)を再利用 ──────────────────
    # action_url カラムのみ追加。既存: user_id/tournament_id/type/title/body/is_read/channel/metadata/created_at
    op.add_column("notifications", sa.Column("action_url", sa.Text, nullable=True))
    op.create_index("idx_notifications_user_read", "notifications", ["user_id", "is_read", "created_at"])

    # ── discord_servers ───────────────────────────────────────────────────────
    op.create_table(
        "discord_servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("guild_id", sa.String(50), nullable=True),
        sa.Column("role_ids", postgresql.JSONB, nullable=True),  # {admin,organizer,captain,player,spectator}
        sa.Column("category_ids", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── discord_channels ──────────────────────────────────────────────────────
    op.create_table(
        "discord_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("discord_server_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("discord_servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.String(50), nullable=False),
        sa.Column("channel_type", sa.String(30), nullable=False),  # announcements/match/etc
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("archived", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_discord_channels_server", "discord_channels", ["discord_server_id"])

    # ── discord_links (ユーザー↔Discord OAuth) ───────────────────────────────
    op.create_table(
        "discord_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("discord_user_id", sa.String(50), nullable=False),
        sa.Column("discord_username", sa.String(100), nullable=True),
        sa.Column("access_token", sa.Text, nullable=True),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_discord_links_discord_user", "discord_links", ["discord_user_id"])

    # ── recruitment_posts ─────────────────────────────────────────────────────
    op.create_table(
        "recruitment_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_type", sa.String(10), nullable=False),  # team_seeks / player_seeks
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("game", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("required_roles", postgresql.JSONB, nullable=True),
        sa.Column("min_rank", sa.String(50), nullable=True),
        sa.Column("regions", postgresql.JSONB, nullable=True),
        sa.Column("is_open", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_recruitment_game_open", "recruitment_posts", ["game", "is_open"])

    # ── riot_profiles ─────────────────────────────────────────────────────────
    op.create_table(
        "riot_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("puuid", sa.String(78), nullable=True, unique=True),
        sa.Column("game_name", sa.String(50), nullable=False),
        sa.Column("tag_line", sa.String(10), nullable=False),
        sa.Column("region", sa.String(10), nullable=True),
        sa.Column("current_rank", sa.String(50), nullable=True),
        sa.Column("peak_rank", sa.String(50), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── riot_matches ──────────────────────────────────────────────────────────
    op.create_table(
        "riot_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("riot_match_id", sa.String(100), nullable=False),
        sa.Column("agent", sa.String(50), nullable=True),
        sa.Column("map_name", sa.String(50), nullable=True),
        sa.Column("kills", sa.Integer, nullable=False, server_default="0"),
        sa.Column("deaths", sa.Integer, nullable=False, server_default="0"),
        sa.Column("assists", sa.Integer, nullable=False, server_default="0"),
        sa.Column("acs", sa.Float, nullable=True),
        sa.Column("hs_rate", sa.Float, nullable=True),
        sa.Column("won", sa.Boolean, nullable=True),
        sa.Column("rounds", sa.Integer, nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("player_id", "riot_match_id", name="uq_riot_match_player"),
    )
    op.create_index("idx_riot_matches_player", "riot_matches", ["player_id", "played_at"])


def downgrade() -> None:
    op.drop_index("idx_notifications_user_read", "notifications")
    op.drop_column("notifications", "action_url")
    for tbl in ["riot_matches", "riot_profiles", "recruitment_posts", "discord_links",
                "discord_channels", "discord_servers",
                "team_careers", "player_careers"]:
        op.drop_table(tbl)
