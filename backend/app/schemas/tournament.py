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
    attachments: list[dict] | None = None
    is_public: bool = True
    require_check_in: bool = False
    # 参加申請の承認方式: manual（主催者が個別承認）/ auto（先着順で自動承認）
    approval_mode: str = Field(default="manual", pattern="^(manual|auto|lottery)$")

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
    """大会情報の更新。作成フォームで設定した項目を後から全て編集できるようにする。

    作成時に rules(JSON) へ格納している拡張項目（賞金内訳・配信・Discord・スポンサー・
    連絡先・分析設定など）は、rules をまるごと差し替えることで更新する。
    """

    name: str | None = Field(default=None, min_length=2, max_length=200)
    status: TournamentStatus | None = None
    format: TournamentFormat | None = None
    max_teams: int | None = Field(default=None, ge=2, le=256)
    min_teams: int | None = Field(default=None, ge=2)
    registration_start_at: datetime | None = None
    registration_end_at: datetime | None = None
    check_in_start_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    rules: dict | None = None
    prize_pool: Decimal | None = None
    prize_currency: str | None = Field(default=None, max_length=3)
    discord_webhook_url: str | None = None
    description: str | None = None
    attachments: list[dict] | None = None
    is_public: bool | None = None
    require_check_in: bool | None = None
    require_team_membership: bool | None = None
    approval_mode: str | None = Field(default=None, pattern="^(manual|auto|lottery)$")
    # 作成フォームの拡張項目のうち、tournaments テーブルに実カラムがあるもの
    subtitle: str | None = Field(default=None, max_length=200)
    banner_url: str | None = None
    thumbnail_url: str | None = None
    season: str | None = Field(default=None, max_length=50)
    split: str | None = Field(default=None, max_length=50)
    tier: str | None = Field(default=None, max_length=20)
    visibility: str | None = Field(default=None, max_length=20)
    seeding_type: str | None = Field(default=None, max_length=20)
    age_restriction: dict | None = None
    region_restriction: dict | None = None
    rank_restriction: dict | None = None
    analytics_enabled: bool | None = None
    player_stats_enabled: bool | None = None
    ranking_enabled: bool | None = None


class TournamentSummary(BaseModel):
    id: str
    name: str
    game: GameType
    format: TournamentFormat
    status: TournamentStatus
    max_teams: int
    registered_teams: int
    registration_start_at: datetime | None = None
    registration_end_at: datetime | None = None
    start_at: datetime | None
    end_at: datetime | None = None
    prize_pool: Decimal | None
    banner_url: str | None

    model_config = {"from_attributes": True}


class TournamentDetail(TournamentSummary):
    description: str | None
    rules: dict | None
    attachments: list[dict] | None = None
    organizer_id: str
    registration_start_at: datetime | None
    registration_end_at: datetime | None
    check_in_start_at: datetime | None
    end_at: datetime | None
    require_check_in: bool
    created_at: datetime
    updated_at: datetime
    # 編集フォームで初期値として読み戻すための項目（作成フォームと対応）
    subtitle: str | None = None
    thumbnail_url: str | None = None
    season: str | None = None
    split: str | None = None
    tier: str | None = None
    visibility: str | None = None
    seeding_type: str | None = None
    min_teams: int | None = None
    prize_currency: str | None = None
    require_team_membership: bool | None = None
    approval_mode: str | None = Field(default=None, pattern="^(manual|auto|lottery)$")
    age_restriction: dict | None = None
    region_restriction: dict | None = None
    rank_restriction: dict | None = None
    # Webhook URL は返却しない（実質的な認証情報のため常に None）。
    # 編集画面が「設定済みかどうか」を判別できるようフラグだけ渡す
    discord_webhook_url: str | None = None
    discord_webhook_configured: bool = False
    analytics_enabled: bool | None = None
    player_stats_enabled: bool | None = None
    ranking_enabled: bool | None = None
    is_public: bool | None = None

    model_config = {"from_attributes": True}


class RegistrationRequest(BaseModel):
    team_id: str
    notes: str | None = None


class RegistrationInfo(BaseModel):
    id: str
    team_id: str
    team_name: str
    team_tag: str
    team_logo_url: str | None
    status: str
    notes: str | None
    registered_at: datetime


class StatusChangeRequest(BaseModel):
    status: TournamentStatus


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
    # ダブルエリミネーションでの所属（winners / losers / grand_finals）。
    # シングルエリミ・総当たりでは null
    bracket_side: str | None = None

    model_config = {"from_attributes": True}


class BracketResponse(BaseModel):
    tournament_id: str
    format: TournamentFormat
    # round_number をキーに全試合を返す。ダブルエリミネーションでは
    # 各試合の bracket_side（winners/losers/grand_finals）で振り分ける
    rounds: dict[int, list[BracketMatch]]
