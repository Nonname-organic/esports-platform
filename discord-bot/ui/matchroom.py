"""Match Room: 試合チャンネルに常設する操作パネル（永続ボタン）。

discord.ui.DynamicItem を使い、custom_id に match_id を埋め込むことで
Bot再起動後もボタンが機能する（add_dynamic_items で登録）。
"""

import discord

from core.errors import to_user_embed
from services.api_client import api_client
from ui.common import ResultConfirmView, brand_embed, info_embed, ok_embed
from ui.modals import DisputeModal
from ui.selects import ChoiceView, team_options


class MRReport(discord.ui.DynamicItem[discord.ui.Button], template=r"mr:report:(?P<mid>[\w-]+)"):
    def __init__(self, match_id: str):
        self.match_id = match_id
        super().__init__(
            discord.ui.Button(label="🏆 結果報告", style=discord.ButtonStyle.success,
                              custom_id=f"mr:report:{match_id}")
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(match["mid"])

    async def callback(self, interaction: discord.Interaction):
        m = await api_client.get_match(self.match_id)
        if not m:
            await interaction.response.send_message(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        opts = team_options(m)
        if len(opts) < 2:
            await interaction.response.send_message(embed=info_embed("⚠️ 対戦チーム未確定"), ephemeral=True)
            return
        mid = self.match_id

        async def _pick(i: discord.Interaction, winner_id: str):
            try:
                res = await api_client.report_result(mid, winner_id, i.user.id)
            except Exception as e:
                await i.response.edit_message(embed=to_user_embed(e), view=None)
                return
            wname = next((o.label for o in opts if o.value == winner_id), "勝者")
            if (res or {}).get("status") == "confirmed":
                await i.response.edit_message(embed=ok_embed("✅ 結果を登録しました", f"勝者: {wname}"), view=None)
            else:
                await i.response.edit_message(embed=ok_embed("📨 報告しました", "相手チームの確認待ち"), view=None)
                await i.channel.send(
                    embed=brand_embed("📨 結果確認待ち", f"**{wname}** の勝利が報告されました。相手キャプテンは確認してください。"),
                    view=ResultConfirmView(mid),
                )

        view = ChoiceView("勝者を選択", opts, _pick, author_id=interaction.user.id)
        await interaction.response.send_message(
            embed=brand_embed("🏆 結果報告", "勝者を選択してください"), view=view, ephemeral=True
        )


class MRDispute(discord.ui.DynamicItem[discord.ui.Button], template=r"mr:dispute:(?P<mid>[\w-]+)"):
    def __init__(self, match_id: str):
        self.match_id = match_id
        super().__init__(
            discord.ui.Button(label="⚠️ 異議", style=discord.ButtonStyle.danger,
                              custom_id=f"mr:dispute:{match_id}")
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(match["mid"])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DisputeModal(self.match_id))


class MRInfo(discord.ui.DynamicItem[discord.ui.Button], template=r"mr:info:(?P<mid>[\w-]+)"):
    def __init__(self, match_id: str):
        self.match_id = match_id
        super().__init__(
            discord.ui.Button(label="📋 試合情報", style=discord.ButtonStyle.secondary,
                              custom_id=f"mr:info:{match_id}")
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(match["mid"])

    async def callback(self, interaction: discord.Interaction):
        m = await api_client.get_match(self.match_id)
        if not m:
            await interaction.response.send_message(embed=info_embed("❌ 試合が見つかりません"), ephemeral=True)
            return
        t1 = (m.get("team1") or {}).get("name", "TBD")
        t2 = (m.get("team2") or {}).get("name", "TBD")
        e = brand_embed(f"⚔️ {t1} vs {t2}")
        e.add_field(name="状態", value=m.get("status", "—"), inline=True)
        e.add_field(name="形式", value=m.get("format", "—"), inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)


class MatchRoomView(discord.ui.View):
    """チャンネル生成時に貼る操作パネル。"""

    def __init__(self, match_id: str):
        super().__init__(timeout=None)
        self.add_item(MRReport(match_id))
        self.add_item(MRDispute(match_id))
        self.add_item(MRInfo(match_id))


def register(bot) -> None:
    """Bot起動時に永続ハンドラを登録。"""
    bot.add_dynamic_items(MRReport, MRDispute, MRInfo)
