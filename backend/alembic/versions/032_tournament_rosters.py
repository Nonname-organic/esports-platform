"""RC4 第 2 段: 大会の名簿・試合の出場登録・交代・出場の異議・管理者の訂正

- tournaments.roster_mode: 既存の大会は legacy。この版の後に作る大会の既定は roster
- 判定 3（D23）: 表のロックを取った後に、開催中の大会・進行中の試合が 1 件でもあれば例外で止める
  （031・032 がまとめて戻り、版は 030 のまま。旧コードのまま動き続ける）
- トリガー（Q02）: legacy の行の作成と、roster → legacy の変更だけを断る。既存の legacy の行の
  ほかの列の更新は通す。開催中への変更を断るトリガーは作らない

Revision ID: 032
Revises: 031
"""
import logging

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")
UUID = postgresql.UUID(as_uuid=True)
NOW = sa.func.now()


def _count(sql: str) -> int:
    return int(op.get_bind().execute(sa.text(sql)).scalar() or 0)


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '10s'")

    # 先に 2 つの表を変更してロックを取る（ここから commit まで、大会・試合は始まらない）
    op.add_column("tournaments", sa.Column("roster_mode", sa.String(8), nullable=False, server_default="legacy"))
    op.add_column("matches", sa.Column("lineup_locked_at", sa.DateTime(timezone=True), nullable=True))

    ongoing_tournaments = _count("SELECT count(*) FROM tournaments WHERE status = 'ongoing'")
    ongoing_matches = _count("SELECT count(*) FROM matches WHERE status = 'ongoing'")
    log.info("rc4 032 gate: ongoing tournaments=%d ongoing matches=%d", ongoing_tournaments, ongoing_matches)
    if ongoing_tournaments or ongoing_matches:
        raise RuntimeError(
            "RC4 032: 開催中の大会か進行中の試合があるため、公開を延期する（D23）。"
            f" ongoing tournaments={ongoing_tournaments}, ongoing matches={ongoing_matches}")

    op.alter_column("tournaments", "roster_mode", server_default="roster")
    op.create_check_constraint("ck_tournaments_roster_mode", "tournaments", "roster_mode IN ('legacy','roster')")
    op.add_column("tournaments", sa.Column("roster_locked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tournaments", sa.Column("lineup_size", sa.SmallInteger, nullable=True))
    op.add_column("tournaments", sa.Column("roster_max", sa.SmallInteger, nullable=True))
    op.create_check_constraint("ck_tournaments_lineup_size", "tournaments",
                               "lineup_size IS NULL OR lineup_size BETWEEN 1 AND 20")
    op.create_check_constraint("ck_tournaments_roster_max", "tournaments",
                               "roster_max IS NULL OR (roster_max BETWEEN 1 AND 40 AND (lineup_size IS NULL OR roster_max >= lineup_size))")
    log.info("rc4 032: tournaments legacy=%d (by status: %s)",
             _count("SELECT count(*) FROM tournaments"),
             ", ".join(f"{s}={n}" for s, n in op.get_bind().execute(
                 sa.text("SELECT status::text, count(*) FROM tournaments GROUP BY 1 ORDER BY 1")).all()))

    op.create_unique_constraint("uq_tournament_registrations_id_tournament_team", "tournament_registrations",
                                ["id", "tournament_id", "team_id"])
    op.create_unique_constraint("uq_matches_id_tournament", "matches", ["id", "tournament_id"])

    op.create_table(
        "tournament_roster_entries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tournament_id", UUID, nullable=False),
        sa.Column("registration_id", UUID, nullable=False),
        sa.Column("team_id", UUID, nullable=False),
        sa.Column("player_id", UUID, nullable=False),
        sa.Column("membership_id", UUID, nullable=False),
        sa.Column("default_slot", sa.String(8), nullable=False, server_default="starter"),
        sa.Column("status", sa.String(10), nullable=False, server_default="invited"),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("invited_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["registration_id", "tournament_id", "team_id"],
                                ["tournament_registrations.id", "tournament_registrations.tournament_id",
                                 "tournament_registrations.team_id"], ondelete="CASCADE",
                                name="fk_roster_entries_registration"),
        sa.ForeignKeyConstraint(["membership_id", "team_id", "player_id"],
                                ["team_members.id", "team_members.team_id", "team_members.player_id"],
                                name="fk_roster_entries_membership"),
        sa.CheckConstraint("default_slot IN ('starter','bench')", name="ck_roster_entries_slot"),
        sa.CheckConstraint("status IN ('invited','accepted','declined','expired','withdrawn','removed')",
                           name="ck_roster_entries_status"),
        sa.UniqueConstraint("id", "tournament_id", "team_id", "player_id", name="uq_roster_entries_id_scope"),
    )
    op.create_index("ix_roster_entries_registration", "tournament_roster_entries", ["registration_id"])
    op.create_index("ix_roster_entries_player", "tournament_roster_entries", ["player_id"])
    # D10: 同じ大会で 2 チームの名簿に載らない（有効な行だけ）
    op.create_index("uq_roster_entries_tournament_player", "tournament_roster_entries",
                    ["tournament_id", "player_id"], unique=True,
                    postgresql_where=sa.text("status IN ('invited','accepted')"))

    op.create_table(
        "match_lineup_entries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("match_id", UUID, nullable=False),
        sa.Column("tournament_id", UUID, nullable=False),
        sa.Column("team_id", UUID, nullable=False),
        sa.Column("player_id", UUID, nullable=False),
        sa.Column("roster_entry_id", UUID, nullable=False),
        sa.Column("slot", sa.String(8), nullable=False),
        sa.Column("source", sa.String(10), nullable=False, server_default="default"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("added_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["match_id", "tournament_id"], ["matches.id", "matches.tournament_id"],
                                ondelete="CASCADE", name="fk_lineup_entries_match"),
        sa.ForeignKeyConstraint(["roster_entry_id", "tournament_id", "team_id", "player_id"],
                                ["tournament_roster_entries.id", "tournament_roster_entries.tournament_id",
                                 "tournament_roster_entries.team_id", "tournament_roster_entries.player_id"],
                                name="fk_lineup_entries_roster"),
        sa.CheckConstraint("slot IN ('starter','bench')", name="ck_lineup_entries_slot"),
        sa.CheckConstraint("source IN ('default','team','organizer','admin')", name="ck_lineup_entries_source"),
        sa.CheckConstraint("removed_at IS NULL OR removed_at >= added_at", name="ck_lineup_entries_period"),
    )
    op.create_index("ix_lineup_entries_match", "match_lineup_entries", ["match_id"])
    # D8: 同じ試合で 2 チームの出場登録にならない
    op.create_index("uq_lineup_entries_match_player", "match_lineup_entries", ["match_id", "player_id"],
                    unique=True, postgresql_where=sa.text("removed_at IS NULL"))

    op.create_table(
        "match_substitutions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("match_id", UUID, sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_number", sa.SmallInteger, nullable=False),
        sa.Column("team_id", UUID, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("out_lineup_entry_id", UUID, sa.ForeignKey("match_lineup_entries.id", ondelete="CASCADE"), nullable=True),
        sa.Column("in_lineup_entry_id", UUID, sa.ForeignKey("match_lineup_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("at_round", sa.SmallInteger, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="requested"),
        sa.Column("requested_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("approved_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("game_number >= 1", name="ck_substitutions_game"),
        sa.CheckConstraint("kind IN ('between_maps','mid_map','fill')", name="ck_substitutions_kind"),
        sa.CheckConstraint("status IN ('requested','approved','rejected')", name="ck_substitutions_status"),
        sa.CheckConstraint("kind <> 'mid_map' OR reason IS NOT NULL", name="ck_substitutions_midmap_reason"),
        sa.CheckConstraint("(kind = 'fill') = (out_lineup_entry_id IS NULL)", name="ck_substitutions_fill"),
        sa.CheckConstraint("out_lineup_entry_id IS NULL OR out_lineup_entry_id <> in_lineup_entry_id",
                           name="ck_substitutions_distinct"),
    )
    op.create_index("ix_substitutions_match", "match_substitutions", ["match_id"])

    op.add_column("player_match_stats", sa.Column(
        "lineup_entry_id", UUID, sa.ForeignKey("match_lineup_entries.id", ondelete="CASCADE"), nullable=True))

    op.create_table(
        "participation_disputes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("match_id", UUID, sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", UUID, sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.CheckConstraint("status IN ('open','upheld','dismissed')", name="ck_disputes_status"),
    )
    op.create_index("uq_disputes_open", "participation_disputes", ["match_id", "player_id"], unique=True,
                    postgresql_where=sa.text("status = 'open'"))
    op.create_index("ix_disputes_player", "participation_disputes", ["player_id"])

    op.create_table(
        "admin_corrections",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("tournament_id", UUID, sa.ForeignKey("tournaments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("match_id", UUID, sa.ForeignKey("matches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("membership_id", UUID, sa.ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("actor_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("before", postgresql.JSONB, nullable=False),
        sa.Column("after", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "kind IN ('lineup_change','substitution_change','stats_change','match_reopen',"
            "'roster_change','membership_unreject','registration_change',"
            # 切り戻しの手順書（Q30）の 1 回だけの作業で、完了した roster の大会を legacy に戻すときの記録
            "'roster_mode_change')", name="ck_admin_corrections_kind"),
    )
    op.create_index("ix_admin_corrections_tournament", "admin_corrections", ["tournament_id"])

    # Q02: 新しく legacy になる行だけを断る
    op.execute("""
        CREATE OR REPLACE FUNCTION rc4_guard_roster_mode() RETURNS trigger AS $$
        BEGIN
          IF NEW.roster_mode = 'legacy' AND (TG_OP = 'INSERT' OR OLD.roster_mode IS DISTINCT FROM 'legacy') THEN
            RAISE EXCEPTION 'tournaments.roster_mode: new legacy tournaments are not allowed (RC4)'
              USING ERRCODE = 'check_violation';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_tournaments_roster_mode_guard
        BEFORE INSERT OR UPDATE OF roster_mode ON tournaments
        FOR EACH ROW EXECUTE FUNCTION rc4_guard_roster_mode()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_tournaments_roster_mode_guard ON tournaments")
    op.execute("DROP FUNCTION IF EXISTS rc4_guard_roster_mode()")
    op.drop_table("admin_corrections")
    op.drop_table("participation_disputes")
    op.drop_column("player_match_stats", "lineup_entry_id")
    op.drop_table("match_substitutions")
    op.drop_table("match_lineup_entries")
    op.drop_table("tournament_roster_entries")
    op.drop_constraint("uq_matches_id_tournament", "matches", type_="unique")
    op.drop_constraint("uq_tournament_registrations_id_tournament_team", "tournament_registrations", type_="unique")
    op.drop_constraint("ck_tournaments_roster_max", "tournaments", type_="check")
    op.drop_constraint("ck_tournaments_lineup_size", "tournaments", type_="check")
    op.drop_constraint("ck_tournaments_roster_mode", "tournaments", type_="check")
    op.drop_column("tournaments", "roster_max")
    op.drop_column("tournaments", "lineup_size")
    op.drop_column("tournaments", "roster_locked_at")
    op.drop_column("matches", "lineup_locked_at")
    op.drop_column("tournaments", "roster_mode")
