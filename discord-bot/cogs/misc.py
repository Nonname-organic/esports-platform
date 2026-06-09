"""チェックイン・チーム・プレイヤー・ヘルプコマンド"""

import discord
from discord import app_commands
from discord.ext import commands

from services.api_client import api_client


class CheckInCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="check-in", description="大会にチェックインします")
    @app_commands.describe(tournament_id="大会ID")
    async def check_in(self, interaction: discord.Interaction, tournament_id: str):
        # プラットフォームのcheck-in APIを呼ぶ（将来実装）
        embed = discord.Embed(
            title="✅ チェックイン完了",
            description=f"{interaction.user.mention} がチェックインしました",
            color=0x2ECC71,
        )
        await interaction.response.send_message(embed=embed)


class TeamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="team", description="チーム情報を表示します")
    @app_commands.describe(team_id="チームID")
    async def team(self, interaction: discord.Interaction, team_id: str):
        base = api_client._base.replace("http://api:8000", "")
        await interaction.response.send_message(f"🔗 チーム: {base}/teams/{team_id}")


class PlayerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="player", description="プレイヤー情報を表示します")
    @app_commands.describe(player_id="プレイヤーID")
    async def player(self, interaction: discord.Interaction, player_id: str):
        base = api_client._base.replace("http://api:8000", "")
        await interaction.response.send_message(f"🔗 プレイヤー: {base}/players/{player_id}")


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="利用可能なコマンド一覧")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🤖 Esports Platform Bot", color=0x3498DB)
        embed.description = "大会運営を自動化するコマンド一覧"
        commands_list = [
            ("/create-tournament", "サーバーを大会用にセットアップ"),
            ("/bracket", "ブラケットを表示"),
            ("/check-in", "大会にチェックイン"),
            ("/report-result", "試合結果を報告"),
            ("/match", "試合情報を表示"),
            ("/team", "チーム情報を表示"),
            ("/player", "プレイヤー情報を表示"),
            ("/help", "このヘルプを表示"),
        ]
        for name, desc in commands_list:
            embed.add_field(name=name, value=desc, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CheckInCog(bot))
    await bot.add_cog(TeamCog(bot))
    await bot.add_cog(PlayerCog(bot))
    await bot.add_cog(HelpCog(bot))
