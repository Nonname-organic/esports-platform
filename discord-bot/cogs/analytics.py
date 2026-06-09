"""アナリティクス: マップ/エージェント(構成)/順位/リーダーボード/メタ。"""

import discord
from discord import app_commands
from discord.ext import commands

from services.api_client import api_client
from services.autocomplete import tournament_autocomplete
from ui.common import brand_embed, info_embed

GAME_CHOICES = [
    app_commands.Choice(name="VALORANT", value="VALORANT"),
    app_commands.Choice(name="CS2", value="CS2"),
    app_commands.Choice(name="LOL", value="LOL"),
    app_commands.Choice(name="APEX", value="APEX"),
    app_commands.Choice(name="OVERWATCH", value="OVERWATCH"),
]


class AnalyticsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="map-stats", description="マップ別統計")
    @app_commands.describe(game="ゲーム", tournament_id="大会ID（任意）")
    @app_commands.choices(game=GAME_CHOICES)
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def map_stats(self, interaction, game: app_commands.Choice[str], tournament_id: str | None = None):
        await interaction.response.defer()
        stats = await api_client.get_map_stats(game.value, tournament_id)
        e = brand_embed(f"🗺 マップ統計 — {game.value}")
        if not stats:
            e.description = "データなし"
        else:
            e.description = "\n".join(
                f"**{m.get('map_name')}** — {m.get('total_games')}試合 / Atk勝率 {round((m.get('attack_win_rate',0))*100)}%"
                for m in stats
            )[:4000]
        await interaction.followup.send(embed=e)

    @app_commands.command(name="agent-stats", description="構成/エージェント統計")
    @app_commands.describe(game="ゲーム", tournament_id="大会ID（任意）")
    @app_commands.choices(game=GAME_CHOICES)
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def agent_stats(self, interaction, game: app_commands.Choice[str], tournament_id: str | None = None):
        await interaction.response.defer()
        comps = await api_client.get_compositions(game.value, tournament_id=tournament_id, limit=10)
        e = brand_embed(f"🧩 構成統計 — {game.value}")
        if not comps:
            e.description = "データなし"
        else:
            e.description = "\n".join(
                f"{', '.join(c.get('composition', []))} — {c.get('games_played')}試合 勝率{round((c.get('win_rate',0))*100)}%"
                for c in comps
            )[:4000]
        await interaction.followup.send(embed=e)

    @app_commands.command(name="rankings", description="大会順位")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def rankings(self, interaction, tournament_id: str):
        await interaction.response.defer()
        rows = await api_client.get_rankings(tournament_id, limit=16)
        e = brand_embed("🏆 順位")
        if not rows:
            e.description = "順位データなし"
        else:
            lines = []
            for r in rows:
                pos = r["rank_position"]
                badge = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, f"{pos}.")
                lines.append(f"{badge} {r['team_name']} [{r['team_tag']}] — {r['points']}pt")
            e.description = "\n".join(lines)[:4000]
        await interaction.followup.send(embed=e)

    @app_commands.command(name="leaderboard", description="大会MVP/上位選手")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def leaderboard(self, interaction, tournament_id: str):
        await interaction.response.defer()
        s = await api_client.get_tournament_summary(tournament_id)
        if not s:
            await interaction.followup.send(embed=info_embed("データなし"), ephemeral=True)
            return
        e = brand_embed("⭐ リーダーボード")
        top_players = s.get("top_players_kda") or []
        if top_players:
            e.add_field(
                name="KDA上位",
                value="\n".join(f"{p.get('name') or p.get('player_name','?')}: {p.get('kda','—')}" for p in top_players[:10])[:1024],
                inline=False,
            )
        top_teams = s.get("top_teams") or []
        if top_teams:
            e.add_field(
                name="上位チーム",
                value="\n".join(f"{t.get('name','?')}" for t in top_teams[:10])[:1024],
                inline=False,
            )
        await interaction.followup.send(embed=e)

    @app_commands.command(name="meta-analysis", description="メタ分析（マップ+構成）")
    @app_commands.describe(game="ゲーム", tournament_id="大会ID（任意）")
    @app_commands.choices(game=GAME_CHOICES)
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def meta_analysis(self, interaction, game: app_commands.Choice[str], tournament_id: str | None = None):
        await interaction.response.defer()
        maps = await api_client.get_map_stats(game.value, tournament_id)
        comps = await api_client.get_compositions(game.value, tournament_id=tournament_id, limit=5)
        e = brand_embed(f"📈 メタ分析 — {game.value}")
        if maps:
            top = sorted(maps, key=lambda m: m.get("total_games", 0), reverse=True)[:5]
            e.add_field(name="人気マップ", value="\n".join(f"{m.get('map_name')} ({m.get('total_games')})" for m in top)[:1024], inline=False)
        if comps:
            e.add_field(name="強い構成", value="\n".join(f"{', '.join(c.get('composition', []))} ({round((c.get('win_rate',0))*100)}%)" for c in comps)[:1024], inline=False)
        if not maps and not comps:
            e.description = "データなし"
        await interaction.followup.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(AnalyticsCog(bot))
