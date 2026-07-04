"""Report Generator — 組み立て/保存の責務（ADR-0009）。

Generator は **集計しない**（Aggregator に委譲）。data を受け取り markdown を組み立て UPSERT するだけ。
ReportGenerator は interface。将来 PlayerReportGenerator / SeasonReportGenerator を register で追加。
"""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.reports.aggregator import TournamentReportAggregator
from app.repositories.tournament_report import TournamentReportRepository


class ReportGenerator(Protocol):
    kind: str
    async def generate(self, target_id: uuid.UUID) -> object: ...


def _render_markdown(data: dict) -> str:
    """data を Markdown へ組み立て（集計はしない）。"""
    t = data.get("tournament", {})
    lines = [
        f"# {t.get('name', '大会')} 終了レポート",
        "",
        f"- ゲーム: {t.get('game', '—')}",
        f"- 形式: {t.get('format', '—')}",
        f"- 参加チーム数: {data.get('participant_count', 0)}",
        f"- 試合数: {data.get('match_count', 0)}",
        "",
        "## 結果",
    ]
    champ = data.get("champion")
    runner = data.get("runner_up")
    lines.append(f"- 優勝: **{champ['team_name']}**" if champ else "- 優勝: —")
    lines.append(f"- 準優勝: {runner['team_name']}" if runner else "- 準優勝: —")
    mw = data.get("most_wins")
    if mw:
        lines.append(f"- 最多勝利: {mw['team_name']}（{mw['wins']}勝）")

    standings = data.get("standings") or []
    if standings:
        lines += ["", "## 順位", "", "| # | チーム | 勝 | 敗 | 勝率 |", "|---|---|---|---|---|"]
        for i, s in enumerate(standings, 1):
            lines.append(f"| {i} | {s['team_name']} | {s['wins']} | {s['losses']} | {s['win_rate']*100:.0f}% |")
    return "\n".join(lines)


class TournamentReportGenerator:
    """大会終了レポートの Generator。集計は Aggregator、保存は Repository。"""
    kind = "tournament"

    def __init__(self, db: AsyncSession):
        self._db = db
        self._aggregator = TournamentReportAggregator(db)
        self._repo = TournamentReportRepository(db)

    async def generate(self, target_id: uuid.UUID):
        data = await self._aggregator.aggregate(target_id)   # 集計は Aggregator に委譲
        markdown = _render_markdown(data)                     # 組み立てのみ
        report = await self._repo.upsert(target_id, data, markdown)  # 冪等保存（commit は呼び出し側）
        return report
