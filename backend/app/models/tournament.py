import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    CheckInMethod,
    GameType,
    NotificationChannel,
    NotificationType,
    RegistrationStatus,
    TournamentFormat,
    TournamentStatus,
)

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.team import Team
    from app.models.player import Player
    from app.models.match import Match


class Tournament(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tournaments"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    game: Mapped[GameType] = mapped_column(
        Enum(GameType, name="game_type"),
        nullable=False,
        index=True,
    )
    format: Mapped[TournamentFormat] = mapped_column(
        Enum(TournamentFormat, name="tournament_format"),
        nullable=False,
    )
    status: Mapped[TournamentStatus] = mapped_column(
        Enum(TournamentStatus, name="tournament_status"),
        nullable=False,
        default=TournamentStatus.DRAFT,
        index=True,
    )
    organizer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    max_teams: Mapped[int] = mapped_column(Integer, nullable=False, default=16)
    min_teams: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    registration_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registration_end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_in_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # {"rules": "...", "bo_format": "BO3", "map_pool": [...]}
    rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    prize_pool: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    prize_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="JPY")
    discord_webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discord_channel_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_check_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    organizer: Mapped["User"] = relationship("User", back_populates="organized_tournaments")
    registrations: Mapped[list["TournamentRegistration"]] = relationship(
        "TournamentRegistration", back_populates="tournament"
    )
    brackets: Mapped[list["Bracket"]] = relationship(
        "Bracket", back_populates="tournament", order_by="Bracket.round_number"
    )
    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="tournament"
    )
    rankings: Mapped[list["Ranking"]] = relationship(
        "Ranking", back_populates="tournament"
    )
    checkins: Mapped[list["CheckIn"]] = relationship(
        "CheckIn", back_populates="tournament"
    )

    def __repr__(self) -> str:
        return f"<Tournament id={self.id} name={self.name} game={self.game}>"


class TournamentRegistration(UUIDMixin, Base):
    __tablename__ = "tournament_registrations"
    __table_args__ = (
        UniqueConstraint("tournament_id", "team_id", name="uq_tournament_team"),
    )

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, name="registration_status"),
        nullable=False,
        default=RegistrationStatus.PENDING,
    )
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    tournament: Mapped["Tournament"] = relationship(
        "Tournament", back_populates="registrations"
    )
    team: Mapped["Team"] = relationship("Team", back_populates="tournament_registrations")


class Bracket(UUIDMixin, Base):
    __tablename__ = "brackets"

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # "winners", "losers", "grand_final" for double elimination
    bracket_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="winners"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="brackets")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="bracket")


class Ranking(UUIDMixin, Base):
    __tablename__ = "rankings"

    tournament_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
    )
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    game_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    game_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    tournament: Mapped[Optional["Tournament"]] = relationship(
        "Tournament", back_populates="rankings"
    )
    team: Mapped[Optional["Team"]] = relationship("Team")


class CheckIn(UUIDMixin, Base):
    __tablename__ = "checkins"

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True,
    )
    qr_code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checked_in_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    method: Mapped[Optional[CheckInMethod]] = mapped_column(
        Enum(CheckInMethod, name="check_in_method"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="checkins")
    team: Mapped["Team"] = relationship("Team")
    player: Mapped[Optional["Player"]] = relationship(
        "Player", back_populates="checkins"
    )


class Notification(UUIDMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tournament_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"),
        nullable=False,
        default=NotificationChannel.IN_APP,
    )
    # {"match_id": "...", "team_id": "..."} など追加情報
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="notifications")
