"""チェックイン・チーム・プレイヤー・ヘルプコマンド"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from services.api_client import api_client


class CheckInCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="check-in", description="大会のチェックイン状況を確認します")
    @app_commands.describe(tournament_id="大会ID")
    async def check_in(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer(ephemeral=True)
        tournament = await api_client.get_tournament(tournament_id)
        if not tournament:
            await interaction.followup.send("❌ 大会が見つかりません", ephemeral=True)
            return

        url = f"{config.PUBLIC_WEB_URL}/tournaments/{tournament_id}"
        if not tournament.get("require_check_in"):
            embed = discord.Embed(
                title="ℹ️ チェックイン不要",
                description=f"**{tournament['name']}** はチェックイン不要の大会です。",
                color=0x95A5A6,
            )
        else:
            embed = discord.Embed(
                title="✅ チェックイン",
                description=f"**{tournament['name']}** のチェックインはプラットフォーム上で行ってください。",
                color=0x2ECC71,
            )
            if tournament.get("check_in_start_at"):
                embed.add_field(
                    name="チェックイン開始", value=tournament["check_in_start_at"], inline=False
                )
        embed.add_field(name="🔗 チェックインページ", value=url, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)


class TeamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="team", description="チーム情報を表示します")
    @app_commands.describe(team_id="チームID")
    async def team(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.send_message(
            f"🔗 チーム: {config.PUBLIC_WEB_URL}/teams/{team_id}"
        )


class PlayerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="player", description="プレイヤー情報を表示します")
    @app_commands.describe(player_id="プレイヤーID")
    async def player(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.send_message(
            f"🔗 プレイヤー: {config.PUBLIC_WEB_URL}/players/{player_id}"
        )


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
