"""SearchService — Provider を束ねて並列実行し、type別に集約する（ADR-0013）。

SearchService はエンティティ固有ロジックを持たない（Provider へ委譲）。
返却は SearchResultDTO（type別グルーピング）。
"""

from __future__ import annotations

import asyncio
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.search.base import SearchRegistry
from app.search.providers import DEFAULT_PROVIDERS

logger = structlog.get_logger()

# 既定の登録（新対象は DEFAULT_PROVIDERS に足すだけ）
_registry = SearchRegistry(DEFAULT_PROVIDERS)


class SearchService:
    def __init__(self, db: AsyncSession, registry: Optional[SearchRegistry] = None):
        self._db = db
        self._registry = registry or _registry

    async def search(self, q: str, *, types: Optional[list[str]] = None, limit: int = 8) -> dict:
        """SearchResultDTO: {players, teams, tournaments, matches} を返す。"""
        result: dict[str, list[dict]] = {"players": [], "teams": [], "tournaments": [], "matches": []}
        query = (q or "").strip()
        if len(query) < 2:
            return result

        providers = self._registry.enabled(types)
        gathered = await asyncio.gather(
            *[p.search(self._db, query, limit) for p in providers],
            return_exceptions=True,
        )
        for provider, res in zip(providers, gathered):
            if isinstance(res, Exception):  # 1 Provider の失敗は隔離
                logger.warning("search_provider_failed", provider=provider.name, error=str(res)[:200])
                continue
            for hit in res:
                bucket = f"{hit.type}s"  # team->teams, player->players ...
                if bucket in result:
                    result[bucket].append(hit.to_dict())
        return result
