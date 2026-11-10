"""RC4 第 1 段: チームの所属を本人の承諾制にする（招待・承諾の状態・移行期間）

- team_invitations: 本人が承認したときだけ所属を作る招待
- team_members.consent: self / invitation / confirmed / unconfirmed / rejected
  既存の所属は、証拠のあるもの（チームのオーナー本人、本人が自分を加えたイベント）だけ self。
  それ以外は unconfirmed（証拠の無い所属を承諾済みにしない。D6）
- 現役の所属の重複は、最も古い行を残してほかを脱退にし、rc4_membership_dedup_backup に写す
- 期間の CHECK は NOT VALID で足し、違反が無いときだけ VALIDATE する
- membership_migration_state: 移行期間の開始の時刻と日数（60 日）

ログに出すのは件数だけ（個人を特定する値は出さない）。

Revision ID: 031
Revises: 030
"""
import logging

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

CONSENT_VALUES = "('self','invitation','confirmed','unconfirmed','rejected')"


def _count(sql: str) -> int:
    return int(op.get_bind().execute(sa.text(sql)).scalar() or 0)


def upgrade() -> None:
    # 利用中の書き込みと長く待ち合わない（取れなければ全体が戻り、旧コードのまま動く）
    op.execute("SET LOCAL lock_timeout = '10s'")

    member_role = postgresql.ENUM(name="member_role", create_type=False)
    op.create_table(
        "team_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invitee_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("role", member_role, nullable=False, server_default="player"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("status IN ('pending','accepted','declined','cancelled','expired')", name="ck_team_invitations_status"),
        sa.CheckConstraint("(status = 'pending') = (decided_at IS NULL)", name="ck_team_invitations_decided"),
        sa.CheckConstraint("status <> 'accepted' OR membership_id IS NOT NULL", name="ck_team_invitations_accepted_membership"),
    )
    op.create_index("ix_team_invitations_invitee", "team_invitations", ["invitee_user_id"])
    op.create_index("ix_team_invitations_team", "team_invitations", ["team_id"])
    op.create_index(
        "uq_team_invitations_pending", "team_invitations", ["team_id", "invitee_user_id"],
        unique=True, postgresql_where=sa.text("status = 'pending'"),
    )

    op.add_column("team_members", sa.Column("consent", sa.String(16), nullable=False, server_default="unconfirmed"))
    op.add_column("team_members", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("team_members", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("team_members", sa.Column(
        "invitation_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("team_invitations.id", ondelete="SET NULL"), nullable=True))
    op.create_check_constraint("ck_team_members_consent", "team_members", f"consent IN {CONSENT_VALUES}")
    op.create_check_constraint("ck_team_members_rejected_at", "team_members", "consent <> 'rejected' OR rejected_at IS NOT NULL")

    # 出どころの判定（証拠のあるものだけ self）。比較は文字列で行い、形の違うイベントで止まらない
    op.execute("""
        UPDATE team_members tm SET consent = 'self'
          FROM teams t JOIN players p ON p.user_id = t.owner_id
         WHERE tm.team_id = t.id AND tm.player_id = p.id
    """)
    op.execute("""
        UPDATE team_members tm SET consent = 'self'
          FROM players p, domain_events e
         WHERE p.id = tm.player_id AND tm.consent = 'unconfirmed'
           AND e.type = 'team.member.added'
           AND e.entity_id::text = tm.team_id::text
           AND e.after->>'player_id' = tm.player_id::text
           AND e.actor_id IS NOT NULL AND e.actor_id::text = p.user_id::text
    """)
    log.info("rc4 031: memberships self=%d unconfirmed=%d",
             _count("SELECT count(*) FROM team_members WHERE consent = 'self'"),
             _count("SELECT count(*) FROM team_members WHERE consent = 'unconfirmed'"))

    # 現役の重複: 最も古い行を残し、ほかを退避してから脱退にする（行は消さない）
    op.execute("""
        CREATE TABLE rc4_membership_dedup_backup AS
        SELECT tm.id, tm.team_id, tm.player_id, tm.role, tm.joined_at, tm.left_at, now() AS deduped_at
          FROM team_members tm
         WHERE tm.left_at IS NULL
           AND EXISTS (SELECT 1 FROM team_members o
                        WHERE o.team_id = tm.team_id AND o.player_id = tm.player_id AND o.left_at IS NULL
                          AND (o.joined_at, o.id::text) < (tm.joined_at, tm.id::text))
    """)
    op.execute("""
        UPDATE team_members tm SET left_at = GREATEST(now(), tm.joined_at)
          FROM rc4_membership_dedup_backup b WHERE b.id = tm.id
    """)
    log.info("rc4 031: duplicate active memberships closed=%d",
             _count("SELECT count(*) FROM rc4_membership_dedup_backup"))

    # 期間の CHECK: 新しい行には必ず効く。既存の違反が無ければ VALIDATE する
    op.execute("ALTER TABLE team_members ADD CONSTRAINT ck_team_members_period "
               "CHECK (left_at IS NULL OR left_at >= joined_at) NOT VALID")
    inverted = _count("SELECT count(*) FROM team_members WHERE left_at IS NOT NULL AND left_at < joined_at")
    if inverted == 0:
        op.execute("ALTER TABLE team_members VALIDATE CONSTRAINT ck_team_members_period")
    log.info("rc4 031: inverted membership periods=%d (constraint %s)",
             inverted, "validated" if inverted == 0 else "left NOT VALID")

    op.create_index(
        "uq_team_members_active", "team_members", ["team_id", "player_id"],
        unique=True, postgresql_where=sa.text("left_at IS NULL"),
    )
    op.create_unique_constraint("uq_team_members_id_team_player", "team_members", ["id", "team_id", "player_id"])

    op.create_table(
        "membership_migration_state",
        sa.Column("id", sa.SmallInteger, primary_key=True, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("grace_days", sa.Integer, nullable=False, server_default="60"),
        sa.CheckConstraint("id = 1", name="ck_membership_migration_state_single"),
    )
    op.execute("INSERT INTO membership_migration_state (id) VALUES (1)")


def downgrade() -> None:
    op.drop_table("membership_migration_state")
    op.drop_constraint("uq_team_members_id_team_player", "team_members", type_="unique")
    op.drop_index("uq_team_members_active", table_name="team_members")
    op.drop_constraint("ck_team_members_period", "team_members", type_="check")
    # 退避した重複の行を元の状態（現役）に戻す
    op.execute("""
        UPDATE team_members tm SET left_at = b.left_at
          FROM rc4_membership_dedup_backup b WHERE b.id = tm.id
    """)
    op.execute("DROP TABLE rc4_membership_dedup_backup")
    op.drop_constraint("ck_team_members_rejected_at", "team_members", type_="check")
    op.drop_constraint("ck_team_members_consent", "team_members", type_="check")
    op.drop_column("team_members", "invitation_id")
    op.drop_column("team_members", "rejected_at")
    op.drop_column("team_members", "confirmed_at")
    op.drop_column("team_members", "consent")
    op.drop_index("uq_team_invitations_pending", table_name="team_invitations")
    op.drop_index("ix_team_invitations_team", table_name="team_invitations")
    op.drop_index("ix_team_invitations_invitee", table_name="team_invitations")
    op.drop_table("team_invitations")
