"""スカウトコマンド: 推薦/検索/募集 + 投稿・応募(Web)。"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import player_autocomplete, team_autocomplete
from ui.common import brand_embed, info_embed


class ScoutCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="search-player", description="プレイヤーを検索")
    @app_commands.describe(game="ゲーム", role="ロール", looking_only="募集中のみ")
    async def search_player(self, interaction, game: str | None = None, role: str | None = None, looking_only: bool = False):
        await interaction.response.defer()
        players = await api_client.scout_players(game=game, role=role, looking_only=looking_only, limit=15)
        e = brand_embed("🔍 プレイヤー検索")
        if not players:
            e.description = "該当なし"
        else:
            e.description = "\n".join(
                f"**{p.get('in_game_name')}** ({p.get('game')}/{p.get('main_role') or '—'}) "
                f"勝率{round((p.get('win_rate',0))*100)}% {'🟢募集中' if p.get('is_looking') else ''}"
                for p in players
            )[:4000]
        await interaction.followup.send(embed=e)

    @app_commands.command(name="search-team", description="チームを検索")
    @app_commands.describe(game="ゲーム", recruiting_only="募集中のみ")
    async def search_team(self, interaction, game: str | None = None, recruiting_only: bool = False):
        await interaction.response.defer()
        teams = await api_client.scout_teams(game=game, recruiting_only=recruiting_only, limit=15)
        e = brand_embed("🔍 チーム検索")
        e.description = "\n".join(
            f"**{t.get('name')}** [{t.get('tag')}] 勝率{round((t.get('win_rate',0))*100)}% "
            f"{'🟢募集中' if t.get('is_recruiting') else ''}"
            for t in teams
        )[:4000] or "該当なし"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="player-availability", description="募集中のプレイヤー一覧")
    @app_commands.describe(game="ゲーム")
    async def player_availability(self, interaction, game: str | None = None):
        await interaction.response.defer()
        players = await api_client.scout_players(game=game, looking_only=True, limit=20)
        e = brand_embed("🟢 募集中プレイヤー")
        e.description = "\n".join(
            f"**{p.get('in_game_name')}** ({p.get('main_role') or '—'}) {p.get('availability') or ''}"
            for p in players
        )[:4000] or "現在募集中のプレイヤーはいません"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="team-recruitment", description="募集投稿一覧")
    @app_commands.describe(game="ゲーム")
    async def team_recruitment(self, interaction, game: str | None = None):
        await interaction.response.defer()
        posts = await api_client.list_recruitment(game=game, limit=15)
        e = brand_embed("📋 募集投稿")
        e.description = "\n".join(
            f"**{p.get('title')}** ({p.get('post_type')}) — 応募{p.get('application_count',0)}"
            for p in posts
        )[:4000] or "募集はありません"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="recommend-players", description="チームへのおすすめ選手")
    @app_commands.describe(team_id="チームID")
    @app_commands.autocomplete(team_id=team_autocomplete)
    async def recommend_players(self, interaction, team_id: str):
        await interaction.response.defer()
        recs = await api_client.recommend_players(team_id, limit=10)
        e = brand_embed("🎯 おすすめ選手")
        e.description = "\n".join(
            f"**{r.get('name')}** — マッチ度 {round((r.get('score',0))*100)}% — {r.get('summary','')}"
            for r in recs
        )[:4000] or "推薦なし"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="recommend-teams", description="選手へのおすすめチーム")
    @app_commands.describe(player_id="プレイヤーID")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def recommend_teams(self, interaction, player_id: str):
        await interaction.response.defer()
        recs = await api_client.recommend_teams(player_id, limit=10)
        e = brand_embed("🎯 おすすめチーム")
        e.description = "\n".join(
            f"**{r.get('name')}** — マッチ度 {round((r.get('score',0))*100)}% — {r.get('summary','')}"
            for r in recs
        )[:4000] or "推薦なし"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="post-recruitment", description="募集を投稿（Web）")
    @requires(Role.PLAYER)
    async def post_recruitment(self, interaction):
        await interaction.response.send_message(
            embed=info_embed("📝 募集投稿", f"{config.web}/scout/recruitment"), ephemeral=True
        )

    @app_commands.command(name="apply-recruitment", description="募集に応募（Web）")
    @requires(Role.PLAYER)
    async def apply_recruitment(self, interaction):
        await interaction.response.send_message(
            embed=info_embed("✉️ 応募", f"{config.web}/scout/recruitment"), ephemeral=True
        )

    @app_commands.command(name="invite-candidate", description="候補者を招待（Web）")
    @requires(Role.CAPTAIN)
    async def invite_candidate(self, interaction):
        await interaction.response.send_message(
            embed=info_embed("📨 候補者招待", f"{config.web}/scout/players"), ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ScoutCog(bot))
