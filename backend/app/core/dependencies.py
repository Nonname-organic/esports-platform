import uuid
from typing import Annotated, Any, Optional

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis import CacheKeys, RedisCache, get_redis
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    SESSION_REVOKED,
    JWTError,
    decode_token,
    stamp_matches,
    verify_token_type,
)
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_cache(redis: aioredis.Redis = Depends(get_redis)) -> RedisCache:
    return RedisCache(redis)


async def get_access_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """アクセストークンを検証して中身を返す（sub は UUID として読めることを確認済み）。"""
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
        uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError()
    return payload


async def get_current_user(
    payload: dict[str, Any] = Depends(get_access_payload),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    from sqlalchemy import select

    from app.models.user import User

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("ユーザーが存在しないか無効化されています")
    # パスワードを変えた・再設定した後は、それ以前に発行したトークンを通さない（S9）
    if not stamp_matches(payload, user.hashed_password):
        raise UnauthorizedError(SESSION_REVOKED)
    # イベント/監査が actor を引数無しで取得できるよう、リクエストコンテキストへ載せる。
    from app.core.context import set_actor
    set_actor(str(user.id))
    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> "User | None":  # type: ignore[name-defined]  # noqa: F821
    """公開エンドポイントで閲覧者を知るための任意認証。トークンが無い・無効なら None。"""
    if credentials is None:
        return None
    try:
        return await get_current_user(await get_access_payload(credentials), db)
    except UnauthorizedError:
        return None


def require_roles(*roles: UserRole):
    """指定ロールのいずれかを持つユーザーのみ通過させるDependency。"""

    async def _check(user=Depends(get_current_user)):
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return _check


# ── Discord Bot service auth (X-Bot-Secret) ──────────────────────────────────
async def verify_bot_secret(
    x_bot_secret: Optional[str] = Header(default=None, alias="X-Bot-Secret"),
) -> None:
    """Bot↔Backend 共有秘密を検証。/api/v1/bot/* 全体のゲート。"""
    expected = settings.BOT_API_TOKEN
    if not expected or x_bot_secret != expected:
        raise UnauthorizedError("Bot認証に失敗しました")


async def resolve_discord_user(
    x_discord_user_id: Optional[str] = Header(default=None, alias="X-Discord-User-Id"),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> "Optional[User]":  # type: ignore[name-defined]  # noqa: F821
    """X-Discord-User-Id → DiscordLink → User を解決（未連携ならNone）。

    Bot経由の代理実行で「実ユーザーの権限」を権威判定するために使う。
    """
    from app.models.discord import DiscordLink
    from app.models.user import User

    if not x_discord_user_id:
        return None
    result = await db.execute(
        select(User)
        .join(DiscordLink, DiscordLink.user_id == User.id)
        .where(DiscordLink.discord_user_id == str(x_discord_user_id), User.is_active == True)
    )
    return result.scalar_one_or_none()


# よく使う型エイリアス
CurrentUser = Annotated["User", Depends(get_current_user)]  # type: ignore[name-defined]  # noqa: F821
OptionalUser = Annotated["User | None", Depends(get_optional_user)]  # type: ignore[name-defined]  # noqa: F821
BotAuth = Annotated[None, Depends(verify_bot_secret)]
BotActor = Annotated["Optional[User]", Depends(resolve_discord_user)]  # type: ignore[name-defined]  # noqa: F821
# scope="function": get_db のコミットを「応答を返す前」に行う。既定（request）だと
# 応答を送った後にコミットされ、直後の別リクエスト（登録→自動ログインなど）が
# 未コミットのデータを読めない・コミット失敗が成功応答のまま届く、という不整合になる。
# get_db を使う依存はすべて同じ scope に揃える（揃えないと別セッションになる）。
DBSession = Annotated[AsyncSession, Depends(get_db, scope="function")]
Cache = Annotated[RedisCache, Depends(get_cache)]
AdminUser = Annotated["User", Depends(require_roles(UserRole.ADMIN))]  # type: ignore[name-defined]  # noqa: F821
OrganizerUser = Annotated[
    "User",  # type: ignore[name-defined]  # noqa: F821
    Depends(require_roles(UserRole.ADMIN, UserRole.ORGANIZER)),
]
