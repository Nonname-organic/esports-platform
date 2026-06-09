"""
Discord Service (Platform側)
- 大会作成時にDiscordセットアップイベントをキューへ送信
- OAuth連携（ユーザー↔Discord）
- Bot側はこのキューを消費してギルド操作を実行
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.redis import RedisCache
from app.models.discord import DiscordServer, DiscordChannel, DiscordLink


class DiscordEventPublisher:
    """Bot連携イベントをキューへ送信（SQS or Redis list）"""

    def __init__(self, cache: RedisCache):
        self._cache = cache

    async def publish(self, event_type: str, payload: dict) -> None:
        message = json.dumps({"event_type": event_type, "payload": payload})
        if settings.SQS_DISCORD_QUEUE_URL and not settings.USE_REDIS_QUEUE:
            await self._publish_sqs(message)
        else:
            await self._publish_redis(message)

    async def _publish_sqs(self, message: str) -> None:
        import asyncio, boto3
        loop = asyncio.get_event_loop()
        client = boto3.client("sqs", region_name=settings.AWS_REGION)
        await loop.run_in_executor(
            None,
            lambda: client.send_message(QueueUrl=settings.SQS_DISCORD_QUEUE_URL, MessageBody=message),
        )

    async def _publish_redis(self, message: str) -> None:
        try:
            redis = getattr(self._cache, "_redis", None)
            if redis:
                await redis.rpush(settings.REDIS_QUEUE_DISCORD_KEY, message)
        except Exception:
            pass


class DiscordService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache
        self._publisher = DiscordEventPublisher(cache)

    # ── 大会Discordセットアップ ──────────────────────────────────────────────
    async def setup_tournament(self, tournament_id: uuid.UUID, guild_id: str) -> DiscordServer:
        """大会用Discordサーバーのテンプレート生成をキューに依頼"""
        existing = await self._db.scalar(
            select(DiscordServer).where(DiscordServer.tournament_id == tournament_id)
        )
        if existing:
            raise BusinessRuleError("この大会のDiscordは既にセットアップ済みです")

        server = DiscordServer(
            tournament_id=tournament_id,
            guild_id=guild_id,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(server)
        await self._db.flush()

        # Bot へテンプレート生成を依頼
        await self._publisher.publish("setup_tournament", {
            "tournament_id": str(tournament_id),
            "guild_id": guild_id,
            "discord_server_id": str(server.id),
        })
        return server

    async def get_server(self, tournament_id: uuid.UUID) -> Optional[DiscordServer]:
        return await self._db.scalar(
            select(DiscordServer).where(DiscordServer.tournament_id == tournament_id)
        )

    # ── 試合チャンネル管理 ─────────────────────────────────────────────────────
    async def notify_match_start(self, match_id: uuid.UUID, tournament_id: uuid.UUID, match_number: int) -> None:
        server = await self.get_server(tournament_id)
        if not server or not server.guild_id:
            return
        await self._publisher.publish("create_match_channel", {
            "match_id": str(match_id),
            "guild_id": server.guild_id,
            "discord_server_id": str(server.id),
            "channel_name": f"match-{match_number:03d}",
        })

    async def notify_match_end(self, match_id: uuid.UUID, tournament_id: uuid.UUID) -> None:
        server = await self.get_server(tournament_id)
        if not server or not server.guild_id:
            return
        channel = await self._db.scalar(
            select(DiscordChannel).where(
                DiscordChannel.match_id == match_id,
                DiscordChannel.archived == False,
            )
        )
        if channel:
            await self._publisher.publish("archive_match_channel", {
                "guild_id": server.guild_id,
                "channel_id": channel.channel_id,
                "archive_category_id": (server.category_ids or {}).get("ARCHIVE"),
            })

    # ── Discord OAuth ───────────────────────────────────────────────────────────
    async def exchange_oauth_code(self, user_id: uuid.UUID, code: str) -> DiscordLink:
        if not (settings.DISCORD_CLIENT_ID and settings.DISCORD_CLIENT_SECRET):
            raise BusinessRuleError("Discord連携が設定されていません")

        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": settings.DISCORD_CLIENT_ID,
                    "client_secret": settings.DISCORD_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.DISCORD_REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if token_res.status_code != 200:
                raise BusinessRuleError("Discord認証に失敗しました")
            tokens = token_res.json()

            user_res = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            duser = user_res.json()

        existing = await self._db.scalar(
            select(DiscordLink).where(DiscordLink.user_id == user_id)
        )
        if existing:
            existing.discord_user_id = duser["id"]
            existing.discord_username = duser.get("username")
            existing.access_token = tokens["access_token"]
            existing.refresh_token = tokens.get("refresh_token")
            existing.linked_at = datetime.now(timezone.utc)
            await self._db.flush()
            return existing

        link = DiscordLink(
            user_id=user_id,
            discord_user_id=duser["id"],
            discord_username=duser.get("username"),
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            linked_at=datetime.now(timezone.utc),
        )
        self._db.add(link)
        await self._db.flush()
        return link

    async def get_link(self, user_id: uuid.UUID) -> Optional[DiscordLink]:
        return await self._db.scalar(
            select(DiscordLink).where(DiscordLink.user_id == user_id)
        )

    def oauth_login_url(self) -> str:
        if not settings.DISCORD_CLIENT_ID:
            return ""
        from urllib.parse import urlencode
        params = urlencode({
            "client_id": settings.DISCORD_CLIENT_ID,
            "redirect_uri": settings.DISCORD_REDIRECT_URI or "",
            "response_type": "code",
            "scope": "identify guilds",
        })
        return f"https://discord.com/api/oauth2/authorize?{params}"
