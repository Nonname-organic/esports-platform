"""競技ランキング（グローバル/シーズン）のスキーマ（ADR-0015）。"""

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
    tournaments: int
    championships: int
    wins: int
    losses: int
    win_rate: float


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
