"""ヘルプ: 実行者のロールに応じてコマンドを表示。"""

import discord
from discord import app_commands
from discord.ext import commands

from core.rbac import LABEL, Role, member_role
from ui.common import brand_embed

# (category, [(command, min_role, desc)])
CATALOG: list[tuple[str, list[tuple[str, Role, str]]]] = [
    ("🏆 Tournament", [
        ("/tournament", Role.SPECTATOR, "大会情報"),
        ("/tournament-rules", Role.SPECTATOR, "ルール"),
        ("/tournament-schedule", Role.SPECTATOR, "日程"),
        ("/tournament-standings", Role.SPECTATOR, "順位"),
        ("/tournament-participants", Role.SPECTATOR, "参加チーム"),
        ("/create-tournament", Role.ORGANIZER, "サーバー構築"),
        ("/edit-tournament", Role.ORGANIZER, "編集"),
        ("/start-tournament", Role.ORGANIZER, "開始"),
        ("/end-tournament", Role.ORGANIZER, "終了"),
        ("/cancel-tournament", Role.ORGANIZER, "中止"),
    ]),
    ("📊 Bracket", [
        ("/bracket", Role.SPECTATOR, "表示"),
        ("/bracket-link", Role.SPECTATOR, "Webリンク"),
        ("/bracket-image", Role.SPECTATOR, "ビジュアル"),
        ("/current-round", Role.SPECTATOR, "現在ラウンド"),
        ("/advance-match", Role.ORGANIZER, "勝者確定"),
        ("/regenerate-bracket", Role.ORGANIZER, "生成/再生成"),
    ]),
    ("✅ Check-In", [
        ("/check-in", Role.PLAYER, "チェックイン"),
        ("/check-in-status", Role.SPECTATOR, "状況"),
        ("/check-in-all", Role.ORGANIZER, "一括"),
        ("/missed-check-in", Role.ORGANIZER, "未完了一覧"),
    ]),
    ("⚔️ Match", [
        ("/match", Role.SPECTATOR, "試合情報"),
        ("/match-stats", Role.SPECTATOR, "スタッツ"),
        ("/match-summary", Role.SPECTATOR, "サマリー"),
        ("/my-matches", Role.PLAYER, "自分の試合"),
        ("/next-match", Role.PLAYER, "次の試合"),
        ("/match-history", Role.PLAYER, "履歴"),
        ("/report-result", Role.CAPTAIN, "結果報告"),
        ("/confirm-result", Role.CAPTAIN, "結果確認"),
        ("/dispute-result", Role.CAPTAIN, "異議"),
        ("/upload-screenshot", Role.PLAYER, "スクショ"),
    ]),
    ("🗺 Map Veto", [
        ("/ban-map", Role.CAPTAIN, "Ban"),
        ("/pick-map", Role.CAPTAIN, "Pick"),
        ("/current-veto", Role.SPECTATOR, "状況"),
        ("/remaining-maps", Role.SPECTATOR, "残り"),
        ("/confirm-veto", Role.CAPTAIN, "確定"),
    ]),
    ("🛡 Team", [
        ("/team", Role.SPECTATOR, "情報"),
        ("/team-roster", Role.SPECTATOR, "ロスター"),
        ("/team-stats", Role.SPECTATOR, "スタッツ"),
        ("/team-history", Role.SPECTATOR, "履歴"),
        ("/team-rating", Role.SPECTATOR, "レーティング"),
        ("/team-achievements", Role.SPECTATOR, "実績"),
        ("/invite-player", Role.CAPTAIN, "招待"),
        ("/remove-player", Role.CAPTAIN, "除外"),
        ("/promote-player", Role.CAPTAIN, "ロール変更"),
        ("/leave-team", Role.PLAYER, "脱退"),
    ]),
    ("🎮 Player", [
        ("/player", Role.SPECTATOR, "プロフィール"),
        ("/player-stats", Role.SPECTATOR, "スタッツ"),
        ("/player-career", Role.SPECTATOR, "キャリア"),
        ("/player-rating", Role.SPECTATOR, "レーティング"),
        ("/player-history", Role.SPECTATOR, "推移"),
        ("/player-achievements", Role.SPECTATOR, "実績"),
        ("/open-to-work", Role.PLAYER, "募集中ON"),
        ("/close-to-work", Role.PLAYER, "募集中OFF"),
    ]),
    ("🔭 Scout", [
        ("/search-player", Role.SPECTATOR, "選手検索"),
        ("/search-team", Role.SPECTATOR, "チーム検索"),
        ("/player-availability", Role.SPECTATOR, "募集中選手"),
        ("/team-recruitment", Role.SPECTATOR, "募集投稿"),
        ("/recommend-players", Role.SPECTATOR, "おすすめ選手"),
        ("/recommend-teams", Role.SPECTATOR, "おすすめチーム"),
        ("/post-recruitment", Role.PLAYER, "募集投稿"),
        ("/apply-recruitment", Role.PLAYER, "応募"),
        ("/invite-candidate", Role.CAPTAIN, "候補招待"),
    ]),
    ("📈 Analytics / Career", [
        ("/map-stats", Role.SPECTATOR, "マップ統計"),
        ("/agent-stats", Role.SPECTATOR, "構成統計"),
        ("/rankings", Role.SPECTATOR, "順位"),
        ("/leaderboard", Role.SPECTATOR, "上位選手"),
        ("/meta-analysis", Role.SPECTATOR, "メタ分析"),
        ("/career", Role.SPECTATOR, "キャリア"),
        ("/history", Role.SPECTATOR, "履歴"),
        ("/achievements", Role.SPECTATOR, "実績"),
        ("/rating-history", Role.SPECTATOR, "レート推移"),
        ("/performance-trend", Role.SPECTATOR, "傾向"),
    ]),
    ("🔔 Notify / 🎥 Stream / 🆘 Support", [
        ("/unread-notifications", Role.PLAYER, "未読通知"),
        ("/subscriptions", Role.PLAYER, "購読"),
        ("/notification-settings", Role.PLAYER, "設定"),
        ("/reminders", Role.PLAYER, "リマインダー"),
        ("/stream", Role.SPECTATOR, "配信"),
        ("/live", Role.SPECTATOR, "LIVE"),
        ("/stream-info", Role.SPECTATOR, "配信情報"),
        ("/support", Role.SPECTATOR, "サポート"),
        ("/contact-admin", Role.PLAYER, "運営連絡"),
        ("/report-player", Role.PLAYER, "通報"),
    ]),
    ("🛠 Moderator", [
        ("/warn", Role.ORGANIZER, "警告"),
        ("/mute", Role.ORGANIZER, "ミュート"),
        ("/unmute", Role.ORGANIZER, "解除"),
        ("/forfeit-match", Role.ORGANIZER, "不戦敗"),
        ("/reopen-match", Role.ORGANIZER, "再オープン"),
        ("/kick-player", Role.ADMIN, "キック"),
    ]),
]


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="利用可能なコマンド一覧（ロール別）")
    async def help_cmd(self, interaction: discord.Interaction):
        role = member_role(interaction.user)
        e = brand_embed(
            "🤖 Discord Tournament OS",
            f"あなたのロール: **{LABEL[role]}** — 実行可能なコマンドのみ表示しています。",
        )
        for category, cmds in CATALOG:
            usable = [f"`{name}` {desc}" for name, mr, desc in cmds if role >= mr]
            if usable:
                e.add_field(name=category, value="\n".join(usable)[:1024], inline=False)
        e.set_footer(text="🔒 上位ロール専用コマンドは非表示。/link でアカウント連携すると本人操作が可能に。")
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
