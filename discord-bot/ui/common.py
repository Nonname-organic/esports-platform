"""共通embed / Button View（確認・結果確認）。"""

import discord

from config import config
from core.errors import to_user_embed
from services.api_client import api_client

BRAND = config.BRAND_COLOR


def brand_embed(title: str, description: str | None = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=BRAND)


def ok_embed(title: str, description: str | None = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=0x2ECC71)


def info_embed(title: str, description: str | None = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=0x95A5A6)


class ConfirmView(discord.ui.View):
    """危険操作の二段確認（実行者本人のみ操作可）。"""

    def __init__(self, *, author_id: int, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.value: bool | None = None
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("実行者のみ操作できます", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="実行する", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class ResultConfirmView(discord.ui.View):
    """結果報告後、相手キャプテン/運営が確認 or 異議。"""

    def __init__(self, match_id: str, timeout: float = 3600):
        super().__init__(timeout=timeout)
        self.match_id = match_id

    @discord.ui.button(label="✅ 結果を確認", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await api_client.confirm_result(self.match_id, interaction.user.id)
        except Exception as e:
            await interaction.response.send_message(embed=to_user_embed(e), ephemeral=True)
            return
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(
            content="✅ 両者確認済み。結果が確定しました。", view=self
        )
        self.stop()

    @discord.ui.button(label="⚠️ 異議あり", style=discord.ButtonStyle.danger)
    async def dispute(self, interaction: discord.Interaction, button: discord.ui.Button):
        from ui.modals import DisputeModal
        await interaction.response.send_modal(DisputeModal(self.match_id))
