import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import GameType, MemberRole


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    tag: str = Field(..., min_length=2, max_length=10, pattern=r"^[A-Za-z0-9]+$")
    game: GameType
    description: Optional[str] = Field(None, max_length=1000)
    country: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = Field(None, max_length=2048)
    banner_url: Optional[str] = Field(None, max_length=2048)
    twitter_handle: Optional[str] = Field(None, max_length=50)


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    tag: Optional[str] = Field(None, min_length=2, max_length=10, pattern=r"^[A-Za-z0-9]+$")
    description: Optional[str] = Field(None, max_length=1000)
    country: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = Field(None, max_length=2048)
    banner_url: Optional[str] = Field(None, max_length=2048)
    twitter_handle: Optional[str] = Field(None, max_length=50)
    # 傾向分析（第2層）の公開設定。結果・ランキング（第1層）はこの設定に関わらず公開。
    stats_public: Optional[bool] = None


class TeamSummarySchema(BaseModel):
    id: uuid.UUID
    name: str
    tag: str
    game: str
    logo_url: Optional[str]
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamDetailSchema(TeamSummarySchema):
    description: Optional[str]
    country: Optional[str]
    banner_url: Optional[str]
    twitter_handle: Optional[str]
    stats_public: bool = True
    updated_at: datetime


class TeamMemberSchema(BaseModel):
    id: uuid.UUID
    player_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    in_game_name: Optional[str]
    username: Optional[str]
    avatar_url: Optional[str]
    role: str
    jersey_number: Optional[int]
    joined_at: datetime
    is_active: bool
    # RC4: 承諾の状態と、正式な所属として扱うか（期限の後の本人未確認は False）
    consent: Optional[str] = None
    formal: bool = True


class AddMemberRequest(BaseModel):
    username: str = Field(..., description="招待するユーザーのユーザー名")
    role: MemberRole = MemberRole.PLAYER
    jersey_number: Optional[int] = Field(None, ge=1, le=99)


class UpdateMemberRoleRequest(BaseModel):
    role: MemberRole


# ── RC4: 招待と所属の確認 ─────────────────────────────────────────────────────

class TeamInvitationCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="招待するユーザーのユーザー名")
    role: MemberRole = MemberRole.PLAYER


class TeamInvitationSchema(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    invitee_user_id: uuid.UUID
    invited_by_user_id: Optional[uuid.UUID]
    role: MemberRole
    status: str
    created_at: datetime
    expires_at: datetime
    decided_at: Optional[datetime]
    membership_id: Optional[uuid.UUID]
    # チームの管理者の一覧でだけ入れる（招待したときに自分で入れたユーザー名）
    invitee_username: Optional[str] = None

    model_config = {"from_attributes": True}


class MyTeamInvitationSchema(TeamInvitationSchema):
    team_name: str
    team_tag: str


class MembershipSchema(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    team_name: str
    team_tag: str
    role: str
    joined_at: datetime
    left_at: Optional[datetime]
    consent: str
    confirmed_at: Optional[datetime]
    rejected_at: Optional[datetime]
    formal: bool


class MyMembershipsResponse(BaseModel):
    deadline: Optional[datetime]
    items: list[MembershipSchema]


class ReasonRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)
