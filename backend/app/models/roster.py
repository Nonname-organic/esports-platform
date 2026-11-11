"""RC4: 所属の招待・移行期間、大会の名簿・試合の出場登録・交代・出場の異議・管理者の訂正。

状態は PostgreSQL の enum ではなく文字列と CHECK（migration 031・032）で持つ。
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, pg_enum
from app.models.enums import MemberRole


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fk(target: str, ondelete: str = "CASCADE"):
    return ForeignKey(target, ondelete=ondelete)


class TeamInvitation(UUIDMixin, Base):
    __tablename__ = "team_invitations"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), _fk("teams.id"), nullable=False)
    invitee_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), _fk("users.id"), nullable=False)
    invited_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    role: Mapped[MemberRole] = mapped_column(pg_enum(MemberRole, name="member_role"), nullable=False,
                                             default=MemberRole.PLAYER)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decided_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    membership_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("team_members.id", "SET NULL"))


class MembershipMigrationState(Base):
    __tablename__ = "membership_migration_state"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    grace_days: Mapped[int] = mapped_column(Integer, nullable=False, default=60)


class TournamentRosterEntry(UUIDMixin, Base):
    __tablename__ = "tournament_roster_entries"

    tournament_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    registration_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    membership_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    default_slot: Mapped[str] = mapped_column(String(8), nullable=False, default="starter")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="invited")
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    invited_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    removed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    reason: Mapped[Optional[str]] = mapped_column(Text)


class MatchLineupEntry(UUIDMixin, Base):
    __tablename__ = "match_lineup_entries"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tournament_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    roster_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    slot: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="default")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    added_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    removed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    reason: Mapped[Optional[str]] = mapped_column(Text)


class MatchSubstitution(UUIDMixin, Base):
    __tablename__ = "match_substitutions"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), _fk("matches.id"), nullable=False)
    game_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), _fk("teams.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    out_lineup_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("match_lineup_entries.id"))
    in_lineup_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), _fk("match_lineup_entries.id"),
                                                          nullable=False)
    at_round: Mapped[Optional[int]] = mapped_column(SmallInteger)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="requested")
    requested_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    approved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ParticipationDispute(UUIDMixin, Base):
    __tablename__ = "participation_disputes"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), _fk("matches.id"), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), _fk("players.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    resolution_note: Mapped[Optional[str]] = mapped_column(Text)


class AdminCorrection(UUIDMixin, Base):
    __tablename__ = "admin_corrections"

    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    tournament_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("tournaments.id", "SET NULL"))
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("matches.id", "SET NULL"))
    membership_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("team_members.id", "SET NULL"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), _fk("users.id", "SET NULL"))
    before: Mapped[dict] = mapped_column(JSONB, nullable=False)
    after: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
