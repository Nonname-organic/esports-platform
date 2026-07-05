"""競技ランキング（グローバル/シーズン）のスキーマ（ADR-0015）。

DTO は tier 構造を直接持たず、tier_key/label/color（SSOT 由来）と progress のみを返す。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TierInfo(BaseModel):
    key: str
    label: str
    min_rp: int
    color: str
    icon: str


class LeaderboardEntry(BaseModel):
    rank: int
    team_id: str
    team_name: str
    team_tag: str
    team_logo_url: Optional[str] = None
    game: str
    rp: int
    tier_key: str
    tier_label: str
    tier_color: str
    progress: float = 0.0
    tournaments: int
    championships: int
    runner_ups: int = 0
    top4: int = 0
    wins: int
    losses: int
    win_rate: float


class RankHistoryItem(BaseModel):
    tournament_id: str
    tournament_name: str
    ended_at: Optional[str] = None
    placement: str
    rp_gained: int
    cumulative_rp: int


class RankCard(BaseModel):
    team_id: str
    team_name: str
    team_tag: str
    game: str
    rp: int
    rank: Optional[int] = None
    total_ranked: int
    tier_key: str
    tier_label: str
    tier_color: str
    next_tier_label: Optional[str] = None
    next_tier_rp: Optional[int] = None
    progress: float
    championships: int
    tournaments: int
    history: list[RankHistoryItem] = []
