"""大会コマンド: 作成/編集/開始/終了/中止 + 情報/ルール/日程/順位/参加者。"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import tournament_autocomplete
from services.template import build_tournament_server
from ui.common import ConfirmView, brand_embed, info_embed, ok_embed

STATUS_EMOJI = {
    "draft": "📝", "registration_open": "📢", "registration_closed": "🔒",
    "check_in": "✅", "ongoing": "🔴", "completed": "🏁", "cancelled": "🛑",
}


def _tournament_embed(t: dict) -> discord.Embed:
    e = brand_embed(f"{STATUS_EMOJI.get(t.get('status'), '🏆')} {t.get('name')}", t.get("description"))
    e.add_field(name="ゲーム", value=t.get("game", "—"), inline=True)
    e.add_field(name="形式", value=t.get("format", "—"), inline=True)
    e.add_field(name="状態", value=t.get("status", "—"), inline=True)
    e.add_field(name="参加", value=f"{t.get('registered_teams', 0)}/{t.get('max_teams', '—')}", inline=True)
    if t.get("start_at"):
        e.add_field(name="開始", value=str(t["start_at"])[:16], inline=True)
    if t.get("prize_pool"):
        e.add_field(name="賞金", value=f"¥{t['prize_pool']}", inline=True)
    e.url = f"{config.web}/tournaments/{t.get('id')}"
    if t.get("banner_url"):
        e.set_image(url=t["banner_url"])
    return e


class TournamentCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── 運営: ライフサイクル ────────────────────────────────────────────────
    @app_commands.command(name="create-tournament", description="このサーバーを大会用にセットアップ")
    @app_commands.describe(tournament_id="プラットフォームの大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.ORGANIZER)
    async def create_tournament(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer(thinking=True)
        t = await api_client.get_tournament(tournament_id)
        if not t:
            await interaction.followup.send(embed=info_embed("❌ 大会が見つかりません"), ephemeral=True)
            return
        result = await build_tournament_server(interaction.guild)
        e = _tournament_embed(t)
        e.title = f"🏆 {t.get('name')} セットアップ完了"
        e.add_field(name="生成ロール", value=str(len(result["role_ids"])), inline=True)
        e.add_field(name="生成カテゴリ", value=str(len(result["category_ids"])), inline=True)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="edit-tournament", description="大会情報を編集（Web）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.ORGANIZER)
    async def edit_tournament(self, interaction: discord.Interaction, tournament_id: str):
        url = f"{config.web}/tournaments/{tournament_id}/edit"
        await interaction.response.send_message(
            embed=info_embed("✏️ 大会編集", f"編集はこちら → {url}"), ephemeral=True
        )

    @app_commands.command(name="start-tournament", description="大会を開始（→ongoing）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.ORGANIZER)
    async def start_tournament(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer(thinking=True)
        t = await api_client.change_tournament_status(tournament_id, "start", interaction.user.id)
        await interaction.followup.send(embed=ok_embed("▶️ 大会を開始しました", f"**{t['name']}** → {t['status']}"))

    @app_commands.command(name="end-tournament", description="大会を終了（→completed）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.ORGANIZER)
    async def end_tournament(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer(thinking=True)
        t = await api_client.change_tournament_status(tournament_id, "end", interaction.user.id)
        await interaction.followup.send(embed=ok_embed("🏁 大会を終了しました", f"**{t['name']}** → {t['status']}"))

    @app_commands.command(name="cancel-tournament", description="大会を中止（→cancelled）")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    @requires(Role.ORGANIZER)
    async def cancel_tournament(self, interaction: discord.Interaction, tournament_id: str):
        view = ConfirmView(author_id=interaction.user.id)
        await interaction.response.send_message(
            embed=info_embed("⚠️ 大会を中止しますか？", "この操作は取り消せません。"),
            view=view, ephemeral=True,
        )
        await view.wait()
        if not view.value:
            return
        t = await api_client.change_tournament_status(tournament_id, "cancel", interaction.user.id)
        await interaction.followup.send(embed=ok_embed("🛑 大会を中止しました", t["name"]), ephemeral=True)

    # ── 参照 ────────────────────────────────────────────────────────────────
    @app_commands.command(name="tournament", description="大会情報を表示")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def tournament(self, interaction: discord.Interaction, tournament_id: str):
        await self._show_info(interaction, tournament_id)

    @app_commands.command(name="tournament-info", description="大会情報を表示")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def tournament_info(self, interaction: discord.Interaction, tournament_id: str):
        await self._show_info(interaction, tournament_id)

    async def _show_info(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        t = await api_client.get_tournament(tournament_id)
        if not t:
            await interaction.followup.send(embed=info_embed("❌ 大会が見つかりません"), ephemeral=True)
            return
        await interaction.followup.send(embed=_tournament_embed(t))

    @app_commands.command(name="tournament-rules", description="大会ルールを表示")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def tournament_rules(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        t = await api_client.get_tournament(tournament_id)
        if not t:
            await interaction.followup.send(embed=info_embed("❌ 大会が見つかりません"), ephemeral=True)
            return
        rules = t.get("rules")
        e = brand_embed(f"📜 {t.get('name')} ルール")
        if isinstance(rules, dict) and rules:
            for k, v in list(rules.items())[:20]:
                e.add_field(name=str(k), value=str(v)[:1024], inline=False)
        else:
            e.description = "ルールは未設定です。"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="tournament-schedule", description="試合日程を表示")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def tournament_schedule(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        bracket = await api_client.get_bracket(tournament_id)
        e = brand_embed("🗓 試合日程")
        if not bracket or not bracket.get("rounds"):
            e.description = "ブラケット未生成です。"
            await interaction.followup.send(embed=e)
            return
        for rnd, matches in sorted(bracket["rounds"].items(), key=lambda x: int(x[0])):
            lines = []
            for m in matches:
                t1 = (m.get("team1") or {}).get("name", "TBD")
                t2 = (m.get("team2") or {}).get("name", "TBD")
                when = str(m.get("scheduled_at"))[:16] if m.get("scheduled_at") else "未定"
                lines.append(f"`M{m.get('match_number')}` {t1} vs {t2} — {when}")
            e.add_field(name=f"Round {rnd}", value="\n".join(lines)[:1024] or "—", inline=False)
        await interaction.followup.send(embed=e)

    @app_commands.command(name="tournament-standings", description="順位表を表示")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def tournament_standings(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        rankings = await api_client.get_rankings(tournament_id, limit=16)
        e = brand_embed("📊 順位表")
        if not rankings:
            e.description = "順位データがまだありません。"
        else:
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}
            lines = []
            for r in rankings:
                pos = r["rank_position"]
                badge = medal.get(pos, f"{pos}.")
                lines.append(
                    f"{badge} **{r['team_name']}** [{r['team_tag']}] — "
                    f"{r['points']}pt ({r['wins']}W-{r['losses']}L)"
                )
            e.description = "\n".join(lines)[:4000]
        await interaction.followup.send(embed=e)

    @app_commands.command(name="tournament-participants", description="参加チーム一覧")
    @app_commands.describe(tournament_id="大会ID")
    @app_commands.autocomplete(tournament_id=tournament_autocomplete)
    async def tournament_participants(self, interaction: discord.Interaction, tournament_id: str):
        await interaction.response.defer()
        status = await api_client.check_in_status(tournament_id)
        e = brand_embed("👥 参加チーム")
        teams = (status or {}).get("checked_in", []) + (status or {}).get("missed", [])
        if not teams:
            e.description = "承認済みの参加チームがありません。"
        else:
            checked = {t["team_id"] for t in (status or {}).get("checked_in", [])}
            lines = [
                f"{'✅' if t['team_id'] in checked else '⬜'} **{t['name']}** [{t['tag']}]"
                for t in teams
            ]
            e.description = "\n".join(lines)[:4000]
            e.set_footer(text=f"チェックイン {status.get('checked_in_count', 0)}/{status.get('total', 0)}")
        await interaction.followup.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(TournamentCog(bot))
