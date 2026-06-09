from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    APP_NAME: str = "e-sports Platform API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["demo", "mvp", "prod"] = "demo"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "esports_db"
    DB_USER: str = "esports_user"
    DB_PASSWORD: str = Field(...)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Set True for Neon / any hosted PostgreSQL that requires TLS.
    DB_SSL_REQUIRED: bool = False

    @property
    def database_url(self) -> str:
        url = (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
        return url + "?ssl=require" if self.DB_SSL_REQUIRED else url

    @property
    def sync_database_url(self) -> str:
        url = (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
        return url + "?sslmode=require" if self.DB_SSL_REQUIRED else url

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_MAX_CONNECTIONS: int = 20
    # Set True for Upstash or any Redis that requires TLS (rediss:// scheme).
    REDIS_TLS: bool = False

    @property
    def redis_url(self) -> str:
        scheme = "rediss" if self.REDIS_TLS else "redis"
        if self.REDIS_PASSWORD:
            return f"{scheme}://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"{scheme}://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # AWS / Storage
    AWS_REGION: str = "ap-northeast-1"
    S3_BUCKET_NAME: str = ""
    # Set to Cloudflare R2 endpoint for $0 demo, leave None for native AWS S3.
    # Example: "https://<account-id>.r2.cloudflarestorage.com"
    S3_ENDPOINT_URL: str | None = None

    # Queue — SQS (default) or Redis list (USE_REDIS_QUEUE=true for free-tier demo)
    USE_REDIS_QUEUE: bool = False
    SQS_MATCH_QUEUE_URL: str | None = None
    SQS_NOTIFICATION_QUEUE_URL: str | None = None
    SQS_ANALYTICS_QUEUE_URL: str | None = None

    # Redis queue key names (used when USE_REDIS_QUEUE=true)
    REDIS_QUEUE_MATCH_KEY: str = "queue:match_events"
    REDIS_QUEUE_NOTIFICATION_KEY: str = "queue:notification_events"
    REDIS_QUEUE_ANALYTICS_KEY: str = "queue:analytics_events"

    # Discord
    DISCORD_WEBHOOK_URL: str | None = None
    DISCORD_BOT_TOKEN: str | None = None
    DISCORD_CLIENT_ID: str | None = None
    DISCORD_CLIENT_SECRET: str | None = None
    DISCORD_REDIRECT_URI: str | None = None
    SQS_DISCORD_QUEUE_URL: str | None = None
    REDIS_QUEUE_DISCORD_KEY: str = "queue:discord_events"

    # Riot Games API
    RIOT_API_KEY: str | None = None
    RIOT_ACCOUNT_REGION: str = "asia"   # asia / americas / europe
    RIOT_VAL_REGION: str = "ap"          # ap / na / eu / kr

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # Rate Limit
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Sentry
    SENTRY_DSN: str | None = None

    # Upload
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB

    # Observability
    LOG_LEVEL: str = "INFO"
    # OTLP gRPC endpoint for OpenTelemetry traces.
    # Example: "http://otel-collector.monitoring.svc.cluster.local:4317"
    # Leave unset in dev — spans are created but discarded.
    OTLP_ENDPOINT: str | None = None
    # Injected by CI: identifies the deployed image in logs and app_info metric.
    IMAGE_TAG: str = "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
