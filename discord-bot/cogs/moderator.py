"""モデレーション: warn/mute/unmute/kick + forfeit/reopen。

warn/mute/unmute/kick はDiscordネイティブ操作（Botに権限が必要）。
forfeit/reopen はバックエンド(/bot)で大会データを更新。
"""

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import my_match_autocomplete
from ui.common import brand_embed, info_embed, ok_embed
from ui.selects import ChoiceView, team_options


class ModeratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="warn", description="メンバーに警告")
    @app_commands.describe(member="対象", reason="理由")
    @requires(Role.ORGANIZER)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        try:
            await member.send(f"⚠️ **{interaction.guild.name}** で警告を受けました: {reason}")
        except discord.HTTPException:
            pass
        await interaction.response.send_message(
            embed=ok_embed("⚠️ 警告しました", f"{member.mention}: {reason}")
        )

    @app_commands.command(name="mute", description="メンバーをミュート（タイムアウト）")
    @app_commands.describe(member="対象", minutes="分", reason="理由")
    @requires(Role.ORGANIZER)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = ""):
        await member.timeout(timedelta(minutes=max(1, min(minutes, 40320))), reason=reason)
        await interaction.response.send_message(
            embed=ok_embed("🔇 ミュート", f"{member.mention} を {minutes} 分間")
        )

    @app_commands.command(name="unmute", description="ミュート解除")
    @app_commands.describe(member="対象")
    @requires(Role.ORGANIZER)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        await interaction.response.send_message(embed=ok_embed("🔊 ミュート解除", member.mention))

    @app_commands.command(name="kick-player", description="メンバーをキック")
    @app_commands.describe(member="対象", reason="理由")
    @requires(Role.ADMIN)
    async def kick_player(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""):
        await member.kick(reason=reason)
        await interaction.response.send_message(embed=ok_embed("👢 キックしました", f"{member} : {reason}"))

    @app_commands.command(name="forfeit-match", description="試合を不戦敗にする（運営）")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    @requires(Role.ORGANIZER)
    async def forfeit_match(self, interaction: discord.Interaction, match_id: str):
        m = await api_client.get_match(match_id)
        if not m:
            await interaction.response.send_message(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        opts = team_options(m)
        if len(opts) < 2:
            await interaction.response.send_message(embed=info_embed("⚠️ 対戦チーム未確定"), ephemeral=True)
            return

        async def _pick(i: discord.Interaction, winner_id: str):
            await api_client.forfeit_match(match_id, winner_id, i.user.id)
            await i.response.edit_message(embed=ok_embed("🏳️ 不戦敗を設定しました"), view=None)

        view = ChoiceView("勝ち上がるチームを選択", opts, _pick, author_id=interaction.user.id)
        await interaction.response.send_message(
            embed=brand_embed("🏳️ 不戦敗", "勝ち上がるチームを選択してください"), view=view, ephemeral=True
        )

    @app_commands.command(name="reopen-match", description="確定した試合を再オープン（運営）")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    @requires(Role.ORGANIZER)
    async def reopen_match(self, interaction: discord.Interaction, match_id: str):
        await interaction.response.defer(ephemeral=True)
        await api_client.reopen_match(match_id, interaction.user.id)
        await interaction.followup.send(embed=ok_embed("🔓 試合を再オープンしました"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModeratorCog(bot))
