import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.core.redis import get_redis
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    JWTError,
    decode_token,
    verify_token_type,
)

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """スライディングウィンドウ方式のレート制限。"""

    SKIP_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}

    # 1リクエストに秒単位のCPUを使うエンドポイントは通常の上限では守れない。
    # パス末尾ごとに厳しい上限を別途設ける（値は「窓あたりの回数」）
    COSTLY_SUFFIXES: dict[str, int] = {
        "/scoreboard-ocr": 6,
        # 認証まわりは総当たりの的になる。通常の操作では窓あたり数回しか
        # 叩かないので、きつめに絞っても使い勝手は変わらない
        "/auth/login": 10,
        "/auth/register": 5,
        "/auth/forgot-password": 5,
        "/auth/reset-password": 5,
        "/auth/refresh": 20,
    }

    # 総当たりの的になる認証系は、ヘッダに何が付いていても常に IP で数える
    IP_ONLY_SUFFIXES = ("/auth/login", "/auth/register", "/auth/forgot-password", "/auth/reset-password")

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in self.SKIP_PATHS:
            return await call_next(request)

        limit = settings.RATE_LIMIT_REQUESTS
        for suffix, costly_limit in self.COSTLY_SUFFIXES.items():
            if path.endswith(suffix):
                limit = costly_limit
                break

        # 認証済みユーザーはuser_id、未認証はIPでレート制限
        identifier = self._get_identifier(request)
        endpoint = path.replace("/", "_")[:50]
        key = f"ratelimit:{identifier}:{endpoint}"

        try:
            redis = await get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
        except (RedisError, OSError) as exc:
            # Redis が落ちている間も API 自体は動かし続ける。ここで例外を
            # 投げると全リクエストが 500 になり、レート制限のために
            # サイト全体を落とすことになる
            logger.warning(
                "rate_limit_unavailable", error=str(exc), path=path
            )
            return await call_next(request)

        if count > limit:
            # BaseHTTPMiddleware 内で raise した例外は FastAPI の exception handler を
            # 通らず 500 になる。app_exception_handler と同じ形式で 429 を直接返す。
            exc = RateLimitError()
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "type": exc.error_type,
                    "title": exc.detail,
                    "status": exc.status_code,
                    "detail": exc.detail,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response

    def _get_identifier(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer ") and not request.url.path.endswith(self.IP_ONLY_SUFFIXES):
            # 署名を検証できたアクセストークンだけをユーザーとして数える（HS256 なので安い）。
            # 未検証の値で数えると、毎回でたらめなトークンを付けるだけで制限をすり抜けられる
            try:
                payload = decode_token(auth[7:])
            except JWTError:
                payload = {}
            if verify_token_type(payload, ACCESS_TOKEN_TYPE) and payload.get("sub"):
                return f"user:{payload['sub']}"
        # X-Forwarded-For はクライアントが先頭に任意の値を入れられる
        # （nginx は追記するだけ）。偽の値を回すと制限をすり抜けられるため、
        # nginx が $remote_addr から立てる X-Real-IP を優先する
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return f"ip:{real_ip.strip()}"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # 直前のプロキシが付けた末尾側が信用できる
            return f"ip:{forwarded_for.split(',')[-1].strip()}"
        return f"ip:{request.client.host if request.client else 'unknown'}"
