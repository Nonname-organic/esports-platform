import re
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("パスワードは大文字を1文字以上含む必要があります")
        if not re.search(r"[0-9]", v):
            raise ValueError("パスワードは数字を1文字以上含む必要があります")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    role: UserRole
    is_active: bool
    discord_id: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}
