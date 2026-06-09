"""プレイヤーコマンド: プロフィール/スタッツ/キャリア/レーティング/履歴/実績 + 求職フラグ。"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import player_autocomplete
from ui.common import brand_embed, info_embed, ok_embed


def _player_embed(p: dict) -> discord.Embed:
    e = brand_embed(f"🎮 {p.get('in_game_name')}", p.get("bio"))
    e.add_field(name="ゲーム", value=p.get("game", "—"), inline=True)
    if p.get("main_role"):
        e.add_field(name="ロール", value=p["main_role"], inline=True)
    if p.get("rank"):
        e.add_field(name="ランク", value=p["rank"], inline=True)
    if p.get("team_name"):
        e.add_field(name="チーム", value=p["team_name"], inline=True)
    if p.get("region"):
        e.add_field(name="地域", value=p["region"], inline=True)
    e.url = f"{config.web}/players/{p.get('id')}"
    if p.get("avatar_url"):
        e.set_thumbnail(url=p["avatar_url"])
    return e


class PlayerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="player", description="プレイヤー情報")
    @app_commands.describe(player_id="プレイヤーID")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def player(self, interaction: discord.Interaction, player_id: str):
        await self._profile(interaction, player_id)

    @app_commands.command(name="player-profile", description="プレイヤープロフィール")
    @app_commands.describe(player_id="プレイヤーID")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def player_profile(self, interaction: discord.Interaction, player_id: str):
        await self._profile(interaction, player_id)

    async def _profile(self, interaction, player_id):
        await interaction.response.defer()
        p = await api_client.get_player(player_id)
        if not p:
            await interaction.followup.send(embed=info_embed("❌ プレイヤーが見つかりません"), ephemeral=True)
            return
        await interaction.followup.send(embed=_player_embed(p))

    @app_commands.command(name="player-stats", description="プレイヤースタッツ")
    @app_commands.describe(player_id="プレイヤーID")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def player_stats(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.defer()
        c = await api_client.get_player_career(player_id)
        if not c:
            await interaction.followup.send(embed=info_embed("データがありません"), ephemeral=True)
            return
        e = brand_embed(f"📊 {c.get('in_game_name')} スタッツ")
        e.add_field(name="試合", value=str(c.get("total_matches", 0)), inline=True)
        e.add_field(name="勝率", value=f"{round((c.get('win_rate',0))*100)}%", inline=True)
        e.add_field(name="平均KDA", value=str(round(c.get("avg_kda", 0), 2)), inline=True)
        e.add_field(name="平均ACS", value=str(round(c.get("avg_acs", 0))), inline=True)
        e.add_field(name="MVP", value=str(c.get("mvp_count", 0)), inline=True)
        e.add_field(name="優勝", value=str(c.get("championships", 0)), inline=True)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="player-career", description="プレイヤーキャリア")
    @app_commands.describe(player_id="プレイヤーID")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def player_career(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.defer()
        c = await api_client.get_player_career(player_id)
        if not c:
            await interaction.followup.send(embed=info_embed("データがありません"), ephemeral=True)
            return
        e = brand_embed(f"📜 {c.get('in_game_name')} キャリア")
        e.add_field(name="出場大会", value=str(c.get("tournaments_played", 0)), inline=True)
        e.add_field(name="優勝", value=str(c.get("championships", 0)), inline=True)
        e.add_field(name="現在レート", value=str(round(c.get("current_rating") or 0)), inline=True)
        top_agents = ", ".join(a.get("agent", "") for a in (c.get("agent_usage") or [])[:3])
        if top_agents:
            e.add_field(name="主なエージェント", value=top_agents, inline=False)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="player-rating", description="プレイヤーレーティング")
    @app_commands.describe(player_id="プレイヤーID")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def player_rating(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.defer()
        c = await api_client.get_player_career(player_id)
        e = brand_embed("📈 レーティング")
        e.add_field(name="現在", value=str(round((c or {}).get("current_rating") or 0)), inline=True)
        e.add_field(name="ピーク", value=str(round((c or {}).get("peak_rating") or 0)), inline=True)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="player-history", description="レーティング推移")
    @app_commands.describe(player_id="プレイヤーID")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def player_history(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.defer()
        hist = await api_client.get_player_rating_history(player_id)
        e = brand_embed("📉 レーティング推移（直近）")
        if not hist:
            e.description = "履歴がありません。"
        else:
            e.description = "\n".join(
                f"{h.get('date','')[:10]}: {round(h.get('rating',0))} ({'+' if h.get('delta',0)>=0 else ''}{round(h.get('delta',0))})"
                for h in hist[-15:]
            )[:4000]
        await interaction.followup.send(embed=e)

    @app_commands.command(name="player-achievements", description="プレイヤー実績")
    @app_commands.describe(player_id="プレイヤーID")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def player_achievements(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.defer()
        items = await api_client.get_player_achievements(player_id)
        e = brand_embed("🏅 実績")
        e.description = "\n".join(f"🏅 **{a.get('title')}**" for a in items)[:4000] or "実績なし"
        await interaction.followup.send(embed=e)

    # ── 求職フラグ ────────────────────────────────────────────────────────────
    async def _set_looking(self, interaction, looking: bool, label: str):
        await interaction.response.defer(ephemeral=True)
        me = await api_client.resolve(interaction.user.id)
        if not me or not me.get("linked") or not me.get("player_id"):
            await interaction.followup.send(embed=info_embed("🔑 連携が必要", "`/link` でアカウント連携してください"), ephemeral=True)
            return
        await api_client.set_looking(me["player_id"], looking, interaction.user.id)
        await interaction.followup.send(embed=ok_embed(label), ephemeral=True)

    @app_commands.command(name="open-to-work", description="移籍市場に「募集中」を表示")
    @requires(Role.PLAYER)
    async def open_to_work(self, interaction: discord.Interaction):
        await self._set_looking(interaction, True, "✅ 「募集中」にしました")

    @app_commands.command(name="close-to-work", description="移籍市場の「募集中」を解除")
    @requires(Role.PLAYER)
    async def close_to_work(self, interaction: discord.Interaction):
        await self._set_looking(interaction, False, "✅ 「募集中」を解除しました")


async def setup(bot: commands.Bot):
    await bot.add_cog(PlayerCog(bot))
