import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, pg_enum
from app.models.enums import GameType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.team import TeamMember
    from app.models.match import PlayerMatchStats
    from app.models.tournament import CheckIn


class Player(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "players"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    in_game_name: Mapped[str] = mapped_column(String(100), nullable=False)
    real_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    game: Mapped[GameType] = mapped_column(pg_enum(GameType, name="game_type"), nullable=False)
    rank: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # ["Jett", "Reyna", "Sage"] など
    agent_pool: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    region: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    twitter_handle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    twitch_handle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="player")
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        "TeamMember", back_populates="player"
    )
    match_stats: Mapped[list["PlayerMatchStats"]] = relationship(
        "PlayerMatchStats", back_populates="player"
    )
    checkins: Mapped[list["CheckIn"]] = relationship(
        "CheckIn", back_populates="player"
    )

    def __repr__(self) -> str:
        return f"<Player id={self.id} ign={self.in_game_name} game={self.game}>"
