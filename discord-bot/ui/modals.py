"""Discord Modal（フォーム入力）。"""

import discord

from core.errors import to_user_embed
from services.api_client import api_client


class RecruitmentModal(discord.ui.Modal, title="募集を投稿"):
    title_in = discord.ui.TextInput(label="タイトル", max_length=100, required=True)
    desc_in = discord.ui.TextInput(
        label="詳細", style=discord.TextStyle.paragraph, max_length=1000, required=False,
    )

    def __init__(self, post_type: str, game: str):
        super().__init__()
        self.post_type = post_type
        self.game = game

    async def on_submit(self, interaction: discord.Interaction):
        try:
            res = await api_client.create_recruitment(
                self.post_type, self.game, str(self.title_in), str(self.desc_in) or None,
                interaction.user.id,
            )
        except Exception as e:
            await interaction.response.send_message(embed=to_user_embed(e), ephemeral=True)
            return
        await interaction.response.send_message(
            f"✅ 募集を投稿しました: **{res.get('title')}**", ephemeral=True
        )


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
