import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── 共通サブスキーマ ───────────────────────────────────────────────────────────
class AgentUsageItem(BaseModel):
    agent: str
    games: int
    wins: int
    win_rate: float
    avg_kda: float


class MapPerformanceItem(BaseModel):
    map_name: str
    games: int
    wins: int
    win_rate: float


class RatingPoint(BaseModel):
    date: str
    rating: float
    delta: float


class TournamentHistoryItem(BaseModel):
    tournament_id: str
    tournament_name: str
    game: str
    placement: Optional[int]
    matches_played: int
    wins: int
    date: Optional[str]


class TeamHistoryItem(BaseModel):
    team_id: str
    team_name: str
    team_tag: str
    role: Optional[str]
    joined_at: Optional[str]
    left_at: Optional[str]
    is_active: bool


class AchievementItem(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str]
    icon_url: Optional[str]
    tournament_id: Optional[str]
    earned_at: str


# ── Player Career ─────────────────────────────────────────────────────────────
class PlayerCareerSchema(BaseModel):
    player_id: str
    in_game_name: str
    game: str

    total_matches: int
    total_wins: int
    total_losses: int
    win_rate: float
    championships: int
    mvp_count: int
    tournaments_played: int

    current_rating: Optional[float]
    peak_rating: Optional[float]
    avg_acs: float
    avg_kda: float
    avg_kills: float
    avg_deaths: float
    avg_assists: float

    agent_usage: list[AgentUsageItem]
    map_performance: list[MapPerformanceItem]


# ── Team Career ───────────────────────────────────────────────────────────────
class RivalItem(BaseModel):
    team_id: str
    team_name: str
    team_tag: str
    matches: int
    wins: int
    losses: int
    win_rate: float


class TeamCareerSchema(BaseModel):
    team_id: str
    team_name: str
    team_tag: str
    game: str

    total_matches: int
    total_wins: int
    total_losses: int
    win_rate: float
    championships: int
    tournaments_played: int

    current_rating: Optional[float]
    peak_rating: Optional[float]

    map_performance: list[MapPerformanceItem]
    agent_trends: list[AgentUsageItem]
    rivals: list[RivalItem]
