"""world class platform - match rounds, ratings, scout, events

Revision ID: 005
Revises: 004
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── match_rounds (ラウンド詳細データ) ─────────────────────────────────────
    op.create_table(
        "match_rounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_number", sa.Integer, nullable=False),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("winner_side", sa.String(10), nullable=True),  # attack/defense
        sa.Column("winner_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("win_condition", sa.String(30), nullable=True),  # elimination/bomb/time
        sa.Column("team1_economy", postgresql.JSONB, nullable=True),
        sa.Column("team2_economy", postgresql.JSONB, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("round_data", postgresql.JSONB, nullable=True),  # kill events etc
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_match_rounds_match", "match_rounds", ["match_id", "game_number", "round_number"])

    # ── match_events (キルフィード・タイムライン) ──────────────────────────────
    op.create_table(
        "match_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("match_rounds.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False),  # kill/ability/plant/defuse/clutch
        sa.Column("timestamp_ms", sa.BigInteger, nullable=True),
        sa.Column("actor_player_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("victim_player_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("weapon", sa.String(50), nullable=True),
        sa.Column("headshot", sa.Boolean, nullable=True),
        sa.Column("event_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_match_events_match", "match_events", ["match_id"])

    # ── player_ratings (ELO/Glicko-2 レーティング) ───────────────────────────
    op.create_table(
        "player_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game", sa.String(20), nullable=False),
        sa.Column("rating", sa.Float, nullable=False, server_default="1500"),
        sa.Column("deviation", sa.Float, nullable=False, server_default="350"),  # Glicko-2 RD
        sa.Column("volatility", sa.Float, nullable=False, server_default="0.06"),
        sa.Column("peak_rating", sa.Float, nullable=True),
        sa.Column("matches_played", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_player_ratings_player_game", "player_ratings", ["player_id", "game"], unique=True)
    op.create_index("idx_player_ratings_game_rating", "player_ratings", ["game", "rating"])

    # ── player_rating_history ─────────────────────────────────────────────────
    op.create_table(
        "player_rating_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game", sa.String(20), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating_before", sa.Float, nullable=False),
        sa.Column("rating_after", sa.Float, nullable=False),
        sa.Column("delta", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_rating_history_player", "player_rating_history", ["player_id", "game"])

    # ── player_achievements (実績・トロフィー) ────────────────────────────────
    op.create_table(
        "player_achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("achievement_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("icon_url", sa.Text, nullable=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_achievements_player", "player_achievements", ["player_id"])

    # ── team_achievements ─────────────────────────────────────────────────────
    op.create_table(
        "team_achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("achievement_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── scout_profiles (スカウト・募集) ───────────────────────────────────────
    op.create_table(
        "scout_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=True, unique=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, unique=True),
        sa.Column("type", sa.String(10), nullable=False),  # player/team
        sa.Column("is_looking", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("availability", sa.String(20), nullable=True),  # full_time/part_time/casual
        sa.Column("preferred_roles", postgresql.JSONB, nullable=True),
        sa.Column("languages", postgresql.JSONB, nullable=True),
        sa.Column("regions", postgresql.JSONB, nullable=True),
        sa.Column("min_tournament_tier", sa.String(20), nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("contact_discord", sa.String(100), nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_scout_profiles_type", "scout_profiles", ["type", "is_looking"])

    # ── platform_events (ドメインイベントログ) ────────────────────────────────
    op.create_table(
        "platform_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("aggregate_type", sa.String(30), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_platform_events_type", "platform_events", ["event_type", "created_at"])
    op.create_index("idx_platform_events_aggregate", "platform_events", ["aggregate_id"])

    # ── match_mvp (MVP自動算出キャッシュ) ────────────────────────────────────
    op.create_table(
        "match_mvps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_name", sa.String(100), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acs", sa.Float, nullable=True),
        sa.Column("kda", sa.Float, nullable=True),
        sa.Column("mvp_score", sa.Float, nullable=False),
        sa.Column("stats_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── match_summaries (AI生成サマリー) ─────────────────────────────────────
    op.create_table(
        "match_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("summary_text", sa.Text, nullable=True),
        sa.Column("key_moments", postgresql.JSONB, nullable=True),
        sa.Column("generated_by", sa.String(30), nullable=True, server_default="ai"),
        sa.Column("language", sa.String(5), nullable=False, server_default="ja"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for tbl in ["match_summaries", "match_mvps", "platform_events", "scout_profiles",
                "team_achievements", "player_achievements", "player_rating_history",
                "player_ratings", "match_events", "match_rounds"]:
        op.drop_table(tbl)
