"""StatsService — 公開ライブ統計（Live Experience / 読み取り専用）。

Live Status Bar と Statistics Card 用の集約値を安価な COUNT で算出する。
Redis に短TTL(15秒)でキャッシュし「ライブ感」と負荷のバランスを取る。
新テーブルは作らない（Growth Policy: Additive・read-only）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.models.domain_event import DomainEvent
from app.models.enums import MatchStatus, TournamentStatus
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament

STATS_CACHE_TTL = 15          # 秒（ライブ感優先の短TTL）
ONLINE_WINDOW_MIN = 30        # オンライン概算の対象窓（分）


class StatsService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    async def overview(self) -> dict:
        cache_key = "stats:overview"
        cached = await self._cache.get(cache_key)
        if cached:
            return cached  # type: ignore[return-value]
        data = await self._compute()
        await self._cache.set(cache_key, data, ttl=STATS_CACHE_TTL)
        return data

    async def _compute(self) -> dict:
        ongoing_tournaments = await self._db.scalar(
            select(func.count()).select_from(Tournament).where(Tournament.status == TournamentStatus.ONGOING)
        )
        ongoing_matches = await self._db.scalar(
            select(func.count()).select_from(Match).where(Match.status == MatchStatus.ONGOING)
        )
        total_tournaments = await self._db.scalar(select(func.count()).select_from(Tournament))
        total_teams = await self._db.scalar(select(func.count()).select_from(Team))
        total_players = await self._db.scalar(select(func.count()).select_from(Player))
        total_matches = await self._db.scalar(select(func.count()).select_from(Match))

        return {
            "live": {
                "ongoing_tournaments": int(ongoing_tournaments or 0),
                "ongoing_matches": int(ongoing_matches or 0),
                "online_participants": await self._estimate_online(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "totals": {
                "tournaments": int(total_tournaments or 0),
                "teams": int(total_teams or 0),
                "players": int(total_players or 0),
                "matches": int(total_matches or 0),
            },
        }

    async def _estimate_online(self) -> int:
        """直近アクティブなactor数の概算（domain_events の distinct actor / 過去30分）。

        リアルなプレゼンス基盤は持たないため近似値。0 の場合はフロント側が
        Mock フォールバックで賑わいを補完できる（数値の出所はどちらでも良い設計）。
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=ONLINE_WINDOW_MIN)
        count = await self._db.scalar(
            select(func.count(func.distinct(DomainEvent.actor_id)))
            .where(DomainEvent.actor_id.isnot(None), DomainEvent.created_at >= cutoff)
        )
        return int(count or 0)
