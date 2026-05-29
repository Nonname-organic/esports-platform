import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis import CacheKeys, RedisCache, get_redis
from app.core.security import ACCESS_TOKEN_TYPE, decode_token, verify_token_type
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_cache(redis: aioredis.Redis = Depends(get_redis)) -> RedisCache:
    return RedisCache(redis)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    cache: RedisCache = Depends(get_cache),
) -> uuid.UUID:
    if credentials is None:
        raise UnauthorizedError()

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("無効なトークンです")

    if not verify_token_type(payload, ACCESS_TOKEN_TYPE):
        raise UnauthorizedError("アクセストークンが必要です")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError()

    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError()


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    from app.models.user import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("ユーザーが存在しないか無効化されています")
    return user


def require_roles(*roles: UserRole):
    """指定ロールのいずれかを持つユーザーのみ通過させるDependency。"""

    async def _check(user=Depends(get_current_user)):
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return _check


# よく使う型エイリアス
CurrentUser = Annotated["User", Depends(get_current_user)]  # type: ignore[name-defined]  # noqa: F821
DBSession = Annotated[AsyncSession, Depends(get_db)]
Cache = Annotated[RedisCache, Depends(get_cache)]
AdminUser = Annotated["User", Depends(require_roles(UserRole.ADMIN))]  # type: ignore[name-defined]  # noqa: F821
OrganizerUser = Annotated[
    "User",  # type: ignore[name-defined]  # noqa: F821
    Depends(require_roles(UserRole.ADMIN, UserRole.ORGANIZER)),
]
