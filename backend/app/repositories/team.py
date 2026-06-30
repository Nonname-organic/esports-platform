import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import GameType, MemberRole
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    def __init__(self, db: AsyncSession):
        super().__init__(Team, db)

    async def list_teams(
        self,
        game: Optional[GameType] = None,
        limit: int = 20,
        cursor: Optional[uuid.UUID] = None,
    ) -> tuple[list[Team], bool]:
        q = select(Team).where(Team.is_active == True).order_by(Team.created_at.desc())
        if game:
            q = q.where(Team.game == game)
        if cursor:
            ref = await self.get_by_id(cursor)
            if ref:
                q = q.where(Team.created_at < ref.created_at)
        q = q.limit(limit + 1)
        result = await self._db.execute(q)
        rows = list(result.scalars().all())
        has_next = len(rows) > limit
        return rows[:limit], has_next

    async def list_my_teams(self, user_id: uuid.UUID) -> list[Team]:
        """オーナーまたはメンバーとして所属しているチーム一覧"""
        owned = select(Team.id).where(Team.owner_id == user_id, Team.is_active == True)
        member_of = (
            select(TeamMember.team_id)
            .join(Player, Player.id == TeamMember.player_id)
            .where(Player.user_id == user_id, TeamMember.left_at.is_(None))
        )
        q = (
            select(Team)
            .where(Team.is_active == True, or_(Team.id.in_(owned), Team.id.in_(member_of)))
            .order_by(Team.created_at.desc())
        )
        result = await self._db.execute(q)
        return list(result.scalars().unique().all())

    async def get_with_members(self, team_id: uuid.UUID) -> Optional[Team]:
        result = await self._db.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members))
        )
        return result.scalar_one_or_none()

    async def exists_name(self, name: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        q = select(Team).where(Team.name == name, Team.is_active == True)
        if exclude_id:
            q = q.where(Team.id != exclude_id)
        return bool((await self._db.execute(q)).scalar_one_or_none())

    async def exists_tag(self, tag: str, game: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        q = select(Team).where(Team.tag == tag, Team.game == game, Team.is_active == True)
        if exclude_id:
            q = q.where(Team.id != exclude_id)
        return bool((await self._db.execute(q)).scalar_one_or_none())


class TeamMemberRepository(BaseRepository[TeamMember]):
    def __init__(self, db: AsyncSession):
        super().__init__(TeamMember, db)

    async def get_active_members(self, team_id: uuid.UUID) -> list[TeamMember]:
        result = await self._db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.left_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def find_active(self, team_id: uuid.UUID, player_id: uuid.UUID) -> Optional[TeamMember]:
        result = await self._db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.player_id == player_id,
                TeamMember.left_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_player(self, player_id: uuid.UUID) -> list[TeamMember]:
        result = await self._db.execute(
            select(TeamMember).where(
                TeamMember.player_id == player_id,
                TeamMember.left_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def soft_delete(self, member: TeamMember) -> None:
        member.left_at = datetime.now(timezone.utc)
        await self._db.flush()
