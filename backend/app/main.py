from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.v1.router import api_router
from app.api.ws.match import router as ws_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_structlog
from app.core.metrics import app_info
from app.core.redis import close_redis, get_redis
from app.middleware.observability import ObservabilityMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

configure_structlog(
    log_level=settings.LOG_LEVEL,
    json_logs=settings.ENVIRONMENT != "demo",
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", env=settings.ENVIRONMENT, version=settings.IMAGE_TAG)
    app_info.info(
        {"version": settings.IMAGE_TAG, "environment": settings.ENVIRONMENT}
    )
    await get_redis()
    yield
    await close_redis()
    logger.info("shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "prod" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "prod" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "prod" else None,
    lifespan=lifespan,
)

# ===== Telemetry (must be called before app starts) =====
from app.core.telemetry import setup_telemetry
setup_telemetry(app, settings)

# ===== Middleware =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
# Outermost middleware: generates request_id, logs every request, records metrics.
# Must be added last so it wraps all other middleware.
app.add_middleware(ObservabilityMiddleware)


# ===== Exception Handlers =====
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": exc.error_type,
            "title": exc.detail,
            "status": exc.status_code,
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", exc=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "internal_server_error",
            "title": "内部サーバーエラーが発生しました",
            "status": 500,
            "detail": "予期せぬエラーが発生しました",
        },
    )


# ===== Routers =====
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health — used by docker-compose and ALB healthcheck."""
    return {"status": "ok", "version": settings.APP_VERSION, "env": settings.ENVIRONMENT}


@app.get("/health/live", tags=["Health"])
async def liveness():
    """Kubernetes liveness probe — 200 if the process is running."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
async def readiness():
    """Kubernetes readiness probe — 503 if DB or cache are unreachable."""
    from sqlalchemy import text

    from app.core.database import async_session_factory
    from app.core.redis import get_redis

    checks: dict[str, str] = {}

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    try:
        redis = await get_redis()
        await redis.ping()
        checks["cache"] = "ok"
    except Exception as exc:
        checks["cache"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    payload = {"status": "ready" if all_ok else "degraded", "checks": checks}
    return JSONResponse(payload, status_code=200 if all_ok else 503)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Prometheus scrape endpoint — read by ServiceMonitor in Kubernetes."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
