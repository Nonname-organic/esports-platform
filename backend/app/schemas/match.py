from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import BOFormat, BanPickAction, MatchStatus, SideType


class ScoreUpdate(BaseModel):
    team1_score: int = Field(..., ge=0)
    team2_score: int = Field(..., ge=0)
    side_first_team1: SideType | None = None
    duration_seconds: int | None = Field(default=None, ge=0)


class BanPickCreate(BaseModel):
    team_id: str
    action: BanPickAction
    map_id: str
    order: int = Field(..., ge=1)


class MatchResultCreate(BaseModel):
    winner_id: str
    was_forfeit: bool = False
    game_stats: list["GameStatsCreate"] | None = None


class PlayerStatsCreate(BaseModel):
    player_id: str
    team_id: str
    agent: str | None = None
    kills: int = Field(default=0, ge=0)
    deaths: int = Field(default=0, ge=0)
    assists: int = Field(default=0, ge=0)
    score: int = Field(default=0, ge=0)
    first_bloods: int = Field(default=0, ge=0)
    custom_stats: dict | None = None


class GameStatsCreate(BaseModel):
    game_number: int = Field(..., ge=1, le=5)
    map_id: str
    team1_score: int = Field(..., ge=0)
    team2_score: int = Field(..., ge=0)
    winner_id: str
    side_first_team1: SideType | None = None
    duration_seconds: int | None = None
    player_stats: list[PlayerStatsCreate]


class PlayerStatsResponse(BaseModel):
    player_id: str
    player_name: str
    team_id: str
    agent: str | None
    kills: int
    deaths: int
    assists: int
    kda: float
    score: int
    first_bloods: int
    custom_stats: dict | None

    model_config = {"from_attributes": True}


class MatchGameResponse(BaseModel):
    id: str
    game_number: int
    map_id: str | None
    map_name: str | None
    team1_score: int
    team2_score: int
    winner_id: str | None
    duration_seconds: int | None
    player_stats: list[PlayerStatsResponse]

    model_config = {"from_attributes": True}


class BanPickResponse(BaseModel):
    team_id: str
    action: BanPickAction
    map_id: str
    map_name: str
    order: int

    model_config = {"from_attributes": True}


class MatchTeam(BaseModel):
    id: str
    name: str
    tag: str
    logo_url: str | None


class MatchDetail(BaseModel):
    id: str
    tournament_id: str
    format: BOFormat
    status: MatchStatus
    round_number: int
    team1: MatchTeam | None
    team2: MatchTeam | None
    winner_id: str | None
    scheduled_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    games: list[MatchGameResponse]
    ban_picks: list[BanPickResponse]
    stream_url: str | None
    vod_url: str | None

    model_config = {"from_attributes": True}


# WebSocket メッセージ型
class WSScoreUpdateMessage(BaseModel):
    type: str = "score_update"
    match_id: str
    game_number: int
    team1_score: int
    team2_score: int


class WSMatchCompleteMessage(BaseModel):
    type: str = "match_complete"
    match_id: str
    winner_id: str
    winner_score: int
    loser_score: int


class WSBracketUpdateMessage(BaseModel):
    type: str = "bracket_update"
    tournament_id: str
    updated_match_id: str
    next_match_id: str | None
