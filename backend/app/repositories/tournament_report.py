"""TournamentReportRepository — レポートの取得・UPSERT（3層維持）。"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tournament_report import TournamentReport
from app.repositories.base import BaseRepository


class TournamentReportRepository(BaseRepository[TournamentReport]):
    def __init__(self, db: AsyncSession):
        super().__init__(TournamentReport, db)

    async def get_by_tournament(self, tournament_id: uuid.UUID) -> Optional[TournamentReport]:
        return await self._db.scalar(
            select(TournamentReport).where(TournamentReport.tournament_id == tournament_id)
        )

    async def upsert(self, tournament_id: uuid.UUID, data: dict, markdown: Optional[str]) -> TournamentReport:
        """冪等 UPSERT。既存があれば version++ で上書き（ADR-0009）。commit は呼び出し側。"""
        existing = await self.get_by_tournament(tournament_id)
        now = datetime.now(timezone.utc)
        if existing:
            existing.data = data
            existing.markdown = markdown
            existing.version = existing.version + 1
            existing.generated_at = now
            await self._db.flush()
            return existing
        report = TournamentReport(
            id=uuid.uuid4(), tournament_id=tournament_id,
            data=data, markdown=markdown, version=1, generated_at=now,
        )
        self._db.add(report)
        await self._db.flush()
        return report
