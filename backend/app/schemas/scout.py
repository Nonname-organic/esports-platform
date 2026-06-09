import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Player Discovery ──────────────────────────────────────────────────────────
class ScoutPlayerCard(BaseModel):
    player_id: str
    in_game_name: str
    game: str
    main_role: Optional[str]
    rank: Optional[str]
    region: Optional[str]
    current_team_id: Optional[str]
    current_team_name: Optional[str]
    rating: Optional[float]
    scout_rating: Optional[float]
    win_rate: float
    total_matches: int
    championships: int
    mvp_count: int
    tournaments_played: int
    is_looking: bool
    availability: Optional[str]
    languages: Optional[list[str]] = None


class ScoutTeamCard(BaseModel):
    team_id: str
    name: str
    tag: str
    game: str
    logo_url: Optional[str]
    region: Optional[str]
    avg_rating: Optional[float]
    win_rate: float
    total_matches: int
    championships: int
    roster_count: int
    is_recruiting: bool


# ── Recruitment ───────────────────────────────────────────────────────────────
class RecruitmentCreate(BaseModel):
    post_type: str = Field(..., pattern=r"^(team_seeks|player_seeks)$")
    team_id: Optional[str] = None
    player_id: Optional[str] = None
    game: str
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    required_roles: Optional[list[str]] = None
    min_rank: Optional[str] = None
    regions: Optional[list[str]] = None


class RecruitmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    required_roles: Optional[list[str]] = None
    min_rank: Optional[str] = None
    regions: Optional[list[str]] = None
    is_open: Optional[bool] = None


class RecruitmentPostSchema(BaseModel):
    id: str
    author_id: str
    post_type: str
    team_id: Optional[str]
    player_id: Optional[str]
    game: str
    title: str
    description: Optional[str]
    required_roles: Optional[list]
    min_rank: Optional[str]
    regions: Optional[list]
    is_open: bool
    application_count: int = 0
    created_at: datetime


class ApplicationCreate(BaseModel):
    post_id: str
    kind: str = Field(default="apply", pattern=r"^(apply|invite)$")
    message: Optional[str] = Field(None, max_length=1000)
    player_id: Optional[str] = None
    team_id: Optional[str] = None


class ApplicationSchema(BaseModel):
    id: str
    post_id: str
    applicant_id: str
    kind: str
    message: Optional[str]
    status: str
    created_at: datetime


# ── Recommendation ────────────────────────────────────────────────────────────
class RecommendationItem(BaseModel):
    target_id: str
    target_type: str  # player / team
    name: str
    score: float
    breakdown: dict  # {role_match, language_match, region_match, rating, activity, tournament, win_rate}
    summary: str


class RecommendationWeights(BaseModel):
    role_match: float = 0.25
    language_match: float = 0.10
    region_match: float = 0.15
    rating_diff: float = 0.20
    activity: float = 0.10
    tournament_exp: float = 0.10
    win_rate: float = 0.10
