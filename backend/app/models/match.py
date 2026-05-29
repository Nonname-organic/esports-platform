import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import BOFormat, BanPickAction, GameType, MatchStatus, SideType

if TYPE_CHECKING:
    from app.models.tournament import Tournament, Bracket
    from app.models.team import Team
    from app.models.player import Player
    from app.models.user import User


class Map(UUIDMixin, Base):
    __tablename__ = "maps"

    game: Mapped[GameType] = mapped_column(
        Enum(GameType, name="game_type"), nullable=False
    )
    internal_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("game", "internal_name", name="uq_map_game_name"),
    )

    # Relationships
    match_games: Mapped[list["MatchGame"]] = relationship(
        "MatchGame", back_populates="map"
    )
    ban_picks: Mapped[list["BanPick"]] = relationship(
        "BanPick", back_populates="map"
    )

    def __repr__(self) -> str:
        return f"<Map game={self.game} name={self.display_name}>"


class Match(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "matches"

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bracket_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brackets.id", ondelete="SET NULL"),
        nullable=True,
    )
    team1_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    team2_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    winner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    format: Mapped[BOFormat] = mapped_column(
        Enum(BOFormat, name="bo_format"),
        nullable=False,
        default=BOFormat.BO3,
    )
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status"),
        nullable=False,
        default=MatchStatus.SCHEDULED,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    match_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 次のブラケットへの自己参照（シングルエリミネーション進行）
    next_match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
    )
    # loser_bracket_match_id: double elimination用
    loser_next_match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stream_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    vod_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="matches")
    bracket: Mapped[Optional["Bracket"]] = relationship(
        "Bracket", back_populates="matches"
    )
    team1: Mapped[Optional["Team"]] = relationship(
        "Team", foreign_keys=[team1_id]
    )
    team2: Mapped[Optional["Team"]] = relationship(
        "Team", foreign_keys=[team2_id]
    )
    winner: Mapped[Optional["Team"]] = relationship(
        "Team", foreign_keys=[winner_id]
    )
    games: Mapped[list["MatchGame"]] = relationship(
        "MatchGame",
        back_populates="match",
        order_by="MatchGame.game_number",
    )
    ban_picks: Mapped[list["BanPick"]] = relationship(
        "BanPick", back_populates="match", order_by="BanPick.order"
    )
    result: Mapped[Optional["MatchResult"]] = relationship(
        "MatchResult", back_populates="match", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Match id={self.id} status={self.status} round={self.round_number}>"


class MatchGame(UUIDMixin, Base):
    __tablename__ = "match_games"
    __table_args__ = (
        UniqueConstraint("match_id", "game_number", name="uq_match_game_number"),
    )

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_number: Mapped[int] = mapped_column(Integer, nullable=False)
    map_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maps.id", ondelete="SET NULL"),
        nullable=True,
    )
    team1_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    team2_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    # team1のファーストサイド
    side_first_team1: Mapped[Optional[SideType]] = mapped_column(
        Enum(SideType, name="side_type"), nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="games")
    map: Mapped[Optional["Map"]] = relationship("Map", back_populates="match_games")
    winner: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[winner_id])
    player_stats: Mapped[list["PlayerMatchStats"]] = relationship(
        "PlayerMatchStats", back_populates="match_game"
    )


class BanPick(UUIDMixin, Base):
    __tablename__ = "ban_picks"

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[BanPickAction] = mapped_column(
        Enum(BanPickAction, name="ban_pick_action"), nullable=False
    )
    map_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maps.id", ondelete="CASCADE"),
        nullable=False,
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="ban_picks")
    team: Mapped["Team"] = relationship("Team")
    map: Mapped["Map"] = relationship("Map", back_populates="ban_picks")


class MatchResult(UUIDMixin, Base):
    __tablename__ = "match_results"

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    winner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        nullable=False,
    )
    loser_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        nullable=False,
    )
    winner_score: Mapped[int] = mapped_column(Integer, nullable=False)
    loser_score: Mapped[int] = mapped_column(Integer, nullable=False)
    was_forfeit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="result")
    winner: Mapped["Team"] = relationship("Team", foreign_keys=[winner_id])
    loser: Mapped["Team"] = relationship("Team", foreign_keys=[loser_id])
    confirmed_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[confirmed_by]
    )


class PlayerMatchStats(UUIDMixin, Base):
    __tablename__ = "player_match_stats"

    match_game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("match_games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    kills: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deaths: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_bloods: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # ゲーム固有データ: {"headshot_pct": 0.35, "damage_per_round": 156, ...}
    custom_stats: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    match_game: Mapped["MatchGame"] = relationship(
        "MatchGame", back_populates="player_stats"
    )
    player: Mapped["Player"] = relationship("Player", back_populates="match_stats")
    team: Mapped["Team"] = relationship("Team")

    def kda(self) -> float:
        return (self.kills + self.assists) / max(self.deaths, 1)
