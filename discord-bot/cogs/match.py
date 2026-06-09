"""試合関連コマンド"""

import discord
from discord import app_commands
from discord.ext import commands

from services.api_client import api_client


class MatchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="report-result", description="試合結果を報告します")
    @app_commands.describe(match_id="試合ID", winner_team_id="勝者チームID")
    async def report_result(self, interaction: discord.Interaction, match_id: str, winner_team_id: str):
        await interaction.response.defer()
        ok = await api_client.report_result(match_id, winner_team_id)
        if ok:
            embed = discord.Embed(
                title="✅ 結果を報告しました",
                description=f"Match `{match_id[:8]}` の勝者を登録しました",
                color=0x2ECC71,
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 結果の報告に失敗しました", ephemeral=True)

    @app_commands.command(name="match", description="試合情報を表示します")
    @app_commands.describe(match_id="試合ID")
    async def match(self, interaction: discord.Interaction, match_id: str):
        await interaction.response.send_message(
            f"🔗 試合詳細: {api_client._base.replace('http://api:8000', '')}/matches/{match_id}",
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MatchCog(bot))
