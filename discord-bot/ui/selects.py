"""汎用Select Menu View（勝者選択 / マップ選択 等）。"""

from typing import Awaitable, Callable

import discord


class _CallbackSelect(discord.ui.Select):
    def __init__(self, placeholder: str, options: list[discord.SelectOption], cb):
        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)
        self._cb = cb

    async def callback(self, interaction: discord.Interaction):
        await self._cb(interaction, self.values[0])


class ChoiceView(discord.ui.View):
    """単一選択Select。author_idのみ操作可。callback(interaction, value)。"""

    def __init__(
        self,
        placeholder: str,
        options: list[discord.SelectOption],
        callback: Callable[[discord.Interaction, str], Awaitable[None]],
        *,
        author_id: int,
        timeout: float = 120,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.add_item(_CallbackSelect(placeholder, options, callback))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("実行者のみ操作できます", ephemeral=True)
            return False
        return True


def team_options(match: dict) -> list[discord.SelectOption]:
    """試合の2チームをSelectOption化（勝者選択用）。"""
    opts = []
    for key in ("team1", "team2"):
        t = match.get(key)
        if t and t.get("id"):
            opts.append(discord.SelectOption(
                label=f"{t.get('name', 'TBD')} [{t.get('tag', '')}]"[:100], value=str(t["id"])
            ))
    return opts


def map_options(maps: list[str]) -> list[discord.SelectOption]:
    return [discord.SelectOption(label=m, value=m) for m in maps[:25]]
