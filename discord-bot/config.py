import os


class Config:
    # Discord
    BOT_TOKEN: str = os.environ.get("DISCORD_BOT_TOKEN", "")
    GUILD_ID: str = os.environ.get("DISCORD_GUILD_ID", "")  # 開発用ギルド（コマンド即時同期）

    # Platform API
    API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://api:8000")
    BOT_API_TOKEN: str = os.environ.get("BOT_API_TOKEN", "")  # Bot用サービストークン

    # Queue (SQS or Redis)
    SQS_DISCORD_QUEUE_URL: str = os.environ.get("SQS_DISCORD_QUEUE_URL", "")
    AWS_REGION: str = os.environ.get("AWS_REGION", "ap-northeast-1")
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    REDIS_QUEUE_DISCORD_KEY: str = os.environ.get("REDIS_QUEUE_DISCORD_KEY", "queue:discord_events")
    USE_REDIS_QUEUE: bool = os.environ.get("USE_REDIS_QUEUE", "true").lower() == "true"


config = Config()


# ── サーバーテンプレート定義 ───────────────────────────────────────────────────
SERVER_TEMPLATE = {
    "categories": [
        {"name": "📢 INFORMATION", "channels": ["announcements", "rules", "schedule"]},
        {"name": "🎮 TOURNAMENT", "channels": ["check-in", "general"]},
        {"name": "🏆 MATCHES", "channels": ["results"]},
        {"name": "🎙 STREAM", "channels": ["stream"]},
        {"name": "📝 SUPPORT", "channels": ["support"]},
    ],
    "archive_category": "📦 ARCHIVE",
    "roles": [
        {"name": "Admin", "color": 0xE74C3C, "permissions": "admin"},
        {"name": "Organizer", "color": 0x3498DB, "permissions": "manage"},
        {"name": "Captain", "color": 0xF1C40F, "permissions": "default"},
        {"name": "Player", "color": 0x2ECC71, "permissions": "default"},
        {"name": "Spectator", "color": 0x95A5A6, "permissions": "view"},
    ],
}
