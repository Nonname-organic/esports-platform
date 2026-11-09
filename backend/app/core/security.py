import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

JWTError = jwt.PyJWTError  # 呼び出し側が従来どおり JWTError で捕捉するための別名

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

REFRESH_TOKEN_TYPE = "refresh"
ACCESS_TOKEN_TYPE = "access"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# bcrypt は1回0.3秒前後CPUを使う。リクエスト処理（async）から直接呼ぶとその間
# イベントループが止まり、他の全リクエストが待たされる（並列のログインで顕著）。
# async の経路からは必ずこちらを使い、スレッドプールで計算する。
async def hash_password_async(password: str) -> str:
    return await run_in_threadpool(hash_password, password)


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    return await run_in_threadpool(verify_password, plain_password, hashed_password)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": ACCESS_TOKEN_TYPE,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": REFRESH_TOKEN_TYPE,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def password_stamp(hashed_password: str) -> str:
    """パスワードのハッシュから作る印（S9）。トークンの "pwv" に入れる。

    トークンを使うたびに今のハッシュの印と比べる。パスワードを変える・再設定すると
    ハッシュが変わるので、それより前に発行したトークンは、他の端末のものも含めて
    通らなくなる。HMAC なので、トークンの中身からハッシュは分からない。
    """
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, hashed_password.encode(), hashlib.sha256).hexdigest()[:32]


SESSION_REVOKED = "セッションが無効になりました。もう一度ログインしてください"


def stamp_matches(payload: dict[str, Any], hashed_password: str) -> bool:
    """印の無いトークン（この仕組みより前に発行したもの）も通さない。"""
    stamp = payload.get("pwv")
    return isinstance(stamp, str) and hmac.compare_digest(stamp, password_stamp(hashed_password))


def issue_tokens(user: Any) -> tuple[str, str]:
    """ログインと更新で渡すアクセストークンとリフレッシュトークン。"""
    stamp = {"pwv": password_stamp(user.hashed_password)}
    access = create_access_token(str(user.id), {"role": user.role.value, **stamp})
    return access, create_refresh_token(str(user.id), stamp)


def decode_token(token: str) -> dict[str, Any]:
    """トークンをデコード（署名方式は HS256 固定）。失敗時は JWTError を raise する。"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def verify_token_type(payload: dict[str, Any], expected_type: str) -> bool:
    return payload.get("type") == expected_type
