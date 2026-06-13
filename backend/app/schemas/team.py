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


class AddMemberRequest(BaseModel):
    username: str = Field(..., description="招待するユーザーのユーザー名")
    role: MemberRole = MemberRole.PLAYER
    jersey_number: Optional[int] = Field(None, ge=1, le=99)


class UpdateMemberRoleRequest(BaseModel):
    role: MemberRole
