"""チェックインコマンド: 本人/状況/一括/未チェックイン。"""

import discord
from discord import app_commands
from discord.ext import commands

from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import tournament_autocomplete
from ui.common import brand_embed, info_embed, ok_embed


class CheckInCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="check-in", description="大会にチェックイン（自分のチーム）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.PLAYER)
    async def check_in(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer(ephemeral=True)
        res = await api_client.self_check_in(tournament_id, interaction.user.id)
        await interaction.followup.send(
            embed=ok_embed("✅ チェックイン完了", f"{interaction.user.mention} のチームを登録しました"),
            ephemeral=True,
        )

    @app_commands.command(name="check-in-status", description="チェックイン状況")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def check_in_status(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        s = await api_client.check_in_status(tournament_id)
        e = brand_embed("✅ チェックイン状況")
        e.add_field(name="完了", value=str(s.get("checked_in_count", 0)), inline=True)
        e.add_field(name="未完了", value=str(s.get("missed_count", 0)), inline=True)
        e.add_field(name="合計", value=str(s.get("total", 0)), inline=True)
        if s.get("checked_in"):
            e.add_field(
                name="✅ 完了チーム",
                value="\n".join(f"{t['name']} [{t['tag']}]" for t in s["checked_in"])[:1024],
                inline=False,
            )
        await interaction.followup.send(embed=e)

    @app_commands.command(name="check-in-all", description="全チームを一括チェックイン（運営）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.ORGANIZER)
    async def check_in_all(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer(thinking=True)
        res = await api_client.check_in_all(tournament_id, interaction.user.id)
        await interaction.followup.send(
            embed=ok_embed("✅ 一括チェックイン", f"{res.get('checked_in', 0)} チームを処理しました")
        )

    @app_commands.command(name="missed-check-in", description="未チェックインのチーム一覧（運営）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.ORGANIZER)
    async def missed_check_in(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        s = await api_client.check_in_status(tournament_id)
        missed = s.get("missed", [])
        e = brand_embed("⬜ 未チェックイン", None if missed else "全チームチェックイン済みです🎉")
        if missed:
            e.description = "\n".join(f"⬜ {t['name']} [{t['tag']}]" for t in missed)[:4000]
        await interaction.followup.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(CheckInCog(bot))
