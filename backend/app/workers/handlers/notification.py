import logging
from urllib.parse import urlsplit

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisCache

logger = logging.getLogger(__name__)

_DISCORD_HOSTS = {"discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com"}


def is_discord_webhook_url(url: str) -> bool:
    """送信先を Discord の Webhook に限る。

    Webhook URL は主催者が自由に入力でき、主催者ロールは誰でも名乗れる。
    検証しないと、サーバーから内部ネットワーク等の任意の宛先へ POST できてしまう（SSRF）。
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and parts.hostname in _DISCORD_HOSTS
        and parts.port in (None, 443)
        and parts.path.startswith("/api/webhooks/")
    )


async def handle_notification(
    body: dict, db: AsyncSession, cache: RedisCache
) -> None:
    channel = body.get("channel", "discord")
    if channel == "discord":
        await _send_discord(body)


async def _send_discord(body: dict) -> None:
    webhook_url = body.get("webhook_url") or settings.DISCORD_WEBHOOK_URL
    if not webhook_url:
        return
    if not is_discord_webhook_url(webhook_url):
        logger.warning("Discord webhook skipped: not a Discord webhook URL")
        return

    content = body.get("content", "")
    embed = body.get("embed")

    payload: dict = {}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed]

    if not payload:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        logger.info("Discord notification sent")
    except httpx.HTTPError as e:
        logger.error(f"Discord webhook failed: {e}")
