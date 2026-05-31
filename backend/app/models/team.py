import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum
from app.models.enums import GameType, MemberRole

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.player import Player
    from app.models.tournament import TournamentRegistration
    from app.models.match import Match


class Team(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(10), nullable=False)
    game: Mapped[GameType] = mapped_column(pg_enum(GameType, name="game_type"), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    twitter_handle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_teams", foreign_keys=[owner_id]
    )
    members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
        primaryjoin="and_(TeamMember.team_id == Team.id, TeamMember.left_at == None)",
    )
    all_members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember", back_populates="team"
    )
    tournament_registrations: Mapped[list["TournamentRegistration"]] = relationship(
        "TournamentRegistration", back_populates="team"
    )

    def __repr__(self) -> str:
        return f"<Team id={self.id} name={self.name} tag={self.tag}>"


class TeamMember(UUIDMixin, Base):
    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MemberRole] = mapped_column(
        pg_enum(MemberRole, name="member_role"),
        nullable=False,
        default=MemberRole.PLAYER,
    )
    jersey_number: Mapped[Optional[int]] = mapped_column(nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="all_members")
    player: Mapped["Player"] = relationship("Player", back_populates="team_memberships")

    def __repr__(self) -> str:
        return f"<TeamMember team={self.team_id} player={self.player_id} role={self.role}>"
