"""アカウント連携: /link /unlink /whoami。

コード方式: Webで `/discord-link`（連携コード発行）→ Discordで `/link code:XXXX`。
連携成功時、プラットフォームのroleに対応するDiscordロールを自動付与（S2の一部）。
"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from services.api_client import api_client
from ui.common import brand_embed, info_embed, ok_embed

# プラットフォームrole → Discordロール名
ROLE_TO_DISCORD = {
    "admin": "Admin",
    "organizer": "Organizer",
    "team_manager": "Organizer",
    "player": "Player",
    "viewer": "Spectator",
}


async def _assign_role(interaction: discord.Interaction, platform_role: str) -> str | None:
    """platform_role に対応するDiscordロールを付与。付与できたロール名を返す。"""
    if not isinstance(interaction.user, discord.Member) or not interaction.guild:
        return None
    role_name = ROLE_TO_DISCORD.get(platform_role)
    if not role_name:
        return None
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if not role:
        return None
    try:
        await interaction.user.add_roles(role, reason="Platform link role sync")
        return role_name
    except discord.HTTPException:
        return None


class AccountCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="link", description="Discordとプラットフォームアカウントを連携")
    @app_commands.describe(code="Webで発行した連携コード（省略で連携状況を表示）")
    async def link(self, interaction: discord.Interaction, code: str | None = None):
        await interaction.response.defer(ephemeral=True)

        if not code:
            me = await api_client.resolve(interaction.user.id)
            if me and me.get("linked"):
                e = ok_embed("✅ 連携済み", f"ロール: **{me.get('role')}**")
                if me.get("teams"):
                    e.add_field(name="所属チーム", value=", ".join(t["name"] for t in me["teams"]) or "—", inline=False)
            else:
                e = info_embed(
                    "🔗 アカウント未連携",
                    f"1) Web `{config.web}/discord-link` で**連携コード**を発行\n"
                    f"2) `/link code:発行されたコード` を実行",
                )
            await interaction.followup.send(embed=e, ephemeral=True)
            return

        res = await api_client.link(code.strip().upper(), interaction.user.id, interaction.user.name)
        role_assigned = await _assign_role(interaction, (res or {}).get("role", ""))
        e = ok_embed("✅ 連携しました", "操作系コマンド（check-in / report-result 等）が使えるようになりました。")
        if role_assigned:
            e.add_field(name="付与ロール", value=role_assigned, inline=True)
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="unlink", description="アカウント連携を解除")
    async def unlink(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await api_client.unlink(interaction.user.id)
        await interaction.followup.send(embed=ok_embed("🔓 連携を解除しました"), ephemeral=True)

    @app_commands.command(name="whoami", description="連携中のアカウント情報を表示")
    async def whoami(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        me = await api_client.resolve(interaction.user.id)
        if not me or not me.get("linked"):
            await interaction.followup.send(
                embed=info_embed("未連携", "`/link` で連携してください"), ephemeral=True
            )
            return
        e = brand_embed("👤 アカウント情報")
        e.add_field(name="ロール", value=me.get("role", "—"), inline=True)
        e.add_field(name="選手", value=me.get("in_game_name") or "—", inline=True)
        if me.get("teams"):
            e.add_field(
                name="所属チーム",
                value="\n".join(f"{t['name']} [{t['tag']}] ({t['role']})" for t in me["teams"])[:1024],
                inline=False,
            )
        await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AccountCog(bot))
