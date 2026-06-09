import os


class Config:
    # Discord
    BOT_TOKEN: str = os.environ.get("DISCORD_BOT_TOKEN", "")
    GUILD_ID: str = os.environ.get("DISCORD_GUILD_ID", "")  # 開発用ギルド（コマンド即時同期）

    # Platform API
    API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://api:8000")
    BOT_API_TOKEN: str = os.environ.get("BOT_API_TOKEN", "")  # Bot用サービストークン
    # 公開Web URL（埋め込みリンク用。API_BASE_URLは内部DNSなのでリンクには使えない）
    PUBLIC_WEB_URL: str = os.environ.get(
        "PUBLIC_WEB_URL", "https://d3r8lgt0kvo61v.cloudfront.net"
    ).rstrip("/")

    # Queue (SQS or Redis)
    SQS_DISCORD_QUEUE_URL: str = os.environ.get("SQS_DISCORD_QUEUE_URL", "")
    AWS_REGION: str = os.environ.get("AWS_REGION", "ap-northeast-1")
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    REDIS_QUEUE_DISCORD_KEY: str = os.environ.get("REDIS_QUEUE_DISCORD_KEY", "queue:discord_events")
    USE_REDIS_QUEUE: bool = os.environ.get("USE_REDIS_QUEUE", "true").lower() == "true"

    # Embedの基調色
    BRAND_COLOR: int = 0x3498DB

    @property
    def web(self) -> str:
        return self.PUBLIC_WEB_URL


config = Config()


# ── Map veto カタログ（VALORANT / CS2） ───────────────────────────────────────
# autocomplete / select / veto進行で使用。
MAP_POOLS = {
    "VALORANT": ["Ascent", "Bind", "Haven", "Split", "Lotus", "Sunset", "Icebox", "Breeze", "Pearl", "Abyss"],
    "CS2": ["Mirage", "Inferno", "Nuke", "Overpass", "Vertigo", "Ancient", "Anubis", "Dust2", "Train"],
}


# ── ロール表示ラベル ──────────────────────────────────────────────────────────
ROLE_LABELS = {
    "admin": "Admin",
    "organizer": "Organizer",
    "captain": "Captain",
    "player": "Player",
    "spectator": "Spectator",
}


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
