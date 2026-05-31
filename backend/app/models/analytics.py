import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, pg_enum
from app.models.enums import AnalyticsEventSource, GameType, PeriodType


class AnalyticsEvent(UUIDMixin, Base):
    """生イベントテーブル。S3にエクスポート後、分析基盤で処理される。"""

    __tablename__ = "analytics_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source: Mapped[AnalyticsEventSource] = mapped_column(
        pg_enum(AnalyticsEventSource, name="analytics_event_source"),
        nullable=False,
        default=AnalyticsEventSource.APPLICATION,
    )
    tournament_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    player_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AggPlayerStats(UUIDMixin, Base):
    """選手統計集計テーブル（日次/週次/月次/大会別）。"""

    __tablename__ = "agg_player_stats"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )
    game: Mapped[GameType] = mapped_column(
        pg_enum(GameType, name="game_type"), nullable=False
    )
    period_type: Mapped[PeriodType] = mapped_column(
        pg_enum(PeriodType, name="period_type"), nullable=False
    )
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    tournament_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matches_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_kills: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_deaths: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_kda: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.0)
    most_played_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # {"Jett": {"games": 10, "wins": 7, "kda": 2.5}, ...}
    agent_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AggTeamStats(UUIDMixin, Base):
    """チーム統計集計テーブル。"""

    __tablename__ = "agg_team_stats"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    game: Mapped[GameType] = mapped_column(
        pg_enum(GameType, name="game_type"), nullable=False
    )
    period_type: Mapped[PeriodType] = mapped_column(
        pg_enum(PeriodType, name="period_type"), nullable=False
    )
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    tournament_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.0)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_win_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_game_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    # {"Ascent": {"games": 5, "wins": 3}, "Bind": {...}}
    map_win_rates: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AggMapStats(UUIDMixin, Base):
    """マップ統計集計テーブル。"""

    __tablename__ = "agg_map_stats"

    map_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maps.id", ondelete="CASCADE"),
        nullable=False,
    )
    game: Mapped[GameType] = mapped_column(
        pg_enum(GameType, name="game_type"), nullable=False
    )
    tournament_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    total_games: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attack_side_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    defense_side_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attack_win_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.0)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    # {round数別の終了分布}
    round_distribution: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    calculated_date: Mapped[date] = mapped_column(Date, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AggCompositionStats(UUIDMixin, Base):
    """エージェント/キャラクター構成統計集計テーブル。"""

    __tablename__ = "agg_composition_stats"

    game: Mapped[GameType] = mapped_column(
        pg_enum(GameType, name="game_type"), nullable=False
    )
    tournament_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    map_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # ["Jett", "Sova", "Sage", "Breach", "Omen"] のようなリスト（ソート済み）
    composition: Mapped[list] = mapped_column(JSONB, nullable=False)
    games_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.0)
    avg_kills: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    avg_deaths: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    calculated_date: Mapped[date] = mapped_column(Date, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
