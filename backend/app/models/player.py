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
    agent_pool: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    region: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    twitter_handle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    twitch_handle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Riot API 連携フィールド ────────────────────────────────────────────────
    # PUUID: Riot APIの永続的ユニーク識別子（将来の自動データ取得に使用）
    riot_puuid: Mapped[Optional[str]] = mapped_column(String(78), nullable=True, unique=True)
    # Riot ID = riot_gamename#riot_tagline（例: SEN Tenz#NA1）
    riot_gamename: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    riot_tagline: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # ── ロール設定 ─────────────────────────────────────────────────────────────
    main_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sub_roles: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # ── Discord 連携 ────────────────────────────────────────────────────────────
    discord_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

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

    @property
    def riot_id(self) -> Optional[str]:
        """Riot ID形式（Name#TAG）で返す"""
        if self.riot_gamename and self.riot_tagline:
            return f"{self.riot_gamename}#{self.riot_tagline}"
        return self.in_game_name

    def __repr__(self) -> str:
        return f"<Player id={self.id} ign={self.in_game_name} game={self.game}>"
