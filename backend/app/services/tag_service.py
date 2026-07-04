"""TagService — タグの唯一の窓口（機能⑤ / ADR-0014）。

slug 正規化・カタログ取得・エンティティへの付与/差し替え・タグ検索を集約。
未知 slug は既存タグから解決し、無ければ新規作成（正規化 slug）。
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.repositories.tag import TagRepository

VALID_ENTITY_TYPES = {"team", "tournament", "lfp", "lft"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(label: str) -> str:
    s = _SLUG_RE.sub("-", label.strip().lower()).strip("-")
    return s[:50] or "tag"


def _tag_dict(t: Tag) -> dict:
    return {"id": str(t.id), "slug": t.slug, "label": t.label, "category": t.category, "color": t.color}


class TagService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._repo = TagRepository(db)

    async def list_catalog(self, *, category: Optional[str] = None, q: Optional[str] = None) -> list[dict]:
        return [_tag_dict(t) for t in await self._repo.list_tags(category=category, q=q)]

    async def tags_for(self, entity_type: str, entity_id: uuid.UUID) -> list[dict]:
        return [_tag_dict(t) for t in await self._repo.tags_for_entity(entity_type, entity_id)]

    async def tags_for_many(self, entity_type: str, entity_ids: list[uuid.UUID]) -> dict[str, list[dict]]:
        m = await self._repo.tags_for_entities(entity_type, entity_ids)
        return {str(eid): [_tag_dict(t) for t in tags] for eid, tags in m.items()}

    async def _resolve_or_create(self, slugs_or_labels: list[str]) -> list[Tag]:
        """入力（slug or ラベル）を正規化し、既存タグ解決 or 新規作成。"""
        norm = [slugify(s) for s in slugs_or_labels if s and s.strip()]
        norm = list(dict.fromkeys(norm))  # 重複排除・順序維持
        if not norm:
            return []
        existing = {t.slug: t for t in await self._repo.get_by_slugs(norm)}
        result: list[Tag] = []
        for slug, original in zip(norm, [s for s in slugs_or_labels if s and s.strip()]):
            tag = existing.get(slug)
            if tag is None:
                tag = await self._repo.create_tag(slug=slug, label=original.strip()[:50])
                existing[slug] = tag
            result.append(tag)
        return result

    async def set_tags(self, entity_type: str, entity_id: uuid.UUID, tag_inputs: list[str]) -> list[dict]:
        """エンティティのタグを差し替え（付与権限は呼び出し側 Service が担保）。commit は呼び出し側。"""
        if entity_type not in VALID_ENTITY_TYPES:
            raise ValueError(f"invalid entity_type: {entity_type}")
        tags = await self._resolve_or_create(tag_inputs)
        await self._repo.set_entity_tags(entity_type, entity_id, [t.id for t in tags])
        return [_tag_dict(t) for t in tags]

    async def clear_entity(self, entity_type: str, entity_id: uuid.UUID) -> None:
        await self._repo.clear_entity(entity_type, entity_id)

    async def entities_with_tag(self, slug: str, entity_type: Optional[str] = None) -> list[dict]:
        rows = await self._repo.entities_with_tag(slugify(slug), entity_type)
        return [{"entity_type": r.entity_type, "entity_id": str(r.entity_id)} for r in rows]
