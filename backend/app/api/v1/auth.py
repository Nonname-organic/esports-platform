import secrets
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import Cache, CurrentUser, DBSession
from app.core.exceptions import BusinessRuleError, UnauthorizedError
from app.core.redis import RedisCache
from app.core import email as mailer
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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/forgot-password", status_code=202)
async def forgot_password(data: ForgotPasswordRequest, db: DBSession, cache: Cache):
    """パスワードリセットメールを要求する。

    アドレスの存在有無を推測されないよう、該当ユーザーが居ても居なくても
    同じ 202 を返す。トークンは Redis に30分だけ保持し、使い捨てにする。
    """
    user = await db.scalar(select(User).where(User.email == data.email))
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        await cache.set(f"pwreset:{token}", str(user.id), ttl=30 * 60)
        reset_url = f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}"
        body = f"""{user.username} さん

パスワード再設定のリクエストを受け付けました。
以下のURLから30分以内に新しいパスワードを設定してください。

{reset_url}

このリクエストに心当たりがない場合は、このメールを破棄してください。
（その場合パスワードは変更されません）

AXELIA"""
        await mailer.send_email(
            to=user.email,
            subject="【AXELIA】パスワード再設定のご案内",
            body=body,
        )
    return {"detail": "受け付けました。登録済みのアドレスであればメールが届きます"}


@router.post("/reset-password", status_code=204)
async def reset_password(data: ResetPasswordRequest, db: DBSession, cache: Cache):
    """リセットトークンで新しいパスワードを設定する。"""
    key = f"pwreset:{data.token}"
    user_id = await cache.get(key)
    if not user_id:
        raise UnauthorizedError("リンクが無効か期限切れです。もう一度リセットを依頼してください")

    # 先にトークンを消す（同じリンクの二重使用を防ぐ）
    await cache.delete(key)

    user = await db.get(User, uuid.UUID(str(user_id)))
    if not user or not user.is_active:
        raise UnauthorizedError("アカウントが見つかりません")

    user.hashed_password = hash_password(data.new_password)
    await db.flush()


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
