"""トーナメント関連コマンド"""

import discord
from discord import app_commands
from discord.ext import commands

from services.api_client import api_client
from services.template import build_tournament_server


class TournamentCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="create-tournament", description="このサーバーを大会用にセットアップします")
    @app_commands.describe(tournament_id="プラットフォームの大会ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_tournament(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer(thinking=True)
        tournament = await api_client.get_tournament(tournament_id)
        if not tournament:
            await interaction.followup.send("❌ 大会が見つかりません", ephemeral=True)
            return

        result = await build_tournament_server(interaction.guild)

        embed = discord.Embed(
            title=f"🏆 {tournament['name']}",
            description="サーバーのセットアップが完了しました！",
            color=0x3498DB,
        )
        embed.add_field(name="ゲーム", value=tournament["game"], inline=True)
        embed.add_field(name="形式", value=tournament["format"], inline=True)
        embed.add_field(name="生成ロール", value=str(len(result["role_ids"])), inline=True)
        embed.add_field(name="生成カテゴリ", value=str(len(result["category_ids"])), inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="bracket", description="現在のブラケットを表示")
    @app_commands.describe(tournament_id="大会ID")
    async def bracket(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        bracket = await api_client.get_bracket(tournament_id)
        if not bracket:
            await interaction.followup.send("❌ ブラケットがまだ生成されていません", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 トーナメントブラケット", color=0x3498DB)
        for round_num, matches in sorted(bracket.get("rounds", {}).items()):
            lines = []
            for m in matches:
                t1 = m["team1"]["name"] if m.get("team1") else "TBD"
                t2 = m["team2"]["name"] if m.get("team2") else "TBD"
                lines.append(f"`M{m['match_number']}` {t1} vs {t2}")
            embed.add_field(name=f"Round {round_num}", value="\n".join(lines) or "—", inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TournamentCog(bot))
