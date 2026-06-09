"""ブラケットコマンド: 表示/リンク/現在ラウンド/勝者確定/再生成。"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import my_match_autocomplete, tournament_autocomplete
from ui.common import brand_embed, info_embed, ok_embed
from ui.selects import ChoiceView, team_options


def _bracket_embed(bracket: dict) -> discord.Embed:
    e = brand_embed("🏆 トーナメントブラケット")
    for rnd, matches in sorted(bracket.get("rounds", {}).items(), key=lambda x: int(x[0])):
        lines = []
        for m in matches:
            t1 = (m.get("team1") or {}).get("name", "TBD")
            t2 = (m.get("team2") or {}).get("name", "TBD")
            mark = ""
            if m.get("winner_id"):
                wname = t1 if (m.get("team1") or {}).get("id") == m["winner_id"] else t2
                mark = f" → 🏅 {wname}"
            lines.append(f"`M{m.get('match_number')}` {t1} vs {t2}{mark}")
        e.add_field(name=f"Round {rnd}", value="\n".join(lines)[:1024] or "—", inline=False)
    return e


class BracketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bracket", description="ブラケットを表示")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def bracket(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        bracket = await api_client.get_bracket(tournament_id)
        if not bracket or not bracket.get("rounds"):
            await interaction.followup.send(embed=info_embed("❌ ブラケットがまだ生成されていません"), ephemeral=True)
            return
        await interaction.followup.send(embed=_bracket_embed(bracket))

    @app_commands.command(name="bracket-link", description="ブラケットのWebリンク")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def bracket_link(self, interaction: discord.Interaction, tournament_id: str):
        url = f"{config.web}/tournaments/{tournament_id}?tab=bracket"
        await interaction.response.send_message(embed=info_embed("🔗 ブラケット", url))

    @app_commands.command(name="bracket-image", description="ビジュアルブラケット（Web）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def bracket_image(self, interaction: discord.Interaction, tournament_id: str):
        url = f"{config.web}/tournaments/{tournament_id}?tab=bracket"
        e = info_embed("🖼 ビジュアルブラケット", f"インタラクティブ表示はこちら → {url}")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="current-round", description="現在進行中のラウンドを表示")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def current_round(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        bracket = await api_client.get_bracket(tournament_id)
        if not bracket or not bracket.get("rounds"):
            await interaction.followup.send(embed=info_embed("❌ ブラケット未生成"), ephemeral=True)
            return
        active_round, active = None, []
        for rnd, matches in sorted(bracket["rounds"].items(), key=lambda x: int(x[0])):
            pending = [m for m in matches if not m.get("winner_id")]
            if pending:
                active_round, active = rnd, pending
                break
        if active_round is None:
            await interaction.followup.send(embed=ok_embed("🏁 全試合終了", "全ラウンドが完了しています"))
            return
        e = brand_embed(f"🔴 現在: Round {active_round}")
        e.description = "\n".join(
            f"`M{m.get('match_number')}` "
            f"{(m.get('team1') or {}).get('name','TBD')} vs {(m.get('team2') or {}).get('name','TBD')}"
            for m in active
        )[:4000]
        await interaction.followup.send(embed=e)

    @app_commands.command(name="advance-match", description="勝者を確定して次へ進める（運営）")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    @requires(Role.ORGANIZER)
    async def advance_match(self, interaction: discord.Interaction, match_id: str):
        match = await api_client.get_match(match_id)
        if not match:
            await interaction.response.send_message(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        opts = team_options(match)
        if len(opts) < 2:
            await interaction.response.send_message(embed=info_embed("⚠️ 対戦チーム未確定"), ephemeral=True)
            return

        async def _pick(i: discord.Interaction, winner_id: str):
            await api_client.report_result(match_id, winner_id, i.user.id)  # 運営は即確定
            await i.response.edit_message(
                embed=ok_embed("⏭ 勝者を確定しました", "ブラケットを更新しました"), view=None
            )

        view = ChoiceView("勝者を選択", opts, _pick, author_id=interaction.user.id)
        await interaction.response.send_message(
            embed=brand_embed("⏭ 勝者の選択", "この試合の勝者を選んでください"), view=view, ephemeral=True
        )

    @app_commands.command(name="regenerate-bracket", description="ブラケットを生成/再生成（運営）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.ORGANIZER)
    async def regenerate_bracket(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer(thinking=True)
        await api_client.regenerate_bracket(tournament_id, interaction.user.id)
        bracket = await api_client.get_bracket(tournament_id)
        e = _bracket_embed(bracket) if bracket and bracket.get("rounds") else ok_embed("✅ 生成しました")
        e.title = "🔄 ブラケットを生成しました"
        await interaction.followup.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(BracketCog(bot))
