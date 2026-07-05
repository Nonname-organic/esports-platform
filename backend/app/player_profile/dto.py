"""Player Profile DTO（ADR-0018）。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PlayerAnalysis(BaseModel):
    provider: str
    play_style: str
    strengths: list[str]
    weaknesses: list[str]
    recommended_role: Optional[str] = None
    recommended_agent: Optional[str] = None
    consistency: int
    aggression: int
    summary: str


class PlayerHistoryItem(BaseModel):
    tournament_id: str
    tournament_name: str
    game: str
    ended_at: Optional[str] = None
    placement: Optional[str] = None
    team_name: Optional[str] = None
    is_mvp: bool = False
