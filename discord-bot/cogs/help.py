"""ヘルプ: Discordで使える進行コマンド一覧（ロール別）。

基本操作（登録/チェックイン/プロフィール/チーム編成/閲覧/スカウト/大会運営）はWeb。
DiscordはVeto・ダイス・結果報告など「試合チャンネル内で完結する進行」に限定。
"""

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core.rbac import LABEL, Role, member_role
from ui.common import brand_embed

CATALOG: list[tuple[str, list[tuple[str, Role, str]]]] = [
    ("🔗 連携", [
        ("/link", Role.SPECTATOR, "アカウント連携（Webでコード発行）"),
        ("/whoami", Role.SPECTATOR, "連携情報"),
        ("/unlink", Role.SPECTATOR, "連携解除"),
    ]),
    ("🗺 Map Veto", [
        ("/ban-map", Role.CAPTAIN, "マップをBan"),
        ("/pick-map", Role.CAPTAIN, "マップをPick"),
        ("/current-veto", Role.SPECTATOR, "veto状況"),
        ("/remaining-maps", Role.SPECTATOR, "残りマップ"),
        ("/confirm-veto", Role.CAPTAIN, "veto確定"),
    ]),
    ("🎲 進行ユーティリティ", [
        ("/roll", Role.SPECTATOR, "ダイス（例 1d100, 2d6）"),
        ("/coinflip", Role.SPECTATOR, "コイントス"),
        ("/pick", Role.SPECTATOR, "候補から抽選"),
    ]),
    ("⚔️ 試合進行", [
        ("/match", Role.SPECTATOR, "試合情報"),
        ("/report-result", Role.CAPTAIN, "結果報告（勝者選択）"),
        ("/confirm-result", Role.CAPTAIN, "相手の報告を確認"),
        ("/dispute-result", Role.CAPTAIN, "異議申し立て"),
        ("/upload-screenshot", Role.PLAYER, "スクショ提出（証跡）"),
        ("/match-evidence", Role.SPECTATOR, "証跡一覧"),
    ]),
]


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Discordで使える進行コマンド一覧")
    async def help_cmd(self, interaction: discord.Interaction):
        role = member_role(interaction.user)
        e = brand_embed(
            "🤖 大会進行コマンド",
            f"あなたのロール: **{LABEL[role]}**\n"
            "💡 登録・チェックイン・プロフィール・チーム編成・順位/統計の閲覧・大会運営は "
            f"**[Webサイト]({config.web})** で行います。Discordは試合チャンネル内の進行専用です。",
        )
        for category, cmds in CATALOG:
            usable = [f"`{name}` {desc}" for name, mr, desc in cmds if role >= mr]
            if usable:
                e.add_field(name=category, value="\n".join(usable)[:1024], inline=False)
        e.set_footer(text="まず /link でアカウント連携（結果報告に必要）")
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
