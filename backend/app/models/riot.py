import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class RiotProfile(UUIDMixin, Base):
    """Riot ID 紐付け + ランク情報"""
    __tablename__ = "riot_profiles"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, unique=True,
    )
    puuid: Mapped[Optional[str]] = mapped_column(String(78), nullable=True, unique=True)
    game_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_line: Mapped[str] = mapped_column(String(10), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    current_rank: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    peak_rank: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.tag_line}"


class RiotMatch(UUIDMixin, Base):
    """Riot APIから取得した試合データ"""
    __tablename__ = "riot_matches"
    __table_args__ = (
        UniqueConstraint("player_id", "riot_match_id", name="uq_riot_match_player"),
    )

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False,
    )
    riot_match_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    map_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    kills: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deaths: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acs: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hs_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    won: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    rounds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    played_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
