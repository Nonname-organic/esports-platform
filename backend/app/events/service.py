"""EventService — イベントの保存のみを責務とする（ADR-0001 / PHASED §2）。

責務:
  - EventEnvelope を Registry で検証し、DomainEvent として **同一トランザクションで保存**する。
非責務（持たない）:
  - 通知 / Discord / レポート生成などの副作用は一切行わない。
    → それらは P0-4 の OutboxRelay → EventDispatcher → Consumer が担う。

使い方（呼び出し元のドメインServiceと同じ AsyncSession を渡す = 同一Tx）:
    env = EventEnvelope.build(type=Ev.TOURNAMENT_STATUS_CHANGED, entity_type="tournament",
                              entity_id=t.id, producer="tournament",
                              before={"status": old}, after={"status": new})
    await EventService(self._db).emit(env)
    # commit は呼び出し元のドメイン処理と一括で行われる（原子性）
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.events import registry
from app.events.envelope import EventEnvelope
from app.models.domain_event import DomainEvent
from app.repositories.event import EventRepository


class EventService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = EventRepository(session)

    async def emit(self, envelope: EventEnvelope) -> DomainEvent:
        """Envelope を検証し DomainEvent を保存する（保存のみ・commit しない）。"""
        spec = registry.get_spec(envelope.type)          # 未登録は UnknownEventError

        # payload schema 検証（Registry に定義がある場合のみ・段階導入）
        if spec.payload is not None and envelope.after is not None:
            spec.payload.model_validate(envelope.after)

        # Registry を SSOT とし、version / visibility は Registry の値で確定する
        # （型ごとに一貫させ、呼び出し側の指定ミスを排除）
        envelope = envelope.model_copy(update={
            "event_version": spec.version,
            "visibility": spec.visibility,
        })

        row = DomainEvent.from_envelope(envelope, needs_dispatch=spec.dispatch)
        await self._repo.add(row)                        # session.add + flush（commit しない）
        return row
