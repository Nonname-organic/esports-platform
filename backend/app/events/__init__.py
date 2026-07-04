"""Event 基盤（Envelope / Registry / Service / Dispatcher）。

- P0-2: EventEnvelope + trace_id 基盤
- P0-3: Event Registry(SSOT) + EventService.emit（保存のみ）+ DomainEvent
- P0-4: Transactional Outbox（OutboxRelay）+ EventDispatcher（予定）
設計: docs/architecture/PHASED_ARCHITECTURE.md / ADR-0001, 0005
"""

from app.events.envelope import ActorType, EventEnvelope, Visibility
from app.events.registry import Ev, EventSpec, UnknownEventError, get_spec, is_registered
from app.events.service import EventService

__all__ = [
    "EventEnvelope",
    "ActorType",
    "Visibility",
    "EventService",
    "Ev",
    "EventSpec",
    "UnknownEventError",
    "get_spec",
    "is_registered",
]
