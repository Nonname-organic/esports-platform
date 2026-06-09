import uuid
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scout import ScoutProfile, RecruitmentPost, RecruitmentApplication
from app.repositories.base import BaseRepository


class ScoutProfileRepository(BaseRepository[ScoutProfile]):
    def __init__(self, db: AsyncSession):
        super().__init__(ScoutProfile, db)

    async def get_by_player(self, player_id: uuid.UUID) -> Optional[ScoutProfile]:
        return await self._db.scalar(
            select(ScoutProfile).where(ScoutProfile.player_id == player_id)
        )

    async def get_by_team(self, team_id: uuid.UUID) -> Optional[ScoutProfile]:
        return await self._db.scalar(
            select(ScoutProfile).where(ScoutProfile.team_id == team_id)
        )

    async def list_looking_players(self, limit: int = 50) -> list[ScoutProfile]:
        result = await self._db.execute(
            select(ScoutProfile)
            .where(ScoutProfile.type == "player", ScoutProfile.is_looking == True)
            .order_by(ScoutProfile.scout_rating.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())


class RecruitmentRepository(BaseRepository[RecruitmentPost]):
    def __init__(self, db: AsyncSession):
        super().__init__(RecruitmentPost, db)

    async def list_posts(
        self,
        post_type: Optional[str] = None,
        game: Optional[str] = None,
        is_open: bool = True,
        limit: int = 30,
        offset: int = 0,
    ) -> list[RecruitmentPost]:
        q = select(RecruitmentPost)
        if is_open:
            q = q.where(RecruitmentPost.is_open == True)
        if post_type:
            q = q.where(RecruitmentPost.post_type == post_type)
        if game:
            q = q.where(RecruitmentPost.game == game)
        q = q.order_by(RecruitmentPost.created_at.desc()).limit(limit).offset(offset)
        result = await self._db.execute(q)
        return list(result.scalars().all())

    async def count_applications(self, post_id: uuid.UUID) -> int:
        return await self._db.scalar(
            select(func.count(RecruitmentApplication.id)).where(
                RecruitmentApplication.post_id == post_id
            )
        ) or 0


class ApplicationRepository(BaseRepository[RecruitmentApplication]):
    def __init__(self, db: AsyncSession):
        super().__init__(RecruitmentApplication, db)

    async def get_existing(
        self, post_id: uuid.UUID, applicant_id: uuid.UUID
    ) -> Optional[RecruitmentApplication]:
        return await self._db.scalar(
            select(RecruitmentApplication).where(
                RecruitmentApplication.post_id == post_id,
                RecruitmentApplication.applicant_id == applicant_id,
            )
        )

    async def list_for_post(self, post_id: uuid.UUID) -> list[RecruitmentApplication]:
        result = await self._db.execute(
            select(RecruitmentApplication)
            .where(RecruitmentApplication.post_id == post_id)
            .order_by(RecruitmentApplication.created_at.desc())
        )
        return list(result.scalars().all())
