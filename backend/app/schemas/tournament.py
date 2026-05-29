from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import GameType, TournamentFormat, TournamentStatus


class TournamentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    game: GameType
    format: TournamentFormat
    max_teams: int = Field(default=16, ge=2, le=256)
    min_teams: int = Field(default=2, ge=2)
    registration_start_at: datetime | None = None
    registration_end_at: datetime | None = None
    check_in_start_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    rules: dict | None = None
    prize_pool: Decimal | None = Field(default=None, ge=0)
    prize_currency: str = Field(default="JPY", max_length=3)
    discord_webhook_url: str | None = None
    description: str | None = None
    is_public: bool = True
    require_check_in: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "TournamentCreate":
        if self.registration_end_at and self.registration_start_at:
            if self.registration_end_at <= self.registration_start_at:
                raise ValueError("参加受付終了日は開始日より後である必要があります")
        if self.start_at and self.registration_end_at:
            if self.start_at <= self.registration_end_at:
                raise ValueError("大会開始日は参加受付終了日より後である必要があります")
        if self.end_at and self.start_at:
            if self.end_at <= self.start_at:
                raise ValueError("大会終了日は開始日より後である必要があります")
        return self

    @field_validator("max_teams")
    @classmethod
    def max_must_be_power_of_two_for_elimination(cls, v: int) -> int:
        return v


class TournamentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    status: TournamentStatus | None = None
    max_teams: int | None = Field(default=None, ge=2, le=256)
    registration_start_at: datetime | None = None
    registration_end_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    rules: dict | None = None
    prize_pool: Decimal | None = None
    discord_webhook_url: str | None = None
    description: str | None = None
    is_public: bool | None = None


class TournamentSummary(BaseModel):
    id: str
    name: str
    game: GameType
    format: TournamentFormat
    status: TournamentStatus
    max_teams: int
    registered_teams: int
    start_at: datetime | None
    prize_pool: Decimal | None
    banner_url: str | None

    model_config = {"from_attributes": True}


class TournamentDetail(TournamentSummary):
    description: str | None
    rules: dict | None
    organizer_id: str
    registration_start_at: datetime | None
    registration_end_at: datetime | None
    check_in_start_at: datetime | None
    end_at: datetime | None
    require_check_in: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegistrationRequest(BaseModel):
    team_id: str
    notes: str | None = None


class BracketMatchTeam(BaseModel):
    id: str | None
    name: str | None
    tag: str | None
    logo_url: str | None


class BracketMatch(BaseModel):
    id: str
    round_number: int
    match_number: int
    team1: BracketMatchTeam | None
    team2: BracketMatchTeam | None
    winner_id: str | None
    status: str
    scheduled_at: datetime | None

    model_config = {"from_attributes": True}


class BracketResponse(BaseModel):
    tournament_id: str
    format: TournamentFormat
    rounds: dict[int, list[BracketMatch]]
