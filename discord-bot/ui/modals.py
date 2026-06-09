"""Discord Modal（フォーム入力）。"""

import discord

from core.errors import to_user_embed
from services.api_client import api_client


class DisputeModal(discord.ui.Modal, title="結果に異議を申し立て"):
    reason = discord.ui.TextInput(
        label="理由",
        style=discord.TextStyle.paragraph,
        placeholder="例: スコアが違う / 不正の疑い / 接続切断 など",
        max_length=500,
        required=True,
    )

    def __init__(self, match_id: str):
        super().__init__()
        self.match_id = match_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await api_client.dispute_result(self.match_id, str(self.reason), interaction.user.id)
        except Exception as e:
            await interaction.response.send_message(embed=to_user_embed(e), ephemeral=True)
            return
        await interaction.response.send_message(
            "⚠️ 異議を受け付けました。運営が確認します。", ephemeral=True
        )
