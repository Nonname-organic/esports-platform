from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.core.redis import get_redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    """スライディングウィンドウ方式のレート制限。"""

    SKIP_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}

    # 1リクエストに秒単位のCPUを使うエンドポイントは通常の上限では守れない。
    # パス末尾ごとに厳しい上限を別途設ける（値は「窓あたりの回数」）
    COSTLY_SUFFIXES: dict[str, int] = {
        "/scoreboard-ocr": 6,
    }

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

        redis = await get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)

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
        if auth.startswith("Bearer "):
            # トークンの末尾16文字をIDとして使用（デコードコスト回避）
            return f"token:{auth[-16:]}"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        return f"ip:{request.client.host if request.client else 'unknown'}"
