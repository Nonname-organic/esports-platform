"""Slash command autocomplete プロバイダ。

IDの手入力を排除し、名前で検索→ID選択を可能にする。
全て失敗時は空リストを返し、コマンド自体は壊さない。
"""

from discord import app_commands

from config import MAP_POOLS
from services.api_client import api_client

_MAX = 25


def _choice(name: str, value: str) -> app_commands.Choice:
    return app_commands.Choice(name=name[:100], value=value)


async def tournament_autocomplete(interaction, current: str):
    try:
        items = await api_client.list_tournaments(limit=_MAX)
        cur = (current or "").lower()
        out = []
        for t in items:
            label = f"{t.get('name')} ({t.get('game')})"
            if cur in label.lower():
                out.append(_choice(label, str(t.get("id"))))
        return out[:_MAX]
    except Exception:
        return []


async def team_autocomplete(interaction, current: str):
    try:
        items = await api_client.list_teams(limit=_MAX)
        cur = (current or "").lower()
        out = []
        for t in items:
            label = f"{t.get('name')} [{t.get('tag')}]"
            if cur in label.lower():
                out.append(_choice(label, str(t.get("id"))))
        return out[:_MAX]
    except Exception:
        return []


async def player_autocomplete(interaction, current: str):
    try:
        items = await api_client.list_players(limit=_MAX)
        cur = (current or "").lower()
        out = []
        for p in items:
            label = p.get("in_game_name") or p.get("username") or str(p.get("id"))
            if cur in label.lower():
                out.append(_choice(label, str(p.get("id"))))
        return out[:_MAX]
    except Exception:
        return []


async def my_match_autocomplete(interaction, current: str):
    """実行者の所属チームの試合を候補化。"""
    try:
        matches = await api_client.my_matches(interaction.user.id, limit=_MAX)
        out = []
        for m in matches:
            label = f"R{m.get('round_number')}-M{m.get('match_number')} ({m.get('status')})"
            out.append(_choice(label, str(m.get("id"))))
        return out[:_MAX]
    except Exception:
        return []


async def map_autocomplete(interaction, current: str):
    """namespace.game があればそのプール、無ければ全マップ。"""
    try:
        game = getattr(interaction.namespace, "game", None)
        pool = MAP_POOLS.get(str(game).upper(), []) if game else [m for v in MAP_POOLS.values() for m in v]
        cur = (current or "").lower()
        return [_choice(m, m) for m in pool if cur in m.lower()][:_MAX]
    except Exception:
        return []
