"""Achievement Card スキーマ（読み取り専用の集約DTO）。

新しい実績テーブルではない。既存 Tournament / TournamentReport / Match /
Registration / CareerAggregationService から算出した結果の安定契約。
将来 Player / Tournament の実績カードでも同型を流用できるよう汎用に保つ。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RecentTitle(BaseModel):
    """カード内 Recent Titles の1件（順位 / 大会名 / 終了日）。"""
    placement: str            # "champion" | "runner_up" | "top4"
    tournament_id: str
    tournament_name: str
    ended_at: Optional[str]   # ISO8601 / 未定は null


class AchievementCardDTO(BaseModel):
    team_id: str
    team_name: str
    team_tag: str
    game: str

    # 順位実績（完了大会から算出・重複カウントしない排他バケット）
    championships: int        # 優勝(1位)
    runner_ups: int           # 準優勝(2位)
    top4: int                 # ベスト4(3〜4位相当)
    tournaments: int          # 参加した完了大会数

    # 勝敗（CareerAggregationService 再利用）
    matches: int
    wins: int
    losses: int
    win_rate: float

    # MVP（現状データ源未整備のため 0 / 将来 Aggregator へ追加）
    mvps: int = 0

    recent_titles: list[RecentTitle] = []

    founded_at: Optional[str] = None   # 発足日(Since)。Team.created_at 由来。
    updated_at: str                    # 集約実行時刻（materializedではないため都度更新）
