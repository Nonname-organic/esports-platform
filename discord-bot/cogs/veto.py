"""Map Ban/Pick（VALORANT / CS2）。

進行状態はBotのメモリにチャンネル単位で保持（単一インスタンス前提）。
最終確定マップはチャンネルに掲示。DB永続化は将来 /matches/{id}/banpick に接続可能。
"""

import discord
from discord import app_commands
from discord.ext import commands

from config import MAP_POOLS
from core.rbac import Role, requires
from services.autocomplete import map_autocomplete
from ui.common import brand_embed, info_embed, ok_embed

# channel_id -> {"game","pool","banned","picked"}
_sessions: dict[int, dict] = {}

GAME_CHOICES = [
    app_commands.Choice(name="VALORANT", value="VALORANT"),
    app_commands.Choice(name="CS2", value="CS2"),
]


def _session(channel_id: int, game: str | None = None) -> dict:
    s = _sessions.get(channel_id)
    if s is None and game:
        s = {"game": game, "pool": list(MAP_POOLS.get(game, [])), "banned": [], "picked": []}
        _sessions[channel_id] = s
    return s


def _remaining(s: dict) -> list[str]:
    used = set(s["banned"]) | set(s["picked"])
    return [m for m in s["pool"] if m not in used]


def _state_embed(s: dict) -> discord.Embed:
    e = brand_embed(f"🗺 Map Veto — {s['game']}")
    e.add_field(name="🚫 Ban", value=", ".join(s["banned"]) or "—", inline=False)
    e.add_field(name="✅ Pick", value=", ".join(s["picked"]) or "—", inline=False)
    e.add_field(name="残り", value=", ".join(_remaining(s)) or "—", inline=False)
    return e


class VetoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ban-map", description="マップをBan")
    @app_commands.describe(game="ゲーム", map="Banするマップ")
    @app_commands.choices(game=GAME_CHOICES)
    @app_commands.autocomplete(map=map_autocomplete)
    @requires(Role.CAPTAIN)
    async def ban_map(self, interaction: discord.Interaction, game: app_commands.Choice[str], map: str):
        s = _session(interaction.channel_id, game.value)
        if map not in _remaining(s):
            await interaction.response.send_message(embed=info_embed("⚠️ そのマップは選べません"), ephemeral=True)
            return
        s["banned"].append(map)
        await interaction.response.send_message(
            embed=_state_embed(s).set_footer(text=f"{interaction.user.display_name} が {map} をBan")
        )

    @app_commands.command(name="pick-map", description="マップをPick")
    @app_commands.describe(game="ゲーム", map="Pickするマップ")
    @app_commands.choices(game=GAME_CHOICES)
    @app_commands.autocomplete(map=map_autocomplete)
    @requires(Role.CAPTAIN)
    async def pick_map(self, interaction: discord.Interaction, game: app_commands.Choice[str], map: str):
        s = _session(interaction.channel_id, game.value)
        if map not in _remaining(s):
            await interaction.response.send_message(embed=info_embed("⚠️ そのマップは選べません"), ephemeral=True)
            return
        s["picked"].append(map)
        await interaction.response.send_message(
            embed=_state_embed(s).set_footer(text=f"{interaction.user.display_name} が {map} をPick")
        )

    @app_commands.command(name="current-veto", description="現在のveto状況")
    async def current_veto(self, interaction: discord.Interaction):
        s = _sessions.get(interaction.channel_id)
        if not s:
            await interaction.response.send_message(embed=info_embed("vetoは進行していません", "`/ban-map` で開始"), ephemeral=True)
            return
        await interaction.response.send_message(embed=_state_embed(s))

    @app_commands.command(name="remaining-maps", description="残りマップ")
    async def remaining_maps(self, interaction: discord.Interaction):
        s = _sessions.get(interaction.channel_id)
        if not s:
            await interaction.response.send_message(embed=info_embed("vetoは進行していません"), ephemeral=True)
            return
        await interaction.response.send_message(
            embed=brand_embed("🗺 残りマップ", ", ".join(_remaining(s)) or "なし")
        )

    @app_commands.command(name="confirm-veto", description="vetoを確定")
    @requires(Role.CAPTAIN)
    async def confirm_veto(self, interaction: discord.Interaction):
        s = _sessions.pop(interaction.channel_id, None)
        if not s:
            await interaction.response.send_message(embed=info_embed("vetoは進行していません"), ephemeral=True)
            return
        decider = s["picked"] or _remaining(s)
        e = ok_embed("✅ Veto確定", f"**使用マップ:** {', '.join(decider) or '—'}")
        e.add_field(name="Ban", value=", ".join(s["banned"]) or "—", inline=False)
        await interaction.response.send_message(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(VetoCog(bot))
