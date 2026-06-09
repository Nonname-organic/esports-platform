"""配信コマンド: stream/live/watch/stream-info。"""

import discord
from discord import app_commands
from discord.ext import commands

from services.api_client import api_client
from services.autocomplete import my_match_autocomplete, tournament_autocomplete
from ui.common import brand_embed, info_embed


class StreamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _stream_of(self, interaction, match_id: str, with_vod=False):
        await interaction.response.defer()
        m = await api_client.get_match(match_id)
        if not m:
            await interaction.followup.send(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        url = m.get("stream_url")
        if not url:
            await interaction.followup.send(embed=info_embed("📴 配信URLが未設定です"), ephemeral=True)
            return
        e = brand_embed("🔴 配信", url)
        if with_vod and m.get("vod_url"):
            e.add_field(name="VOD", value=m["vod_url"], inline=False)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="stream", description="試合の配信リンク")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    async def stream(self, interaction, match_id: str):
        await self._stream_of(interaction, match_id)

    @app_commands.command(name="watch", description="試合を視聴（配信リンク）")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    async def watch(self, interaction, match_id: str):
        await self._stream_of(interaction, match_id)

    @app_commands.command(name="stream-info", description="配信+VOD情報")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    async def stream_info(self, interaction, match_id: str):
        await self._stream_of(interaction, match_id, with_vod=True)

    @app_commands.command(name="live", description="Stream Hub: 進行中の試合と配信リンク")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def live(self, interaction, tournament_id: str):
        await interaction.response.defer()
        bracket = await api_client.get_bracket(tournament_id)
        e = brand_embed("📺 Stream Hub — LIVE")
        live_matches = [
            m for matches in (bracket or {}).get("rounds", {}).values()
            for m in matches if m.get("status") == "ongoing"
        ]
        if not live_matches:
            e.description = "進行中の試合はありません。"
            await interaction.followup.send(embed=e)
            return
        # 各試合の配信URLを取得（最大8件）
        for m in live_matches[:8]:
            detail = await api_client.get_match(m["id"])
            t1 = (m.get("team1") or {}).get("name", "TBD")
            t2 = (m.get("team2") or {}).get("name", "TBD")
            url = (detail or {}).get("stream_url")
            value = f"🔴 [配信を見る]({url})" if url else "配信URL未設定"
            e.add_field(name=f"M{m.get('match_number')}: {t1} vs {t2}", value=value, inline=False)
        await interaction.followup.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(StreamCog(bot))
