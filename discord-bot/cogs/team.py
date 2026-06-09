"""チームコマンド: 情報/ロスター/履歴/スタッツ/レーティング/実績 + 編成(Web)。"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import team_autocomplete
from ui.common import brand_embed, info_embed


def _team_embed(t: dict) -> discord.Embed:
    e = brand_embed(f"🛡 {t.get('name')} [{t.get('tag')}]", t.get("description"))
    e.add_field(name="ゲーム", value=t.get("game", "—"), inline=True)
    if t.get("country"):
        e.add_field(name="地域", value=t["country"], inline=True)
    e.url = f"{config.web}/teams/{t.get('id')}"
    if t.get("logo_url"):
        e.set_thumbnail(url=t["logo_url"])
    return e


class TeamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="team", description="チーム情報を表示")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    async def team(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.defer()
        t = await api_client.get_team(team_id)
        if not t:
            await interaction.followup.send(embed=info_embed("❌ チームが見つかりません"), ephemeral=True)
            return
        await interaction.followup.send(embed=_team_embed(t))

    @app_commands.command(name="team-roster", description="ロスター（在籍メンバー）")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    async def team_roster(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.defer()
        members = await api_client.get_team_members(team_id)
        e = brand_embed("👥 ロスター")
        if not members:
            e.description = "メンバーがいません。"
        else:
            e.description = "\n".join(
                f"`{m.get('role','player')}` **{m.get('in_game_name') or m.get('username') or '?'}**"
                + (f" #{m['jersey_number']}" if m.get("jersey_number") else "")
                for m in members
            )[:4000]
        await interaction.followup.send(embed=e)

    @app_commands.command(name="team-stats", description="チームスタッツ")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    async def team_stats(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.defer()
        c = await api_client.get_team_career(team_id)
        if not c:
            await interaction.followup.send(embed=info_embed("データがありません"), ephemeral=True)
            return
        e = brand_embed(f"📊 {c.get('team_name')} スタッツ")
        e.add_field(name="戦績", value=f"{c.get('total_wins',0)}W-{c.get('total_losses',0)}L", inline=True)
        e.add_field(name="勝率", value=f"{round((c.get('win_rate',0))*100)}%", inline=True)
        e.add_field(name="優勝", value=str(c.get("championships", 0)), inline=True)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="team-history", description="チームの大会履歴")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    async def team_history(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.defer()
        c = await api_client.get_team_career(team_id)
        e = brand_embed("📜 チーム履歴")
        e.add_field(name="出場大会", value=str((c or {}).get("tournaments_played", 0)), inline=True)
        e.add_field(name="優勝", value=str((c or {}).get("championships", 0)), inline=True)
        e.url = f"{config.web}/teams/{team_id}?tab=career"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="team-rating", description="チームレーティング")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    async def team_rating(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.defer()
        c = await api_client.get_team_career(team_id)
        e = brand_embed("📈 チームレーティング")
        e.add_field(name="現在", value=str(round((c or {}).get("current_rating") or 0)), inline=True)
        e.add_field(name="ピーク", value=str(round((c or {}).get("peak_rating") or 0)), inline=True)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="team-achievements", description="チーム実績")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    async def team_achievements(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.defer()
        items = await api_client.get_team_achievements(team_id)
        e = brand_embed("🏅 チーム実績")
        e.description = "\n".join(f"🏅 **{a.get('title')}** — {a.get('description') or ''}" for a in items)[:4000] or "実績なし"
        await interaction.followup.send(embed=e)

    # ── 編成（Web。CurrentUser認証が必要なためWebで実行） ──────────────────────
    @app_commands.command(name="invite-player", description="メンバーを招待（Web）")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    @requires(Role.CAPTAIN)
    async def invite_player(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.send_message(
            embed=info_embed("➕ メンバー招待", f"{config.web}/teams/{team_id}?tab=manage"), ephemeral=True
        )

    @app_commands.command(name="remove-player", description="メンバーを除外（Web）")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    @requires(Role.CAPTAIN)
    async def remove_player(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.send_message(
            embed=info_embed("➖ メンバー除外", f"{config.web}/teams/{team_id}?tab=manage"), ephemeral=True
        )

    @app_commands.command(name="promote-player", description="ロールを変更（Web）")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    @requires(Role.CAPTAIN)
    async def promote_player(self, interaction: discord.Interaction, team_id: str):
        await interaction.response.send_message(
            embed=info_embed("⬆️ ロール変更", f"{config.web}/teams/{team_id}?tab=manage"), ephemeral=True
        )

    @app_commands.command(name="leave-team", description="チームを脱退（Web）")
    @requires(Role.PLAYER)
    async def leave_team(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=info_embed("🚪 チーム脱退", f"{config.web}/players/me"), ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TeamCog(bot))
