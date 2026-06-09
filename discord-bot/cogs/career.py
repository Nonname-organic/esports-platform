"""キャリアコマンド: career/history/achievements/rating-history/performance-trend。

player_id 省略時は実行者本人（DiscordLink解決）を対象にする。
"""

import discord
from discord import app_commands
from discord.ext import commands

from services.api_client import api_client
from services.autocomplete import player_autocomplete
from ui.common import brand_embed, info_embed


class CareerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _resolve_pid(self, interaction, player_id: str | None) -> str | None:
        if player_id:
            return player_id
        me = await api_client.resolve(interaction.user.id)
        if me and me.get("player_id"):
            return me["player_id"]
        return None

    @app_commands.command(name="career", description="キャリア概要（自分 or 指定選手）")
    @app_commands.describe(player_id="プレイヤーID（省略で自分）")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def career(self, interaction, player_id: str | None = None):
        await interaction.response.defer()
        pid = await self._resolve_pid(interaction, player_id)
        if not pid:
            await interaction.followup.send(embed=info_embed("🔑 連携が必要", "`/link` で連携、または player_id を指定"), ephemeral=True)
            return
        c = await api_client.get_player_career(pid)
        if not c:
            await interaction.followup.send(embed=info_embed("データがありません"), ephemeral=True)
            return
        e = brand_embed(f"📜 {c.get('in_game_name')} のキャリア")
        e.add_field(name="試合", value=str(c.get("total_matches", 0)), inline=True)
        e.add_field(name="勝率", value=f"{round((c.get('win_rate',0))*100)}%", inline=True)
        e.add_field(name="優勝", value=str(c.get("championships", 0)), inline=True)
        e.add_field(name="MVP", value=str(c.get("mvp_count", 0)), inline=True)
        e.add_field(name="出場大会", value=str(c.get("tournaments_played", 0)), inline=True)
        e.add_field(name="現在レート", value=str(round(c.get("current_rating") or 0)), inline=True)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="history", description="大会出場履歴")
    @app_commands.describe(player_id="プレイヤーID（省略で自分）")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def history(self, interaction, player_id: str | None = None):
        await interaction.response.defer()
        pid = await self._resolve_pid(interaction, player_id)
        if not pid:
            await interaction.followup.send(embed=info_embed("🔑 連携が必要"), ephemeral=True)
            return
        c = await api_client.get_player_career(pid)
        e = brand_embed("📚 履歴")
        e.add_field(name="出場大会", value=str((c or {}).get("tournaments_played", 0)), inline=True)
        e.add_field(name="優勝", value=str((c or {}).get("championships", 0)), inline=True)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="achievements", description="獲得実績")
    @app_commands.describe(player_id="プレイヤーID（省略で自分）")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def achievements(self, interaction, player_id: str | None = None):
        await interaction.response.defer()
        pid = await self._resolve_pid(interaction, player_id)
        if not pid:
            await interaction.followup.send(embed=info_embed("🔑 連携が必要"), ephemeral=True)
            return
        items = await api_client.get_player_achievements(pid)
        e = brand_embed("🏅 実績")
        e.description = "\n".join(f"🏅 **{a.get('title')}** — {a.get('description') or ''}" for a in items)[:4000] or "実績なし"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="rating-history", description="レーティング推移")
    @app_commands.describe(player_id="プレイヤーID（省略で自分）")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def rating_history(self, interaction, player_id: str | None = None):
        await interaction.response.defer()
        pid = await self._resolve_pid(interaction, player_id)
        if not pid:
            await interaction.followup.send(embed=info_embed("🔑 連携が必要"), ephemeral=True)
            return
        hist = await api_client.get_player_rating_history(pid)
        e = brand_embed("📉 レーティング推移")
        e.description = "\n".join(
            f"{h.get('date','')[:10]}: {round(h.get('rating',0))}" for h in hist[-15:]
        )[:4000] or "履歴なし"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="performance-trend", description="直近パフォーマンス傾向")
    @app_commands.describe(player_id="プレイヤーID（省略で自分）")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def performance_trend(self, interaction, player_id: str | None = None):
        await interaction.response.defer()
        pid = await self._resolve_pid(interaction, player_id)
        if not pid:
            await interaction.followup.send(embed=info_embed("🔑 連携が必要"), ephemeral=True)
            return
        hist = await api_client.get_player_rating_history(pid)
        e = brand_embed("📈 パフォーマンス傾向")
        if len(hist) >= 2:
            delta = round(hist[-1].get("rating", 0) - hist[0].get("rating", 0))
            arrow = "⬆️ 上昇傾向" if delta > 0 else ("⬇️ 下降傾向" if delta < 0 else "➡️ 横ばい")
            e.description = f"直近 {len(hist)} 記録: {arrow}（{'+' if delta>=0 else ''}{delta}）"
        else:
            e.description = "傾向を出すにはデータが不足しています。"
        await interaction.followup.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(CareerCog(bot))
