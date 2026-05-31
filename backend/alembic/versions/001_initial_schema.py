"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== ENUM TYPES =====
    # ENUM types are created automatically by sa.Enum in op.create_table below

    # ===== USERS =====
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "organizer", "team_manager", "player", name="user_role"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("discord_id", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("discord_id"),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # ===== PLAYERS =====
    op.create_table(
        "players",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("in_game_name", sa.String(100), nullable=False),
        sa.Column("real_name", sa.String(100), nullable=True),
        sa.Column(
            "game",
            sa.Enum("VALORANT", "LOL", "APEX", "CS2", "OVERWATCH", name="game_type"),
            nullable=False,
        ),
        sa.Column("rank", sa.String(50), nullable=True),
        sa.Column("agent_pool", postgresql.JSONB(), nullable=True),
        sa.Column("region", sa.String(20), nullable=True),
        sa.Column("nationality", sa.String(50), nullable=True),
        sa.Column("twitter_handle", sa.String(100), nullable=True),
        sa.Column("twitch_handle", sa.String(100), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # ===== TEAMS =====
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("tag", sa.String(10), nullable=False),
        sa.Column(
            "game",
            sa.Enum("VALORANT", "LOL", "APEX", "CS2", "OVERWATCH", name="game_type"),
            nullable=False,
        ),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("twitter_handle", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_teams_name", "teams", ["name"])

    # ===== TEAM MEMBERS =====
    op.create_table(
        "team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("captain", "player", "substitute", "coach", "analyst", name="member_role"),
            nullable=False,
        ),
        sa.Column("jersey_number", sa.Integer(), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_team_members_team", "team_members", ["team_id"])
    op.create_index("idx_team_members_player", "team_members", ["player_id"])

    # ===== TOURNAMENTS =====
    op.create_table(
        "tournaments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column(
            "game",
            sa.Enum("VALORANT", "LOL", "APEX", "CS2", "OVERWATCH", name="game_type"),
            nullable=False,
        ),
        sa.Column(
            "format",
            sa.Enum(
                "single_elimination",
                "double_elimination",
                "round_robin",
                "swiss",
                name="tournament_format",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "registration_open",
                "registration_closed",
                "check_in",
                "ongoing",
                "completed",
                "cancelled",
                name="tournament_status",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("organizer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("max_teams", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("min_teams", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("registration_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registration_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_in_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rules", postgresql.JSONB(), nullable=True),
        sa.Column("prize_pool", sa.Numeric(12, 2), nullable=True),
        sa.Column("prize_currency", sa.String(3), nullable=False, server_default="JPY"),
        sa.Column("discord_webhook_url", sa.Text(), nullable=True),
        sa.Column("discord_channel_id", sa.String(100), nullable=True),
        sa.Column("banner_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("require_check_in", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("idx_tournaments_game", "tournaments", ["game"])
    op.create_index("idx_tournaments_status", "tournaments", ["status"])
    op.create_index("idx_tournaments_start_at", "tournaments", ["start_at"])
    op.create_index(
        "idx_tournaments_game_status",
        "tournaments",
        ["game", "status", sa.text("start_at DESC")],
    )

    # ===== TOURNAMENT REGISTRATIONS =====
    op.create_table(
        "tournament_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "approved", "rejected", "withdrawn", "waitlisted",
                name="registration_status",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "team_id", name="uq_tournament_team"),
    )

    # ===== BRACKETS =====
    op.create_table(
        "brackets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("bracket_type", sa.String(20), nullable=False, server_default="winners"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== MAPS =====
    op.create_table(
        "maps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "game",
            sa.Enum("VALORANT", "LOL", "APEX", "CS2", "OVERWATCH", name="game_type"),
            nullable=False,
        ),
        sa.Column("internal_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game", "internal_name", name="uq_map_game_name"),
    )

    # ===== MATCHES =====
    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bracket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team1_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team2_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("winner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "format",
            sa.Enum("BO1", "BO3", "BO5", name="bo_format"),
            nullable=False,
            server_default="BO3",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "scheduled", "ongoing", "completed", "cancelled", "forfeit", "no_show",
                name="match_status",
            ),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("match_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_match_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("loser_next_match_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stream_url", sa.String(500), nullable=True),
        sa.Column("vod_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bracket_id"], ["brackets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team1_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team2_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["next_match_id"], ["matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["loser_next_match_id"], ["matches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_matches_tournament", "matches", ["tournament_id"])
    op.create_index("idx_matches_status", "matches", ["status"])
    op.create_index("idx_matches_scheduled", "matches", ["scheduled_at"])

    # ===== MATCH GAMES =====
    op.create_table(
        "match_games",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_number", sa.Integer(), nullable=False),
        sa.Column("map_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team1_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("team2_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "side_first_team1",
            sa.Enum("attack", "defense", name="side_type"),
            nullable=True,
        ),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["map_id"], ["maps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", "game_number", name="uq_match_game_number"),
    )
    op.create_index("idx_match_games_match", "match_games", ["match_id"])

    # ===== BAN PICKS =====
    op.create_table(
        "ban_picks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "action",
            sa.Enum("ban", "pick", name="ban_pick_action"),
            nullable=False,
        ),
        sa.Column("map_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["map_id"], ["maps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ban_picks_match", "ban_picks", ["match_id"])

    # ===== MATCH RESULTS =====
    op.create_table(
        "match_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("winner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("loser_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("winner_score", sa.Integer(), nullable=False),
        sa.Column("loser_score", sa.Integer(), nullable=False),
        sa.Column("was_forfeit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["loser_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id"),
    )

    # ===== PLAYER MATCH STATS =====
    op.create_table(
        "player_match_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent", sa.String(100), nullable=True),
        sa.Column("kills", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deaths", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assists", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_bloods", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("custom_stats", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_game_id"], ["match_games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pms_player", "player_match_stats", ["player_id"])
    op.create_index("idx_pms_match_game", "player_match_stats", ["match_game_id"])
    op.create_index("idx_pms_agent", "player_match_stats", ["agent"])
    op.create_index("idx_pms_player_agent", "player_match_stats", ["player_id", "agent"])

    # ===== RANKINGS =====
    op.create_table(
        "rankings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("game_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("game_losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_rankings_tournament", "rankings", ["tournament_id", "rank_position"])
    op.create_index("idx_rankings_team", "rankings", ["team_id"])

    # ===== NOTIFICATIONS =====
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "match_start", "match_result", "match_scheduled",
                "registration_approved", "registration_rejected",
                "check_in_reminder", "tournament_start", "tournament_cancelled",
                "bracket_updated", "general",
                name="notification_type",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "channel",
            sa.Enum("in_app", "discord", "email", name="notification_channel"),
            nullable=False,
            server_default="in_app",
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notifications_user", "notifications", ["user_id"])
    op.create_index(
        "idx_notifications_user_unread",
        "notifications",
        ["user_id", "is_read", sa.text("created_at DESC")],
        postgresql_where=sa.text("is_read = false"),
    )

    # ===== CHECKINS =====
    op.create_table(
        "checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("qr_code", sa.String(255), nullable=False, unique=True),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "method",
            sa.Enum("qr", "manual", name="check_in_method"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checked_in_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== AUDIT LOGS (with BRIN index) =====
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE INDEX idx_audit_logs_created_brin ON audit_logs USING BRIN(created_at)"
    )
    op.create_index("idx_audit_logs_user", "audit_logs", ["user_id", sa.text("created_at DESC")])
    op.create_index(
        "idx_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"]
    )

    # ===== ANALYTICS EVENTS =====
    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "application", "riot_api", "manual", "webhook",
                name="analytics_event_source",
            ),
            nullable=False,
        ),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_events_type", "analytics_events", ["event_type", sa.text("created_at DESC")])
    op.create_index("idx_events_tournament", "analytics_events", ["tournament_id", sa.text("created_at DESC")])

    # ===== AGGREGATION TABLES =====
    op.create_table(
        "agg_player_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "game",
            sa.Enum("VALORANT", "LOL", "APEX", "CS2", "OVERWATCH", name="game_type"),
            nullable=False,
        ),
        sa.Column(
            "period_type",
            sa.Enum("daily", "weekly", "monthly", "tournament", "all_time", name="period_type"),
            nullable=False,
        ),
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_kills", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_deaths", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_assists", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_kda", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("most_played_agent", sa.String(100), nullable=True),
        sa.Column("agent_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_agg_player_unique",
        "agg_player_stats",
        ["player_id", "game", "period_type", "period_date"],
        unique=True,
    )

    op.create_table(
        "agg_team_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "game",
            sa.Enum("VALORANT", "LOL", "APEX", "CS2", "OVERWATCH", name="game_type"),
            nullable=False,
        ),
        sa.Column(
            "period_type",
            sa.Enum("daily", "weekly", "monthly", "tournament", "all_time", name="period_type"),
            nullable=False,
        ),
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_win_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_game_duration_seconds", sa.Numeric(8, 2), nullable=True),
        sa.Column("map_win_rates", postgresql.JSONB(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agg_map_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("map_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "game",
            sa.Enum("VALORANT", "LOL", "APEX", "CS2", "OVERWATCH", name="game_type"),
            nullable=False,
        ),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_games", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attack_side_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("defense_side_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attack_win_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("total_rounds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_duration_seconds", sa.Numeric(8, 2), nullable=True),
        sa.Column("round_distribution", postgresql.JSONB(), nullable=True),
        sa.Column("calculated_date", sa.Date(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["map_id"], ["maps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agg_composition_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "game",
            sa.Enum("VALORANT", "LOL", "APEX", "CS2", "OVERWATCH", name="game_type"),
            nullable=False,
        ),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("map_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("composition", postgresql.JSONB(), nullable=False),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("avg_kills", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_deaths", sa.Numeric(5, 2), nullable=True),
        sa.Column("calculated_date", sa.Date(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ===== SEED DATA: Maps =====
    op.execute("""
        INSERT INTO maps (id, game, internal_name, display_name, is_active) VALUES
        (gen_random_uuid(), 'VALORANT', 'ascent', 'Ascent', true),
        (gen_random_uuid(), 'VALORANT', 'bind', 'Bind', true),
        (gen_random_uuid(), 'VALORANT', 'haven', 'Haven', true),
        (gen_random_uuid(), 'VALORANT', 'split', 'Split', true),
        (gen_random_uuid(), 'VALORANT', 'fracture', 'Fracture', true),
        (gen_random_uuid(), 'VALORANT', 'pearl', 'Pearl', true),
        (gen_random_uuid(), 'VALORANT', 'lotus', 'Lotus', true),
        (gen_random_uuid(), 'VALORANT', 'sunset', 'Sunset', true),
        (gen_random_uuid(), 'VALORANT', 'abyss', 'Abyss', true)
    """)


def downgrade() -> None:
    op.drop_table("agg_composition_stats")
    op.drop_table("agg_map_stats")
    op.drop_table("agg_team_stats")
    op.drop_table("agg_player_stats")
    op.drop_table("analytics_events")
    op.drop_table("audit_logs")
    op.drop_table("checkins")
    op.drop_table("notifications")
    op.drop_table("rankings")
    op.drop_table("player_match_stats")
    op.drop_table("match_results")
    op.drop_table("ban_picks")
    op.drop_table("match_games")
    op.drop_table("matches")
    op.drop_table("maps")
    op.drop_table("brackets")
    op.drop_table("tournament_registrations")
    op.drop_table("tournaments")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("players")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS analytics_event_source")
    op.execute("DROP TYPE IF EXISTS period_type")
    op.execute("DROP TYPE IF EXISTS check_in_method")
    op.execute("DROP TYPE IF EXISTS notification_channel")
    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS side_type")
    op.execute("DROP TYPE IF EXISTS ban_pick_action")
    op.execute("DROP TYPE IF EXISTS match_status")
    op.execute("DROP TYPE IF EXISTS bo_format")
    op.execute("DROP TYPE IF EXISTS member_role")
    op.execute("DROP TYPE IF EXISTS registration_status")
    op.execute("DROP TYPE IF EXISTS tournament_status")
    op.execute("DROP TYPE IF EXISTS tournament_format")
    op.execute("DROP TYPE IF EXISTS game_type")
    op.execute("DROP TYPE IF EXISTS user_role")
