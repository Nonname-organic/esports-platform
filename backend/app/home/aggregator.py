"""HomeAggregator — ホーム全体の Read Model を Provider から集約するだけ（ADR-0019）。

Provider を追加しても本クラスは変更しない（registry.PROVIDERS を回すのみ）。保存禁止。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import RedisCache
from app.home.base import HomeContext
from app.home.registry import PROVIDERS, get_provider

HOME_TTL = 60  # 秒


class HomeAggregator:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    async def home(self, ctx: HomeContext) -> dict:
        key = f"home:{ctx.cache_suffix}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        result: dict = {}
        for provider in PROVIDERS:
            result[provider.key] = await provider.build(self._db, self._cache, ctx)
        result["updated_at"] = datetime.now(timezone.utc).isoformat()

        await self._cache.set(key, result, ttl=HOME_TTL)
        return result

    async def widget(self, key: str, ctx: HomeContext) -> object:
        provider = get_provider(key)
        if provider is None:
            raise NotFoundError("ホームWidget", key)
        return await provider.build(self._db, self._cache, ctx)
