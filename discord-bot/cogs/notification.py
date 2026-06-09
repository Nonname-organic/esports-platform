"""通知コマンド: 未読通知 + 購読/設定/リマインダー(Web)。"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import Role, requires
from services.api_client import api_client
from ui.common import brand_embed, info_embed


class NotificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="unread-notifications", description="未読通知を表示")
    @requires(Role.PLAYER)
    async def unread_notifications(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = await api_client.my_notifications(interaction.user.id, unread=True, limit=10)
        if not data or not data.get("items"):
            await interaction.followup.send(embed=info_embed("📭 未読通知はありません"), ephemeral=True)
            return
        e = brand_embed(f"🔔 未読通知 ({data.get('unread_count', 0)})")
        for n in data["items"]:
            e.add_field(name=f"• {n.get('title')}", value=(n.get("body") or "")[:200] or "—", inline=False)
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="subscriptions", description="通知購読の管理（Web）")
    @requires(Role.PLAYER)
    async def subscriptions(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=info_embed("🔔 購読管理", f"{config.web}/notifications"), ephemeral=True
        )

    @app_commands.command(name="notification-settings", description="通知設定（Web）")
    @requires(Role.PLAYER)
    async def notification_settings(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=info_embed("⚙️ 通知設定", f"{config.web}/notifications"), ephemeral=True
        )

    @app_commands.command(name="reminders", description="リマインダー（Web）")
    @requires(Role.PLAYER)
    async def reminders(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=info_embed("⏰ リマインダー", f"{config.web}/notifications"), ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(NotificationCog(bot))
