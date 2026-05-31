import uuid
from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, UnauthorizedError
from app.core.redis import CacheKeys, CacheTTL, RedisCache
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    verify_token_type,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    async def register(self, data: RegisterRequest) -> User:
        existing_email = await self._db.execute(
            select(User).where(User.email == data.email)
        )
        if existing_email.scalar_one_or_none():
            raise AlreadyExistsError("このメールアドレスは既に登録されています")

        existing_username = await self._db.execute(
            select(User).where(User.username == data.username)
        )
        if existing_username.scalar_one_or_none():
            raise AlreadyExistsError("このユーザー名は既に使用されています")

        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            role=data.role if data.role in (UserRole.PLAYER, UserRole.ORGANIZER) else UserRole.PLAYER,
            is_active=True,
        )
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def login(self, data: LoginRequest) -> TokenResponse:
        result = await self._db.execute(
            select(User).where(User.email == data.email, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("メールアドレスまたはパスワードが正しくありません")

        access_token = create_access_token(
            subject=str(user.id),
            extra={"role": user.role.value},
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        # Refresh Token を Redis に保存（無効化可能にするため）
        jti = str(uuid.uuid4())
        cache_key = CacheKeys.REFRESH_TOKEN.replace("{user_id}", str(user.id)).replace(
            "{jti}", jti
        )
        await self._cache.set(
            cache_key,
            {"user_id": str(user.id), "valid": True},
            ttl=CacheTTL.REFRESH_TOKEN,
        )

        from app.core.config import settings

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("無効なリフレッシュトークンです")

        if not verify_token_type(payload, REFRESH_TOKEN_TYPE):
            raise UnauthorizedError("リフレッシュトークンが必要です")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError()

        result = await self._db.execute(
            select(User).where(
                User.id == uuid.UUID(user_id), User.is_active == True
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise UnauthorizedError("ユーザーが存在しません")

        access_token = create_access_token(
            subject=str(user.id),
            extra={"role": user.role.value},
        )
        new_refresh_token = create_refresh_token(subject=str(user.id))

        from app.core.config import settings

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
