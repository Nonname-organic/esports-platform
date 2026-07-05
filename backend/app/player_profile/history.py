"""PlayerHistoryAggregator — 選手の大会履歴（read-only / ADR-0018）。

選手の所属チームが参加した完了大会の placement を report から集約する
（Ranking/Achievement と同一系のロジック。保存禁止）。
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RegistrationStatus, TournamentStatus
from app.models.team import Team, TeamMember
from app.models.tournament import Tournament, TournamentRegistration
from app.models.tournament_report import TournamentReport
from app.rankings.aggregator import _placements
from app.reports.aggregator import TournamentReportAggregator


class PlayerHistoryAggregator:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def history(self, player_id: uuid.UUID, *, limit: int = 30) -> list[dict]:
        team_ids = [t for t in (await self._db.execute(
            select(TeamMember.team_id).where(TeamMember.player_id == player_id)
        )).scalars().all()]
        if not team_ids:
            return []

        rows = (await self._db.execute(
            select(
                Tournament.id, Tournament.name, Tournament.game, Tournament.end_at,
                TournamentRegistration.team_id, Team.name,
            )
            .join(TournamentRegistration, TournamentRegistration.tournament_id == Tournament.id)
            .join(Team, Team.id == TournamentRegistration.team_id)
            .where(
                TournamentRegistration.team_id.in_(team_ids),
                TournamentRegistration.status == RegistrationStatus.APPROVED,
                Tournament.status == TournamentStatus.COMPLETED,
            )
            .order_by(Tournament.end_at.desc())
            .limit(limit)
        )).all()

        out: list[dict] = []
        for tid, tname, game, end_at, team_id, team_name in rows:
            data = await self._report_data(tid)
            placement = _placements(data).get(str(team_id)) if data else None
            out.append({
                "tournament_id": str(tid),
                "tournament_name": tname,
                "game": game.value if hasattr(game, "value") else str(game),
                "ended_at": end_at.isoformat() if end_at else None,
                "placement": placement,
                "team_name": team_name,
                "is_mvp": False,  # 将来 match_mvps 連携で精緻化
            })
        return out

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
