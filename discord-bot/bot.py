"""
Discord Tournament Operating System — Bot エントリポイント

- スラッシュコマンド（cogs: 全カテゴリ）
- RBAC（core/rbac）+ グローバルエラーハンドラ（core/errors）
- コマンドメトリクス/エラーログ（core/monitoring → /api/v1/bot/*）
- イベントコンシューマ（SQS/Redis）で自動チャンネル生成/Archive
  - setup_tournament / create_match_channel / archive_match_channel
"""

import asyncio
import json
import logging
import traceback

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.errors import to_user_embed
from core.monitoring import Metrics
from services.api_client import api_client
from services.template import archive_channel, build_tournament_server, create_match_channel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
metrics = Metrics(api_client)

COGS = [
    "cogs.account",
    "cogs.tournament", "cogs.bracket", "cogs.checkin", "cogs.match", "cogs.veto",
    "cogs.team", "cogs.player", "cogs.scout", "cogs.analytics", "cogs.career",
    "cogs.notification", "cogs.stream", "cogs.moderator", "cogs.support", "cogs.help",
]


# ══════════════════════════════════════════════════════════════════════════════
# lifecycle
# ══════════════════════════════════════════════════════════════════════════════
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

    bot.loop.create_task(event_consumer())
    bot.loop.create_task(metrics_flusher())


async def metrics_flusher():
    """コマンドメトリクスを定期フラッシュ。"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(30)
        await metrics.flush()


# ── メトリクス & エラーハンドリング ───────────────────────────────────────────
@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: app_commands.Command):
    metrics.record(interaction, command.qualified_name, success=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    err = getattr(error, "original", error)
    cmd = interaction.command.qualified_name if interaction.command else None

    # ユーザーへ整形メッセージ
    embed = to_user_embed(err)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException:
        pass

    # メトリクス + エラーログ
    metrics.record(interaction, cmd or "unknown", success=False, error_type=type(err).__name__)
    # 想定内（権限/業務）は詳細ログ不要。想定外のみtraceback保存。
    from core.errors import ApiError
    from core.rbac import MissingRole
    if not isinstance(err, (ApiError, MissingRole, app_commands.CheckFailure, app_commands.CommandOnCooldown)):
        tb = "".join(traceback.format_exception(type(err), err, err.__traceback__))
        logger.error("Command error in %s: %s", cmd, tb)
        await metrics.log_error(interaction, cmd, type(err).__name__, str(err), tb)


# ══════════════════════════════════════════════════════════════════════════════
# イベントコンシューマ（自動化）
# ══════════════════════════════════════════════════════════════════════════════
async def event_consumer():
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


async def _dm_user(payload: dict):
    """連携ユーザーへDM通知（guild不要）。"""
    did = payload.get("discord_user_id")
    if not did:
        return
    try:
        user = bot.get_user(int(did)) or await bot.fetch_user(int(did))
        if not user:
            return
        e = discord.Embed(
            title=f"🔔 {payload.get('title', '通知')}",
            description=payload.get("body") or None,
            color=config.BRAND_COLOR,
        )
        url = payload.get("action_url")
        if url:
            e.add_field(name="リンク", value=f"{config.web}{url}" if url.startswith('/') else url, inline=False)
        await user.send(embed=e)
    except discord.HTTPException:
        pass  # DM拒否設定などは無視


async def handle_event(event: dict):
    event_type = event.get("event_type")
    payload = event.get("payload", {})
    logger.info(f"Handling event: {event_type}")

    # DM系イベントはguild不要
    if event_type == "notify_user":
        await _dm_user(payload)
        return

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
            matches_cat = discord.utils.get(guild.categories, name="🏆 MATCHES")
            cat_id = str(matches_cat.id) if matches_cat else None
            channel_id = await create_match_channel(guild, payload["channel_name"], cat_id)
            logger.info(f"Match channel created: {channel_id}")
            # チャンネルを記録（Archive対象特定用）
            if channel_id and payload.get("discord_server_id") and payload.get("match_id"):
                await api_client.record_match_channel(
                    payload["discord_server_id"], payload["match_id"],
                    channel_id, payload.get("channel_name"),
                )
            # 自動: 試合チャンネルに操作ガイドを掲示
            ch = guild.get_channel(int(channel_id)) if channel_id else None
            if isinstance(ch, discord.TextChannel):
                e = discord.Embed(
                    title="⚔️ 試合チャンネル開設",
                    description=(
                        "進行に使うコマンド:\n"
                        "• `/ban-map` `/pick-map` `/confirm-veto` — マップveto\n"
                        "• `/report-result` — 結果報告（相手が `確認` で確定）\n"
                        "• `/dispute-result` — 異議申し立て\n"
                        "• `/upload-screenshot` — スクショ提出"
                    ),
                    color=config.BRAND_COLOR,
                )
                await ch.send(embed=e)

        elif event_type == "archive_match_channel":
            await archive_channel(guild, payload["channel_id"], payload.get("archive_category_id"))
            logger.info(f"Match channel archived: {payload['channel_id']}")

    except Exception as e:
        logger.error(f"Event handling failed ({event_type}): {e}")


# ══════════════════════════════════════════════════════════════════════════════
async def main():
    if not config.BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN is not set. Bot will not start.")
        return
    async with bot:
        for ext in COGS:
            await bot.load_extension(ext)
        await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
