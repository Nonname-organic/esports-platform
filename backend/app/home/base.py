"""Home Widget の基盤（ADR-0019）。

各 Widget は `WidgetProvider` を実装し registry に登録する。HomeAggregator は
registry を集約するだけ（Provider 追加時に HomeAggregator は不変）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache


@dataclass
class HomeContext:
    """パーソナライズ文脈（現状は game のみ / 将来 rank・region・team_ids・tags を追加）。"""
    user_id: Optional[str] = None
    game: Optional[str] = None

    @property
    def cache_suffix(self) -> str:
        return f"{self.user_id or 'anon'}:{self.game or 'all'}"


class WidgetProvider(Protocol):
    """ホーム Widget の唯一IF。key と build のみ。"""
    key: str
    async def build(self, db: AsyncSession, cache: RedisCache, ctx: HomeContext) -> object: ...
