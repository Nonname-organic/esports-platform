import re
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # 設定エラーの文面に入力値を載せない（SECRET_KEY 等がそのまま起動ログに出るため）
        hide_input_in_errors=True,
    )

    # App
    APP_NAME: str = "e-sports Platform API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["demo", "mvp", "prod"] = "demo"
    DEBUG: bool = False
    # /docs・/redoc・/openapi.json を公開するか。インターネット公開時は
    # 管理系を含む全エンドポイントが一覧できてしまうため既定で無効
    EXPOSE_API_DOCS: bool = False
    # /metrics を公開するか。未認証で到達すると、パス別のリクエスト数・
    # エラー率・レイテンシと、稼働中のイメージタグが読めるため既定で無効。
    # 監視を入れる段では、有効化と同時に認証方式（共有秘密など）も決める。
    # 有効化しただけでは無認証のまま公開される。
    EXPOSE_METRICS: bool = False

    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    # 本番（docker-compose.prod.yml）で true にする。DB のパスワードが空・既定値、
    # SECRET_KEY が見本・テスト用の値なら起動しない（読み込み時に enforce_production_settings で確かめる）
    REQUIRE_STRONG_SECRETS: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "esports_db"
    DB_USER: str = "esports_user"
    # DATABASE_URL 運用時は未使用のため任意にしている
    DB_PASSWORD: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Set True for Neon / any hosted PostgreSQL that requires TLS.
    DB_SSL_REQUIRED: bool = False

    # マネージドDB（Neon等）が発行する接続文字列を1本で受け付ける。
    # 設定されている場合は DB_HOST 等の個別指定より優先される。
    # 例: postgresql://user:pass@host/db?sslmode=require
    DATABASE_URL: str | None = None

    def _split_database_url(self):
        """DATABASE_URL を (ホスト部, ssl要否) に正規化する。"""
        if not self.DATABASE_URL:
            return None
        url = self.DATABASE_URL
        for prefix in ("postgresql+asyncpg://", "postgresql+psycopg2://",
                       "postgresql://", "postgres://"):
            if url.startswith(prefix):
                url = url[len(prefix):]
                break
        # sslmode等のクエリはドライバ別に付け直すため剥がす
        base = url.split("?", 1)[0]
        needs_ssl = "sslmode=require" in self.DATABASE_URL or self.DB_SSL_REQUIRED
        return base, needs_ssl

    @property
    def database_url(self) -> str:
        parsed = self._split_database_url()
        if parsed:
            base, ssl = parsed
            # asyncpg は sslmode ではなく ssl パラメータを使う
            return f"postgresql+asyncpg://{base}" + ("?ssl=require" if ssl else "")
        url = (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
        return url + "?ssl=require" if self.DB_SSL_REQUIRED else url

    @property
    def sync_database_url(self) -> str:
        parsed = self._split_database_url()
        if parsed:
            base, ssl = parsed
            return f"postgresql+psycopg2://{base}" + ("?sslmode=require" if ssl else "")
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

    # マネージドRedis（Upstash等）の接続文字列を1本で受け付ける。
    # 設定されている場合は REDIS_HOST 等より優先される。
    REDIS_URL: str | None = None

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
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
    # 分析イベントの夜間書き出し先（daily_s3_export）。未設定なら書き出さない。
    # 以前は画像用の S3_BUCKET_NAME を endpoint なしで使い、AWS S3 へ向かっていた
    ANALYTICS_EXPORT_BUCKET: str = ""

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
    # ── メール送信（パスワードリセット等） ──────────────────────────────────
    # SMTP_HOST 未設定の環境では送信しない（本文は LOG_LEVEL=DEBUG のときだけログに出す）
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_SSL: bool = False  # True: SMTPS(465) / False: STARTTLS(587)
    MAIL_FROM: str = "noreply@localhost"
    MAIL_FROM_NAME: str = "AXELIA"
    # リセットリンクの基点URL（フロントの公開URL）
    FRONTEND_BASE_URL: str = "http://localhost"

    DISCORD_WEBHOOK_URL: str | None = None
    DISCORD_BOT_TOKEN: str | None = None
    DISCORD_CLIENT_ID: str | None = None
    DISCORD_CLIENT_SECRET: str | None = None
    DISCORD_REDIRECT_URI: str | None = None
    SQS_DISCORD_QUEUE_URL: str | None = None
    REDIS_QUEUE_DISCORD_KEY: str = "queue:discord_events"
    # Bot↔Backend 共有秘密（/api/v1/bot/* のservice認証）。Discord Botと同値を設定する。
    BOT_API_TOKEN: str | None = None
    # Botが埋め込みリンクに使う公開URL（バックエンドでは通知action_url等に利用可）
    PUBLIC_WEB_URL: str = "https://d3r8lgt0kvo61v.cloudfront.net"

    # Riot Games API
    RIOT_API_KEY: str | None = None
    RIOT_ACCOUNT_REGION: str = "asia"   # asia / americas / europe
    RIOT_VAL_REGION: str = "ap"          # ap / na / eu / kr
    RIOT_SYNC_INTERVAL_HOURS: int = 6    # 0 で自動同期OFF
    RIOT_SYNC_DELAY_SECONDS: float = 2.0  # プロフィール間の待機（レート制限緩和）

    # CORS — NoDecode で pydantic-settings のJSON先行デコードを止め、
    # validator でカンマ区切り文字列 (例: "http://a.com,http://b.com") を受け付ける
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # Host ヘッダとして受け付ける名前。ALLOWED_ORIGINS とは別物で、
    # 「このAPIがどの名前で呼ばれるか」を書く。CORS の許可先とは一致しない。
    # Render は axelia-api.onrender.com でヘルスチェックに来るが、その名前は
    # フロントのオリジンではないので ALLOWED_ORIGINS には入らない。
    # 空のままなら ALLOWED_ORIGINS から導出する従来の挙動に落ちる（全許可にはしない）。
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = []

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_hosts(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [h.strip() for h in v.split(",") if h.strip()]
        return v

    # Rate Limit
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # RC4: チームの招待（D20）。期限・拒否の後の再招待の待ち・チームごとの返事待ちの上限
    TEAM_INVITATION_EXPIRY_DAYS: int = 7
    TEAM_INVITATION_REINVITE_DAYS: int = 7
    TEAM_INVITATION_MAX_PENDING: int = 30

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


# 本番で使ってはいけない値（compose の既定値・.env.example と CI の見本値）
_WEAK_DB_PASSWORDS = {"", "esports_pass", "password", "postgres", "changeme"}
_PLACEHOLDER_SECRET = re.compile(r"change|example|your[-_]|dummy|placeholder|ci-test|replace", re.IGNORECASE)


def production_problems(s: Settings) -> list[str]:
    """本番で使ってはいけない設定を、値を含まない文で返す。"""
    problems: list[str] = []
    password: str | None = s.DB_PASSWORD
    if s.DATABASE_URL:
        try:
            password = make_url(s.DATABASE_URL).password
        except (ArgumentError, ValueError):  # 解釈できない URL は未設定と同じに扱う
            password = None
    if (password or "") in _WEAK_DB_PASSWORDS:
        problems.append("DB のパスワードが未設定か既定値です")
    if _PLACEHOLDER_SECRET.search(s.SECRET_KEY):
        problems.append("SECRET_KEY が見本・テスト用の値です")
    return problems


def enforce_production_settings(s: Settings) -> None:
    """REQUIRE_STRONG_SECRETS=true のとき、本番で使ってはいけない設定なら起動を止める。"""
    if s.REQUIRE_STRONG_SECRETS and (problems := production_problems(s)):
        # 値は例外の文面に入れない（起動ログにそのまま出る）
        raise RuntimeError("本番設定の不備: " + " / ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
enforce_production_settings(settings)
