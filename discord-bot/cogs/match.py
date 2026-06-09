"""試合コマンド: 表示/履歴/統計/結果報告/確認/異議/スクショ。"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import my_match_autocomplete
from ui.common import ResultConfirmView, brand_embed, info_embed, ok_embed
from ui.modals import DisputeModal
from ui.selects import ChoiceView, team_options

STATUS_EMOJI = {
    "scheduled": "🕒", "ongoing": "🔴", "completed": "🏁",
    "cancelled": "🛑", "forfeit": "🏳️", "no_show": "👻",
}


def _match_embed(m: dict) -> discord.Embed:
    t1 = (m.get("team1") or {}).get("name", "TBD")
    t2 = (m.get("team2") or {}).get("name", "TBD")
    e = brand_embed(f"{STATUS_EMOJI.get(m.get('status'), '⚔️')} {t1} vs {t2}")
    e.add_field(name="形式", value=m.get("format", "—"), inline=True)
    e.add_field(name="状態", value=m.get("status", "—"), inline=True)
    e.add_field(name="ラウンド", value=str(m.get("round_number", "—")), inline=True)
    games = m.get("games") or []
    if games:
        score = []
        for g in games:
            score.append(f"Map{g.get('game_number')}: {g.get('team1_score')}-{g.get('team2_score')} ({g.get('map_name') or '—'})")
        e.add_field(name="ゲーム", value="\n".join(score)[:1024], inline=False)
    if m.get("winner_id"):
        wname = t1 if (m.get("team1") or {}).get("id") == m["winner_id"] else t2
        e.add_field(name="勝者", value=f"🏅 {wname}", inline=False)
    e.url = f"{config.web}/matches/{m.get('id')}"
    return e


class MatchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="match", description="試合情報を表示")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    async def match(self, interaction: discord.Interaction, match_id: str):
        await interaction.response.defer()
        m = await api_client.get_match(match_id)
        if not m:
            await interaction.followup.send(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        await interaction.followup.send(embed=_match_embed(m))

    @app_commands.command(name="match-stats", description="試合の詳細スタッツ")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    async def match_stats(self, interaction: discord.Interaction, match_id: str):
        await interaction.response.defer()
        m = await api_client.get_match(match_id)
        if not m:
            await interaction.followup.send(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        e = brand_embed("📊 試合スタッツ")
        for g in (m.get("games") or []):
            rows = []
            for ps in (g.get("player_stats") or [])[:10]:
                rows.append(f"{ps.get('player_name','?')}: {ps.get('kills')}/{ps.get('deaths')}/{ps.get('assists')} (KDA {ps.get('kda')})")
            e.add_field(
                name=f"Map{g.get('game_number')} {g.get('map_name') or ''}",
                value="\n".join(rows)[:1024] or "スタッツなし", inline=False,
            )
        if not (m.get("games")):
            e.description = "ゲームデータがありません。"
        await interaction.followup.send(embed=e)

    @app_commands.command(name="match-summary", description="試合サマリー")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    async def match_summary(self, interaction: discord.Interaction, match_id: str):
        await interaction.response.defer()
        m = await api_client.get_match(match_id)
        if not m:
            await interaction.followup.send(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        await interaction.followup.send(embed=_match_embed(m))

    @app_commands.command(name="my-matches", description="自分のチームの試合一覧")
    @requires(Role.PLAYER)
    async def my_matches(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._list_matches(interaction, only_pending=False)

    @app_commands.command(name="next-match", description="自分のチームの次の試合")
    @requires(Role.PLAYER)
    async def next_match(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        matches = await api_client.my_matches(interaction.user.id, limit=20)
        nxt = next((m for m in matches if m.get("status") in ("scheduled", "ongoing")), None)
        if not nxt:
            await interaction.followup.send(embed=info_embed("🎉 次の試合はありません"), ephemeral=True)
            return
        full = await api_client.get_match(nxt["id"])
        await interaction.followup.send(embed=_match_embed(full or nxt), ephemeral=True)

    @app_commands.command(name="match-history", description="自分のチームの試合履歴")
    @requires(Role.PLAYER)
    async def match_history(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._list_matches(interaction, only_pending=False, completed_only=True)

    async def _list_matches(self, interaction, only_pending=False, completed_only=False):
        matches = await api_client.my_matches(interaction.user.id, limit=25)
        if completed_only:
            matches = [m for m in matches if m.get("status") in ("completed", "forfeit")]
        e = brand_embed("⚔️ 試合一覧")
        if not matches:
            e.description = "試合が見つかりません（チーム未所属または未連携の可能性）。"
        else:
            e.description = "\n".join(
                f"{STATUS_EMOJI.get(m.get('status'),'⚔️')} R{m.get('round_number')}-M{m.get('match_number')} "
                f"`{m.get('id')[:8]}`"
                for m in matches
            )[:4000]
        await interaction.followup.send(embed=e, ephemeral=True)

    # ── 結果報告フロー ─────────────────────────────────────────────────────
    @app_commands.command(name="report-result", description="試合結果を報告（勝者を選択）")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    @requires(Role.CAPTAIN)
    async def report_result(self, interaction: discord.Interaction, match_id: str):
        m = await api_client.get_match(match_id)
        if not m:
            await interaction.response.send_message(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        opts = team_options(m)
        if len(opts) < 2:
            await interaction.response.send_message(embed=info_embed("⚠️ 対戦チーム未確定"), ephemeral=True)
            return

        async def _pick(i: discord.Interaction, winner_id: str):
            res = await api_client.report_result(match_id, winner_id, i.user.id)
            wname = next((o.label for o in opts if o.value == winner_id), "勝者")
            if (res or {}).get("status") == "confirmed":
                await i.response.edit_message(
                    embed=ok_embed("✅ 結果を登録しました", f"勝者: {wname}"), view=None
                )
            else:
                await i.response.edit_message(
                    embed=ok_embed("📨 報告しました", "相手チームの確認待ちです"), view=None
                )
                # チャンネルに確認ボタンを掲示（相手キャプテン/運営がクリック）
                pub = brand_embed(
                    "📨 結果確認待ち",
                    f"**{wname}** の勝利が報告されました。\n相手チームのキャプテンは確認してください。",
                )
                await i.channel.send(embed=pub, view=ResultConfirmView(match_id))

        view = ChoiceView("勝者を選択", opts, _pick, author_id=interaction.user.id)
        await interaction.response.send_message(
            embed=brand_embed("🏆 結果報告", "この試合の勝者を選択してください"), view=view, ephemeral=True
        )

    @app_commands.command(name="confirm-result", description="相手の報告を確認して確定")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    @requires(Role.CAPTAIN)
    async def confirm_result(self, interaction: discord.Interaction, match_id: str):
        await interaction.response.defer(ephemeral=True)
        await api_client.confirm_result(match_id, interaction.user.id)
        await interaction.followup.send(embed=ok_embed("✅ 結果を確定しました"), ephemeral=True)

    @app_commands.command(name="dispute-result", description="結果に異議を申し立て")
    @app_commands.describe(match_id="試合ID")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    @requires(Role.CAPTAIN)
    async def dispute_result(self, interaction: discord.Interaction, match_id: str):
        await interaction.response.send_modal(DisputeModal(match_id))

    @app_commands.command(name="upload-screenshot", description="試合のスクショを添付")
    @app_commands.describe(match_id="試合ID", screenshot="結果のスクリーンショット")
    @app_commands.autocomplete(match_id=my_match_autocomplete)
    @requires(Role.PLAYER)
    async def upload_screenshot(
        self, interaction: discord.Interaction, match_id: str, screenshot: discord.Attachment,
    ):
        if not (screenshot.content_type or "").startswith("image/"):
            await interaction.response.send_message(embed=info_embed("⚠️ 画像を添付してください"), ephemeral=True)
            return
        e = brand_embed("📸 スクリーンショット", f"試合 `{match_id[:8]}` / 提出: {interaction.user.mention}")
        e.set_image(url=screenshot.url)
        await interaction.response.send_message(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(MatchCog(bot))
