"""ActivityService — 公開活動タイムライン（機能② / ADR-0011）。

domain_events の visibility='public' のみを list_activity 経由で読み、表示用 DTO に整形する。
表示タイトルは type + metadata から組み立てる（before/after は返さない = 監査の関心事）。
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.registry import Ev
from app.models.domain_event import DomainEvent
from app.repositories.event import EventRepository


# type → 表示タイトルの組み立て（metadata で format）。未定義は type をそのまま表示。
def _title(e: DomainEvent) -> str:
    m = e.event_metadata or {}
    if e.type == Ev.PLAYER_TEAM_JOINED:
        return f"「{m.get('team_name', 'チーム')}」に加入しました"
    if e.type == Ev.TOURNAMENT_COMPLETED:
        return f"「{m.get('tournament_name', '大会')}」が終了しました"
    return e.type


class ActivityService:
    def __init__(self, db: AsyncSession):
        self._repo = EventRepository(db)

    async def player_activity(self, player_id: uuid.UUID, *, limit: int = 30, offset: int = 0) -> list[dict]:
        """プレイヤーに関する公開活動（新しい順）。"""
        events = await self._repo.list_activity(
            entity_type="player", entity_id=player_id, limit=limit, offset=offset,
        )
        return [self._to_item(e) for e in events]

    @staticmethod
    def _to_item(e: DomainEvent) -> dict:
        return {
            "id": str(e.id),
            "type": e.type,
            "title": _title(e),
            "metadata": e.event_metadata or {},
            "occurred_at": (e.occurred_at or e.created_at).isoformat(),
        }
