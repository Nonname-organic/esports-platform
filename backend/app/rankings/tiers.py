"""競技ランキングの Tier / RP 定義（SSOT / ADR-0015）。

RP 付与式と Tier しきい値をここに一元化する。DTO・集約・フロントは必ずここ由来の値を使う。
UI は数値しきい値を持たず、tier_for / tier_progress の結果（Tier）だけを受け取る。
"""

from __future__ import annotations

# 順位 → RP（1大会あたり / 大会終了時のみ加算・途中敗退で減点しない）。
PLACEMENT_RP: dict[str, int] = {
    "champion": 1000,
    "runner_up": 600,
    "top4": 300,
    "participated": 100,
}

# Tier しきい値（min_rp 昇順）。key/label/color/icon は表示のSSOT。
TIERS: list[dict] = [
    {"key": "bronze", "label": "Bronze", "min_rp": 0, "color": "#b45309", "icon": "shield"},
    {"key": "silver", "label": "Silver", "min_rp": 1000, "color": "#94a3b8", "icon": "shield"},
    {"key": "gold", "label": "Gold", "min_rp": 2500, "color": "#eab308", "icon": "shield-half"},
    {"key": "platinum", "label": "Platinum", "min_rp": 5000, "color": "#22d3ee", "icon": "gem"},
    {"key": "diamond", "label": "Diamond", "min_rp": 9000, "color": "#60a5fa", "icon": "gem"},
    {"key": "master", "label": "Master", "min_rp": 15000, "color": "#a78bfa", "icon": "crown"},
    {"key": "grandmaster", "label": "Grandmaster", "min_rp": 25000, "color": "#f43f5e", "icon": "crown"},
]


def tier_for(rp: int) -> dict:
    """RP から現在の Tier を返す（純関数 / 公開API）。"""
    current = TIERS[0]
    for t in TIERS:
        if rp >= t["min_rp"]:
            current = t
        else:
            break
    return current


def next_tier_for(rp: int) -> dict | None:
    """次の Tier（無ければ None=最上位）。"""
    for t in TIERS:
        if t["min_rp"] > rp:
            return t
    return None


def tier_progress(rp: int) -> float:
    """現在 Tier から次 Tier までの進捗（0.0–1.0 / 最上位は1.0 / 公開API）。"""
    cur = tier_for(rp)
    nxt = next_tier_for(rp)
    if not nxt:
        return 1.0
    span = nxt["min_rp"] - cur["min_rp"]
    return round((rp - cur["min_rp"]) / span, 4) if span > 0 else 0.0


def list_tiers() -> list[dict]:
    return [dict(t) for t in TIERS]
