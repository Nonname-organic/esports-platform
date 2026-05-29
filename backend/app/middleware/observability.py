import re
import time
import uuid
from typing import Callable

import structlog
import structlog.contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.metrics import http_request_duration_seconds, http_requests_total

logger = structlog.get_logger()

# Normalise dynamic path segments so Prometheus label cardinality stays bounded.
# /api/v1/tournaments/3fa85f64-5717-...  →  /api/v1/tournaments/{id}
# /api/v1/matches/42/games/1/score       →  /api/v1/matches/{id}/games/{id}/score
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)
_INT_SEGMENT_RE = re.compile(r"(?<=/)\d+(?=/|$)")

# Paths that are too noisy to record per-path (just record as-is)
_SKIP_METRIC_PATHS = frozenset(["/health", "/health/live", "/health/ready", "/metrics"])


def _normalize_path(path: str) -> str:
    path = _UUID_RE.sub("{id}", path)
    path = _INT_SEGMENT_RE.sub("{id}", path)
    return path


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Per-request: generate request_id, structured log, Prometheus metrics.

    Must be the outermost middleware (added last via add_middleware) so it
    captures the full round-trip time including rate-limiting and CORS.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            logger.exception("http_request_unhandled", duration_ms=round(duration * 1000, 2))
            raise

        duration = time.perf_counter() - start
        status_code = response.status_code

        path = request.url.path
        if path not in _SKIP_METRIC_PATHS:
            norm_path = _normalize_path(path)
            http_requests_total.labels(
                method=request.method,
                path=norm_path,
                status_code=str(status_code),
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                path=norm_path,
            ).observe(duration)

        log_level = "warning" if status_code >= 400 else "info"
        getattr(logger, log_level)(
            "http_request",
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
        )

        response.headers["X-Request-ID"] = request_id
        return response
