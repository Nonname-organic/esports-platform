"""Search の共通契約（ADR-0013）: SearchHit / SearchProvider / SearchRegistry。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SearchHit:
    type: str                       # "team" | "player" | "tournament" | "match"
    id: str
    label: str                      # 主表示（名前）
    sub: Optional[str] = None       # 補助（タグ/ゲーム/日時等）
    image_url: Optional[str] = None
    url: str = ""                   # 遷移先
    score: float = 0.0              # 0..1 に正規化（Provider の責務）

    def to_dict(self) -> dict:
        return {
            "type": self.type, "id": self.id, "label": self.label,
            "sub": self.sub, "image_url": self.image_url, "url": self.url,
            "score": round(self.score, 4),
        }


class SearchProvider(Protocol):
    name: str
    async def search(self, db: AsyncSession, q: str, limit: int) -> list[SearchHit]: ...


class SearchRegistry:
    def __init__(self, providers: list[SearchProvider] | None = None):
        self._providers: list[SearchProvider] = list(providers or [])

    def register(self, provider: SearchProvider) -> None:
        self._providers.append(provider)

    def enabled(self, types: Optional[list[str]]) -> list[SearchProvider]:
        if not types:
            return list(self._providers)
        want = set(types)
        return [p for p in self._providers if p.name in want]

    def names(self) -> list[str]:
        return [p.name for p in self._providers]
