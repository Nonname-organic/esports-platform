"""
Esports Platform Discord Bot
- スラッシュコマンド（cogs）
- イベントコンシューマ（SQS/Redis）でプラットフォームからの指示を処理
  - setup_tournament: サーバーテンプレート生成
  - create_match_channel: 試合チャンネル生成
  - archive_match_channel: 試合チャンネルをアーカイブ
"""

import asyncio
import json
import logging

import discord
from discord.ext import commands

from config import config
from services.api_client import api_client
from services.template import build_tournament_server, create_match_channel, archive_channel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user}")
    try:
        if config.GUILD_ID:
            guild = discord.Object(id=int(config.GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"Command sync failed: {e}")

    # イベントコンシューマをバックグラウンド起動
    bot.loop.create_task(event_consumer())


# ══════════════════════════════════════════════════════════════════════════════
# イベントコンシューマ
# ══════════════════════════════════════════════════════════════════════════════
async def event_consumer():
    """SQS or Redis からプラットフォームイベントを消費"""
    await bot.wait_until_ready()
    logger.info("Event consumer started")

    if config.USE_REDIS_QUEUE:
        await _redis_consumer()
    else:
        await _sqs_consumer()


async def _redis_consumer():
    import redis.asyncio as aioredis
    r = aioredis.from_url(config.REDIS_URL)
    while not bot.is_closed():
        try:
            item = await r.blpop(config.REDIS_QUEUE_DISCORD_KEY, timeout=5)
            if item:
                _, raw = item
                await handle_event(json.loads(raw))
        except Exception as e:
            logger.error(f"Redis consumer error: {e}")
            await asyncio.sleep(3)


async def _sqs_consumer():
    import boto3
    client = boto3.client("sqs", region_name=config.AWS_REGION)
    while not bot.is_closed():
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.receive_message(
                    QueueUrl=config.SQS_DISCORD_QUEUE_URL,
                    MaxNumberOfMessages=5,
                    WaitTimeSeconds=10,
                ),
            )
            for msg in resp.get("Messages", []):
                await handle_event(json.loads(msg["Body"]))
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.delete_message(
                        QueueUrl=config.SQS_DISCORD_QUEUE_URL,
                        ReceiptHandle=msg["ReceiptHandle"],
                    ),
                )
        except Exception as e:
            logger.error(f"SQS consumer error: {e}")
            await asyncio.sleep(3)


async def handle_event(event: dict):
    event_type = event.get("event_type")
    payload = event.get("payload", {})
    logger.info(f"Handling event: {event_type}")

    guild_id = payload.get("guild_id")
    if not guild_id:
        return
    guild = bot.get_guild(int(guild_id))
    if not guild:
        logger.warning(f"Guild {guild_id} not found")
        return

    try:
        if event_type == "setup_tournament":
            result = await build_tournament_server(guild)
            await api_client.update_discord_server(payload["discord_server_id"], {
                "role_ids": result["role_ids"],
                "category_ids": result["category_ids"],
                "status": "ready",
            })
            logger.info(f"Tournament server setup complete for guild {guild_id}")

        elif event_type == "create_match_channel":
            from services.template import create_match_channel
            # MATCHES カテゴリを探す
            matches_cat = discord.utils.get(guild.categories, name="🏆 MATCHES")
            cat_id = str(matches_cat.id) if matches_cat else None
            channel_id = await create_match_channel(guild, payload["channel_name"], cat_id)
            logger.info(f"Match channel created: {channel_id}")

        elif event_type == "archive_match_channel":
            await archive_channel(guild, payload["channel_id"], payload.get("archive_category_id"))
            logger.info(f"Match channel archived: {payload['channel_id']}")

    except Exception as e:
        logger.error(f"Event handling failed ({event_type}): {e}")


async def main():
    if not config.BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN is not set. Bot will not start.")
        return
    async with bot:
        await bot.load_extension("cogs.tournament")
        await bot.load_extension("cogs.match")
        await bot.load_extension("cogs.misc")
        await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
