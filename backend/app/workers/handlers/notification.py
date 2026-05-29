import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisCache

logger = logging.getLogger(__name__)


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
