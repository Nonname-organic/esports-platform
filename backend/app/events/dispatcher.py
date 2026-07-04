"""Event Dispatcher — OutboxRelay からイベントを consumer へ fan-out する（ADR-0002）。

現在は InProcessDispatcher のみ実装。将来 SQS/Redis/Kafka Dispatcher へ差し替え可能なよう
`EventDispatcher` Protocol にのみ依存させる（Relay は具象実装を知らない）。

consumer は冪等（idempotency_key で重複排除）である前提。1イベントの dispatch 中に
consumer が失敗したら dispatch 全体を失敗として送出し、Relay が再試行する（at-least-once）。
「全体を止めない」は Relay 側のイベント単位 try/except で担保する。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import structlog

from app.events.envelope import EventEnvelope

logger = structlog.get_logger()


@runtime_checkable
class EventConsumer(Protocol):
    """イベントの受け手（通知・レポート等）。冪等であること。"""

    def handles(self, event_type: str) -> bool: ...
    async def handle(self, envelope: EventEnvelope) -> None: ...


class EventDispatcher(Protocol):
    """イベントを consumer へ配送する契約。差し替え点はこの1インターフェースのみ。"""

    async def dispatch(self, envelope: EventEnvelope) -> None: ...


class InProcessDispatcher:
    """同一プロセス内で consumer へ直接 fan-out する現行実装。"""

    def __init__(self, consumers: list[EventConsumer] | None = None):
        self._consumers: list[EventConsumer] = list(consumers or [])

    def register(self, consumer: EventConsumer) -> None:
        self._consumers.append(consumer)

    async def dispatch(self, envelope: EventEnvelope) -> None:
        matched = [c for c in self._consumers if c.handles(envelope.type)]
        if not matched:
            # consumer 不在は正常（純監査など）。dispatch 済みとして扱う。
            logger.debug("event_no_consumer", event_type=envelope.type, event_id=envelope.event_id)
            return
        # いずれかの consumer が失敗したら例外を送出（Relay が再試行）。
        for consumer in matched:
            await consumer.handle(envelope)
