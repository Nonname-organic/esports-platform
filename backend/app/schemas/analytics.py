from datetime import date

from pydantic import BaseModel

from app.models.enums import GameType, PeriodType


class PlayerStatsQuery(BaseModel):
    game: GameType
    period_type: PeriodType = PeriodType.ALL_TIME
    tournament_id: str | None = None


class PlayerStatsResponse(BaseModel):
    player_id: str
    in_game_name: str
    game: GameType
    period_type: PeriodType
    period_date: date
    matches_played: int
    matches_won: int
    games_played: int
    games_won: int
    total_kills: int
    total_deaths: int
    total_assists: int
    avg_kda: float
    win_rate: float
    most_played_agent: str | None
    agent_breakdown: dict | None

    model_config = {"from_attributes": True}


class TeamStatsResponse(BaseModel):
    team_id: str
    team_name: str
    game: GameType
    matches_played: int
    wins: int
    losses: int
    win_rate: float
    current_streak: int
    best_win_streak: int
    map_win_rates: dict | None

    model_config = {"from_attributes": True}


class MapStatsResponse(BaseModel):
    map_id: str
    map_name: str
    game: GameType
    total_games: int
    attack_side_wins: int
    defense_side_wins: int
    attack_win_rate: float
    avg_duration_seconds: float | None
    round_distribution: dict | None

    model_config = {"from_attributes": True}


class CompositionStatsResponse(BaseModel):
    composition: list[str]
    games_played: int
    wins: int
    win_rate: float
    avg_kills: float | None
    avg_deaths: float | None

    model_config = {"from_attributes": True}


class TournamentSummaryResponse(BaseModel):
    tournament_id: str
    tournament_name: str
    game: GameType
    total_matches: int
    completed_matches: int
    total_teams: int
    top_teams: list[dict]
    top_players_kda: list[dict]
    most_played_map: str | None
    avg_match_duration_seconds: float | None


class RankingEntry(BaseModel):
    rank_position: int
    team_id: str
    team_name: str
    team_tag: str
    team_logo_url: str | None
    points: int
    wins: int
    losses: int
    game_wins: int
    game_losses: int
    win_rate: float

    model_config = {"from_attributes": True}
