"""OutboxRelay — domain_events(未dispatch) を拾い Dispatcher へ渡す（P0-4 / ADR-0001, 0007）。

- at-least-once: dispatch 成功で mark_dispatched、失敗で mark_failed（attempts++）。
- Terminal Failure（attempts >= MAX_DISPATCH_ATTEMPTS）は claim から自動除外され再試行されない。
- イベント単位で try/except し、1件の失敗が他イベントの処理を止めない。
- 既存 worker（sqs_consumer）の asyncio ループから run_once を回す。
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatcher import EventDispatcher
from app.events.envelope import EventEnvelope
from app.repositories.event import EventRepository

logger = structlog.get_logger()


class OutboxRelay:
    def __init__(self, dispatcher: EventDispatcher, worker_id: str):
        self._dispatcher = dispatcher
        self._worker_id = worker_id

    async def run_once(self, session: AsyncSession, limit: int = 100) -> int:
        """1バッチ処理。dispatch 成功件数を返す。"""
        repo = EventRepository(session)

        events = await repo.claim_undispatched(self._worker_id, limit)
        await session.commit()   # ロックを他worker/次サイクルへ確定
        if not events:
            return 0

        processed = 0
        for e in events:
            try:
                await self._dispatcher.dispatch(EventEnvelope.from_orm_row(e))
                await repo.mark_dispatched(e)
                await session.commit()
                processed += 1
            except Exception as ex:  # noqa: BLE001 — 1件失敗で全体を止めない
                await session.rollback()
                terminal = await repo.mark_failed(e, str(ex))
                await session.commit()
                if terminal:
                    logger.error(
                        "outbox_terminal_failure",
                        event_id=str(e.id), event_type=e.type,
                        attempts=e.dispatch_attempts, error=str(ex)[:200],
                    )
                else:
                    logger.warning(
                        "outbox_dispatch_failed",
                        event_id=str(e.id), event_type=e.type,
                        attempts=e.dispatch_attempts, error=str(ex)[:200],
                    )
        return processed
