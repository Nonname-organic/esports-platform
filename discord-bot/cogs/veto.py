"""Map Ban/Pick（VALORANT / CS2）。

進行状態はバックエンド(Redis)にチャンネル単位で永続化（Bot再起動でも保持）。
veto LOGIC はBot側（MAP_POOLS）、永続化は /api/v1/bot/veto/{key}。
"""

import discord
from discord import app_commands
from discord.ext import commands

from config import MAP_POOLS
from core.rbac import Role, requires
from services.api_client import api_client
from services.autocomplete import map_autocomplete
from ui.common import brand_embed, info_embed, ok_embed

GAME_CHOICES = [
    app_commands.Choice(name="VALORANT", value="VALORANT"),
    app_commands.Choice(name="CS2", value="CS2"),
]


def _remaining(s: dict) -> list[str]:
    used = set(s.get("banned", [])) | set(s.get("picked", []))
    return [m for m in s.get("pool", []) if m not in used]


def _state_embed(s: dict) -> discord.Embed:
    e = brand_embed(f"🗺 Map Veto — {s.get('game')}")
    e.add_field(name="🚫 Ban", value=", ".join(s.get("banned", [])) or "—", inline=False)
    e.add_field(name="✅ Pick", value=", ".join(s.get("picked", [])) or "—", inline=False)
    e.add_field(name="残り", value=", ".join(_remaining(s)) or "—", inline=False)
    return e


class VetoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _key(self, interaction: discord.Interaction) -> str:
        return str(interaction.channel_id)

    async def _load(self, interaction, game: str | None = None) -> dict | None:
        s = await api_client.veto_get(self._key(interaction))
        if s is None and game:
            s = {"game": game, "pool": list(MAP_POOLS.get(game, [])), "banned": [], "picked": []}
            await api_client.veto_put(self._key(interaction), s)
        return s

    async def _save(self, interaction, s: dict) -> None:
        await api_client.veto_put(self._key(interaction), s)

    @app_commands.command(name="ban-map", description="マップをBan")
    @app_commands.describe(game="ゲーム", map="Banするマップ")
    @app_commands.choices(game=GAME_CHOICES)
    @app_commands.autocomplete(map=map_autocomplete)
    @requires(Role.CAPTAIN)
    async def ban_map(self, interaction: discord.Interaction, game: app_commands.Choice[str], map: str):
        await interaction.response.defer()
        s = await self._load(interaction, game.value)
        if map not in _remaining(s):
            await interaction.followup.send(embed=info_embed("⚠️ そのマップは選べません"), ephemeral=True)
            return
        s["banned"].append(map)
        await self._save(interaction, s)
        await interaction.followup.send(
            embed=_state_embed(s).set_footer(text=f"{interaction.user.display_name} が {map} をBan")
        )

    @app_commands.command(name="pick-map", description="マップをPick")
    @app_commands.describe(game="ゲーム", map="Pickするマップ")
    @app_commands.choices(game=GAME_CHOICES)
    @app_commands.autocomplete(map=map_autocomplete)
    @requires(Role.CAPTAIN)
    async def pick_map(self, interaction: discord.Interaction, game: app_commands.Choice[str], map: str):
        await interaction.response.defer()
        s = await self._load(interaction, game.value)
        if map not in _remaining(s):
            await interaction.followup.send(embed=info_embed("⚠️ そのマップは選べません"), ephemeral=True)
            return
        s["picked"].append(map)
        await self._save(interaction, s)
        await interaction.followup.send(
            embed=_state_embed(s).set_footer(text=f"{interaction.user.display_name} が {map} をPick")
        )

    @app_commands.command(name="current-veto", description="現在のveto状況")
    async def current_veto(self, interaction: discord.Interaction):
        await interaction.response.defer()
        s = await self._load(interaction)
        if not s:
            await interaction.followup.send(embed=info_embed("vetoは進行していません", "`/ban-map` で開始"), ephemeral=True)
            return
        await interaction.followup.send(embed=_state_embed(s))

    @app_commands.command(name="remaining-maps", description="残りマップ")
    async def remaining_maps(self, interaction: discord.Interaction):
        await interaction.response.defer()
        s = await self._load(interaction)
        if not s:
            await interaction.followup.send(embed=info_embed("vetoは進行していません"), ephemeral=True)
            return
        await interaction.followup.send(embed=brand_embed("🗺 残りマップ", ", ".join(_remaining(s)) or "なし"))

    @app_commands.command(name="confirm-veto", description="vetoを確定")
    @requires(Role.CAPTAIN)
    async def confirm_veto(self, interaction: discord.Interaction):
        await interaction.response.defer()
        s = await self._load(interaction)
        if not s:
            await interaction.followup.send(embed=info_embed("vetoは進行していません"), ephemeral=True)
            return
        decider = s.get("picked") or _remaining(s)
        e = ok_embed("✅ Veto確定", f"**使用マップ:** {', '.join(decider) or '—'}")
        e.add_field(name="Ban", value=", ".join(s.get("banned", [])) or "—", inline=False)
        await api_client.veto_delete(self._key(interaction))
        await interaction.followup.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(VetoCog(bot))
