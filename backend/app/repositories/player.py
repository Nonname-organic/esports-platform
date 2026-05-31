import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.repositories.base import BaseRepository


class PlayerRepository(BaseRepository[Player]):
    def __init__(self, db: AsyncSession):
        super().__init__(Player, db)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Player]:
        result = await self._db.execute(
            select(Player).where(Player.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_riot_puuid(self, puuid: str) -> Optional[Player]:
        result = await self._db.execute(
            select(Player).where(Player.riot_puuid == puuid)
        )
        return result.scalar_one_or_none()

    async def list_players(
        self,
        game: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[uuid.UUID] = None,
    ) -> tuple[list[Player], bool]:
        q = select(Player).order_by(Player.created_at.desc())
        if game:
            q = q.where(Player.game == game)
        if region:
            q = q.where(Player.region == region)
        if cursor:
            ref = await self.get_by_id(cursor)
            if ref:
                q = q.where(Player.created_at < ref.created_at)
        q = q.limit(limit + 1)
        result = await self._db.execute(q)
        rows = list(result.scalars().all())
        has_next = len(rows) > limit
        return rows[:limit], has_next
