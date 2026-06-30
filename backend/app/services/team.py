import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AlreadyExistsError,
    ForbiddenError,
    NotFoundError,
)
from app.core.redis import RedisCache
from app.models.enums import MemberRole
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.models.user import User
from app.repositories.team import TeamMemberRepository, TeamRepository
from app.schemas.team import AddMemberRequest, TeamCreate, TeamUpdate


class TeamService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._repo = TeamRepository(db)
        self._member_repo = TeamMemberRepository(db)

    # ── 権限チェック ──────────────────────────────────────────────────────────

    def _is_owner(self, team: Team, user: User) -> bool:
        return team.owner_id == user.id or user.role.value == "admin"

    async def _get_member_role(self, team_id: uuid.UUID, user_id: uuid.UUID) -> MemberRole | None:
        """ユーザーのチーム内ロールを返す（非メンバーはNone）"""
        player = await self._db.scalar(select(Player).where(Player.user_id == user_id))
        if not player:
            return None
        member = await self._member_repo.find_active(team_id, player.id)
        return member.role if member else None

    async def _require_owner_or_captain(self, team: Team, user: User) -> None:
        if self._is_owner(team, user):
            return
        role = await self._get_member_role(team.id, user.id)
        if role not in (MemberRole.CAPTAIN,):
            raise ForbiddenError("この操作はチームオーナーまたはキャプテンのみ実行できます")

    # ── チーム CRUD ───────────────────────────────────────────────────────────

    async def list_teams(self, game=None, limit=20, cursor=None):
        return await self._repo.list_teams(game=game, limit=limit, cursor=cursor)

    async def get_my_teams(self, user_id: uuid.UUID) -> list[Team]:
        return await self._repo.list_my_teams(user_id)

    async def get_team(self, team_id: uuid.UUID) -> Team:
        team = await self._repo.get_by_id(team_id)
        if not team or not team.is_active:
            raise NotFoundError("チームが見つかりません")
        return team

    async def create_team(self, data: TeamCreate, owner: User) -> Team:
        if await self._repo.exists_name(data.name):
            raise AlreadyExistsError("このチーム名は既に使用されています")
        if await self._repo.exists_tag(data.tag, data.game.value):
            raise AlreadyExistsError("このタグはこのゲームで既に使用されています")

        team = await self._repo.create(
            owner_id=owner.id,
            name=data.name,
            tag=data.tag.upper(),
            game=data.game,
            description=data.description,
            country=data.country,
            logo_url=data.logo_url,
            banner_url=data.banner_url,
            twitter_handle=data.twitter_handle,
            is_active=True,
        )

        # オーナーをキャプテンとして自動追加
        player = await self._db.scalar(select(Player).where(Player.user_id == owner.id))
        if player:
            await self._member_repo.create(
                team_id=team.id,
                player_id=player.id,
                role=MemberRole.CAPTAIN,
                joined_at=datetime.now(timezone.utc),
            )

        return team

    async def update_team(self, team_id: uuid.UUID, data: TeamUpdate, current_user: User) -> Team:
        team = await self.get_team(team_id)
        await self._require_owner_or_captain(team, current_user)

        updates = data.model_dump(exclude_none=True)
        if "name" in updates and updates["name"] != team.name:
            if await self._repo.exists_name(updates["name"], exclude_id=team_id):
                raise AlreadyExistsError("このチーム名は既に使用されています")
        if "tag" in updates:
            updates["tag"] = updates["tag"].upper()

        return await self._repo.update(team, **updates)

    async def delete_team(self, team_id: uuid.UUID, current_user: User) -> None:
        team = await self.get_team(team_id)
        if not self._is_owner(team, current_user):
            raise ForbiddenError("チームの削除はオーナーのみ実行できます")
        await self._repo.update(team, is_active=False)

    # ── メンバー管理 ──────────────────────────────────────────────────────────

    async def get_members(self, team_id: uuid.UUID) -> list[dict]:
        await self.get_team(team_id)
        members = await self._member_repo.get_active_members(team_id)

        result = []
        for m in members:
            player = await self._db.scalar(select(Player).where(Player.id == m.player_id))
            user = None
            if player and player.user_id:
                user = await self._db.scalar(select(User).where(User.id == player.user_id))
            result.append({
                "id": m.id,
                "player_id": m.player_id,
                "user_id": player.user_id if player else None,
                "in_game_name": player.in_game_name if player else None,
                "username": user.username if user else None,
                "avatar_url": user.avatar_url if user else None,
                "role": m.role.value,
                "jersey_number": m.jersey_number,
                "joined_at": m.joined_at,
                "is_active": True,
            })
        return result

    async def add_member(
        self, team_id: uuid.UUID, data: AddMemberRequest, current_user: User
    ) -> dict:
        team = await self.get_team(team_id)
        await self._require_owner_or_captain(team, current_user)

        # ユーザー名でユーザーを検索
        target_user = await self._db.scalar(
            select(User).where(User.username == data.username, User.is_active == True)
        )
        if not target_user:
            raise NotFoundError(f"ユーザー '{data.username}' が見つかりません")

        # Playerプロフィールを取得
        player = await self._db.scalar(
            select(Player).where(Player.user_id == target_user.id)
        )
        if not player:
            raise NotFoundError("このユーザーはプレイヤープロフィールを持っていません")

        # 既存メンバーチェック
        existing = await self._member_repo.find_active(team_id, player.id)
        if existing:
            raise AlreadyExistsError("このユーザーは既にチームメンバーです")

        member = await self._member_repo.create(
            team_id=team_id,
            player_id=player.id,
            role=data.role,
            jersey_number=data.jersey_number,
            joined_at=datetime.now(timezone.utc),
        )

        return {
            "id": member.id,
            "player_id": player.id,
            "user_id": target_user.id,
            "in_game_name": player.in_game_name,
            "username": target_user.username,
            "avatar_url": target_user.avatar_url,
            "role": member.role.value,
            "jersey_number": member.jersey_number,
            "joined_at": member.joined_at,
            "is_active": True,
        }

    async def remove_member(
        self, team_id: uuid.UUID, player_id: uuid.UUID, current_user: User
    ) -> None:
        team = await self.get_team(team_id)
        member = await self._member_repo.find_active(team_id, player_id)
        if not member:
            raise NotFoundError("メンバーが見つかりません")

        # オーナー・キャプテン・本人のみ削除可
        current_player = await self._db.scalar(
            select(Player).where(Player.user_id == current_user.id)
        )
        is_self = current_player and current_player.id == player_id

        if not self._is_owner(team, current_user) and not is_self:
            role = await self._get_member_role(team_id, current_user.id)
            if role != MemberRole.CAPTAIN:
                raise ForbiddenError("この操作を行う権限がありません")

        # オーナーは脱退不可
        owner_player = await self._db.scalar(
            select(Player).where(Player.user_id == team.owner_id)
        )
        if owner_player and owner_player.id == player_id and not current_user.role.value == "admin":
            raise ForbiddenError("チームオーナーは脱退できません。先に所有権を移転してください")

        await self._member_repo.soft_delete(member)
