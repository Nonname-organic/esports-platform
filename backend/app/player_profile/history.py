"""PlayerHistoryAggregator — 選手の大会履歴（read-only / ADR-0018）。

選手の所属チームが参加した完了大会の placement を report から集約する
（Ranking/Achievement と同一系のロジック。保存禁止）。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.models.tournament_report import TournamentReport
from app.reports.aggregator import TournamentReportAggregator


class PlayerHistoryAggregator:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def history(self, player_id: uuid.UUID, *, limit: int = 30) -> list[dict]:
        """RC4（S8-2）: 帰属の関数で決めた大会だけを出す（名簿の大会は実出場、既存の大会は所属の期間）。"""
        from app.rankings.attribution import attribution_entries
        entries = await attribution_entries(self._db, self._report_data, season="all", player_ids={player_id})
        entries.sort(key=lambda e: e["ended_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        entries = entries[:limit]
        names = dict((await self._db.execute(select(Team.id, Team.name).where(
            Team.id.in_({uuid.UUID(e["team_id"]) for e in entries} or {uuid.uuid4()})))).all())
        return [{
            "tournament_id": e["tournament_id"],
            "tournament_name": e["tournament_name"],
            "game": e["game"],
            "ended_at": e["ended_at"].isoformat() if e["ended_at"] else None,
            "placement": e["label"],
            "team_name": names.get(uuid.UUID(e["team_id"])),
            "is_mvp": False,  # 将来 match_mvps 連携で精緻化
        } for e in entries]

    async def _report_data(self, tournament_id: uuid.UUID) -> Optional[dict]:
        report = await self._db.scalar(
            select(TournamentReport).where(TournamentReport.tournament_id == tournament_id)
        )
        if report and report.data:
            return report.data
        try:
            return await TournamentReportAggregator(self._db).aggregate(tournament_id)
        except Exception:
            return None
