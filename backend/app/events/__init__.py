"""Event 基盤（Envelope / Registry / Service / Dispatcher）。

P0-2: EventEnvelope（本パッケージの契約）+ trace_id 基盤。
P0-3 以降で Registry / EventService.emit / Outbox / Dispatcher を追加する。
設計: docs/architecture/PHASED_ARCHITECTURE.md
"""

from app.events.envelope import ActorType, EventEnvelope, Visibility

__all__ = ["EventEnvelope", "ActorType", "Visibility"]
