"""ReportConsumer — tournament.completed を受けてレポートを非同期生成（ADR-0009）。

OutboxRelay の InProcessDispatcher に register される（worker）。
自前セッションで Generator を呼び commit（Relay の Outbox 記録とは別Tx / P1-2 と同型・冪等 UPSERT）。
"""

from __future__ import annotations

import uuid

import structlog

from app.core.database import AsyncSessionLocal
from app.events.envelope import EventEnvelope
from app.events.registry import Ev
from app.reports.generator import TournamentReportGenerator

logger = structlog.get_logger()


class ReportConsumer:
    """tournament.completed のみ処理する。"""

    _HANDLED = {Ev.TOURNAMENT_COMPLETED}

    def handles(self, event_type: str) -> bool:
        return event_type in self._HANDLED

    async def handle(self, envelope: EventEnvelope) -> None:
        tournament_id = uuid.UUID(str(envelope.entity_id))
        async with AsyncSessionLocal() as db:
            generator = TournamentReportGenerator(db)
            report = await generator.generate(tournament_id)
            await db.commit()
            logger.info(
                "tournament_report_generated",
                tournament_id=str(tournament_id), version=report.version, event_id=envelope.event_id,
            )
