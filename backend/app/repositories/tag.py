"""TagRepository — tags / taggables の永続化（ADR-0014）。

一覧のタグは親IDリストで一括取得（Data Loader / N+1回避）。
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, Taggable


class TagRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── タグカタログ ──────────────────────────────────────────────────────
    async def list_tags(self, *, category: Optional[str] = None, q: Optional[str] = None, limit: int = 100) -> list[Tag]:
        query = select(Tag)
        if category:
            query = query.where(Tag.category == category)
        if q:
            query = query.where(Tag.label.ilike(f"%{q}%"))
        query = query.order_by(Tag.label).limit(limit)
        return list((await self._db.execute(query)).scalars().all())

    async def get_by_slug(self, slug: str) -> Optional[Tag]:
        return await self._db.scalar(select(Tag).where(Tag.slug == slug))

    async def get_by_slugs(self, slugs: list[str]) -> list[Tag]:
        if not slugs:
            return []
        return list((await self._db.execute(select(Tag).where(Tag.slug.in_(slugs)))).scalars().all())

    async def create_tag(self, *, slug: str, label: str, category: Optional[str] = None, color: Optional[str] = None) -> Tag:
        tag = Tag(id=uuid.uuid4(), slug=slug, label=label, category=category, color=color)
        self._db.add(tag)
        await self._db.flush()
        return tag

    # ── エンティティのタグ ────────────────────────────────────────────────
    async def tags_for_entity(self, entity_type: str, entity_id: uuid.UUID) -> list[Tag]:
        rows = (await self._db.execute(
            select(Tag).join(Taggable, Taggable.tag_id == Tag.id)
            .where(Taggable.entity_type == entity_type, Taggable.entity_id == entity_id)
            .order_by(Tag.label)
        )).scalars().all()
        return list(rows)

    async def tags_for_entities(self, entity_type: str, entity_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Tag]]:
        """複数エンティティのタグを1クエリで一括取得（N+1回避 / Data Loader）。"""
        if not entity_ids:
            return {}
        rows = (await self._db.execute(
            select(Taggable.entity_id, Tag)
            .join(Tag, Tag.id == Taggable.tag_id)
            .where(Taggable.entity_type == entity_type, Taggable.entity_id.in_(entity_ids))
            .order_by(Tag.label)
        )).all()
        out: dict[uuid.UUID, list[Tag]] = {eid: [] for eid in entity_ids}
        for eid, tag in rows:
            out.setdefault(eid, []).append(tag)
        return out

    async def set_entity_tags(self, entity_type: str, entity_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> None:
        """エンティティのタグを差し替え（追加/削除を算出）。commit は呼び出し側。"""
        current = set((await self._db.execute(
            select(Taggable.tag_id).where(
                Taggable.entity_type == entity_type, Taggable.entity_id == entity_id)
        )).scalars().all())
        want = set(tag_ids)
        to_add = want - current
        to_remove = current - want
        for tid in to_add:
            self._db.add(Taggable(tag_id=tid, entity_type=entity_type, entity_id=entity_id))
        if to_remove:
            await self._db.execute(
                delete(Taggable).where(
                    Taggable.entity_type == entity_type,
                    Taggable.entity_id == entity_id,
                    Taggable.tag_id.in_(to_remove),
                )
            )
        await self._db.flush()

    async def clear_entity(self, entity_type: str, entity_id: uuid.UUID) -> None:
        """エンティティ削除時の孤児掃除（ADR-0014）。"""
        await self._db.execute(
            delete(Taggable).where(Taggable.entity_type == entity_type, Taggable.entity_id == entity_id)
        )

    async def entities_with_tag(self, slug: str, entity_type: Optional[str] = None, limit: int = 50) -> list[Taggable]:
        q = select(Taggable).join(Tag, Tag.id == Taggable.tag_id).where(Tag.slug == slug)
        if entity_type:
            q = q.where(Taggable.entity_type == entity_type)
        q = q.limit(limit)
        return list((await self._db.execute(q)).scalars().all())
