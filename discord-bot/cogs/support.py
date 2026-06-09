"""サポート: support/contact-admin/report-player/report-team。"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import Role, requires
from services.autocomplete import team_autocomplete
from ui.common import brand_embed, info_embed, ok_embed


def _organizer_mention(guild: discord.Guild) -> str:
    if guild:
        for name in ("Organizer", "Admin"):
            role = discord.utils.get(guild.roles, name=name)
            if role:
                return role.mention
    return "@運営"


class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="support", description="サポート情報")
    async def support(self, interaction: discord.Interaction):
        e = brand_embed(
            "🆘 サポート",
            "困ったら `#support` チャンネルへ、または `/contact-admin` で運営に連絡できます。",
        )
        e.add_field(name="ヘルプ", value="`/help` でコマンド一覧", inline=False)
        e.add_field(name="Web", value=config.web, inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="contact-admin", description="運営に連絡")
    @app_commands.describe(message="連絡内容")
    @requires(Role.PLAYER)
    async def contact_admin(self, interaction: discord.Interaction, message: str):
        e = brand_embed("📨 運営への連絡", message)
        e.set_footer(text=f"from {interaction.user.display_name}")
        await interaction.channel.send(content=_organizer_mention(interaction.guild), embed=e)
        await interaction.response.send_message(embed=ok_embed("✅ 運営に送信しました"), ephemeral=True)

    @app_commands.command(name="report-player", description="プレイヤーを通報")
    @app_commands.describe(member="対象", reason="理由")
    @requires(Role.PLAYER)
    async def report_player(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        e = brand_embed("🚩 プレイヤー通報", f"対象: {member.mention}\n理由: {reason}")
        e.set_footer(text=f"通報者: {interaction.user.display_name}")
        await interaction.channel.send(content=_organizer_mention(interaction.guild), embed=e)
        await interaction.response.send_message(embed=ok_embed("✅ 通報を受け付けました"), ephemeral=True)

    @app_commands.command(name="report-team", description="チームを通報")
    @app_commands.describe(team_id="チームID", reason="理由")
    @app_commands.autocomplete(team_id=team_autocomplete)
    @requires(Role.PLAYER)
    async def report_team(self, interaction: discord.Interaction, team_id: str, reason: str):
        e = brand_embed("🚩 チーム通報", f"対象チーム: `{team_id}`\n理由: {reason}")
        e.set_footer(text=f"通報者: {interaction.user.display_name}")
        await interaction.channel.send(content=_organizer_mention(interaction.guild), embed=e)
        await interaction.response.send_message(embed=ok_embed("✅ 通報を受け付けました"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
