from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.core.exceptions import BusinessRuleError, UnauthorizedError
from app.core.redis import RedisCache
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["認証"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangeEmailRequest(BaseModel):
    password: str
    new_email: EmailStr


class DeleteAccountRequest(BaseModel):
    password: str


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, db: DBSession, cache: Cache):
    service = AuthService(db, cache)
    user = await service.register(data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DBSession, cache: Cache):
    service = AuthService(db, cache)
    return await service.login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: DBSession, cache: Cache):
    service = AuthService(db, cache)
    return await service.refresh(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser):
    return UserResponse.model_validate(current_user)


@router.patch("/password", status_code=204)
async def change_password(data: ChangePasswordRequest, db: DBSession, current_user: CurrentUser):
    """パスワード変更（現在のパスワード確認が必要）。"""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise UnauthorizedError("現在のパスワードが正しくありません")
    current_user.hashed_password = hash_password(data.new_password)
    await db.flush()


@router.patch("/email", response_model=UserResponse)
async def change_email(data: ChangeEmailRequest, db: DBSession, current_user: CurrentUser):
    """メールアドレス変更（パスワード確認が必要）。"""
    if not verify_password(data.password, current_user.hashed_password):
        raise UnauthorizedError("パスワードが正しくありません")
    dupe = await db.scalar(
        select(User).where(User.email == data.new_email, User.id != current_user.id)
    )
    if dupe:
        raise BusinessRuleError("このメールアドレスは既に使用されています")
    current_user.email = data.new_email
    current_user.is_email_verified = False
    await db.flush()
    return UserResponse.model_validate(current_user)


@router.delete("/account", status_code=204)
async def delete_account(data: DeleteAccountRequest, db: DBSession, current_user: CurrentUser):
    """退会（パスワード確認）。所有チーム等のFK制約に配慮し論理削除。以後ログイン不可。"""
    if not verify_password(data.password, current_user.hashed_password):
        raise UnauthorizedError("パスワードが正しくありません")
    current_user.is_active = False
    await db.flush()
