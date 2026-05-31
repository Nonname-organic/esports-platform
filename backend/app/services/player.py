"""
Player Service - Riot API連携を考慮した設計

## 将来的なRiot API統合フロー
1. ユーザーがRiot ID (Name#TAG) を登録
2. `verify_riot_id()` が Riot API に問い合わせて PUUID を取得
3. PUUID を元に詳細データ（ランク、過去試合等）を自動取得
4. `riot_puuid` が設定されると「認証済み」プレイヤーになる

## 現在の実装
- Riot IDの形式検証のみ（API呼び出しなし）
- riot_puuid は手動設定または将来のタスクキューで設定
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, ForbiddenError, NotFoundError
from app.core.redis import RedisCache
from app.models.player import Player
from app.models.team import TeamMember
from app.models.user import User
from app.repositories.player import PlayerRepository
from app.schemas.player import PlayerCreate, PlayerSchema, PlayerUpdate, RiotIdInput


class PlayerService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._repo = PlayerRepository(db)

    def _to_schema(self, player: Player, user: Optional[User] = None) -> PlayerSchema:
        return PlayerSchema(
            id=player.id,
            user_id=player.user_id,
            in_game_name=player.in_game_name,
            riot_id=player.riot_id,
            riot_gamename=player.riot_gamename,
            riot_tagline=player.riot_tagline,
            riot_puuid=player.riot_puuid,
            game=player.game.value,
            rank=player.rank,
            main_role=player.main_role,
            sub_roles=player.sub_roles or [],
            agent_pool=player.agent_pool or [],
            discord_id=player.discord_id,
            region=player.region,
            nationality=player.nationality,
            real_name=player.real_name,
            bio=player.bio,
            twitter_handle=player.twitter_handle,
            twitch_handle=player.twitch_handle,
            created_at=player.created_at,
            updated_at=player.updated_at,
            username=user.username if user else None,
            avatar_url=user.avatar_url if user else None,
        )

    async def get_player(self, player_id: uuid.UUID) -> PlayerSchema:
        player = await self._repo.get_by_id(player_id)
        if not player:
            raise NotFoundError("プレイヤーが見つかりません")
        user = None
        if player.user_id:
            user = await self._db.scalar(select(User).where(User.id == player.user_id))
        return self._to_schema(player, user)

    async def get_my_player(self, user_id: uuid.UUID) -> Optional[PlayerSchema]:
        player = await self._repo.get_by_user_id(user_id)
        if not player:
            return None
        user = await self._db.scalar(select(User).where(User.id == user_id))
        return self._to_schema(player, user)

    async def list_players(self, game=None, region=None, limit=20, cursor=None):
        players, has_next = await self._repo.list_players(
            game=game, region=region, limit=limit, cursor=cursor
        )
        result = []
        for p in players:
            user = None
            if p.user_id:
                user = await self._db.scalar(select(User).where(User.id == p.user_id))
            result.append(self._to_schema(p, user))
        return result, has_next

    async def create_player(self, data: PlayerCreate, current_user: User) -> PlayerSchema:
        # 1アカウント1プレイヤーのみ
        existing = await self._repo.get_by_user_id(current_user.id)
        if existing:
            raise AlreadyExistsError("このアカウントには既にプレイヤープロフィールが存在します")

        # Riot ID のパース
        riot_input = RiotIdInput(riot_id=data.riot_id)
        in_game_name, riot_gamename, riot_tagline = riot_input.parse()

        player = await self._repo.create(
            user_id=current_user.id,
            in_game_name=in_game_name,
            riot_gamename=riot_gamename,
            riot_tagline=riot_tagline,
            game=data.game,
            main_role=data.main_role,
            sub_roles=data.sub_roles or [],
            agent_pool=data.agent_pool or [],
            discord_id=data.discord_id,
            rank=data.rank,
            region=data.region,
            bio=data.bio,
            real_name=data.real_name,
            nationality=data.nationality,
            twitter_handle=data.twitter_handle,
            twitch_handle=data.twitch_handle,
        )

        # TODO: 将来的にここでRiot API検証タスクをキューに追加
        # await queue.enqueue("verify_riot_id", player_id=str(player.id))

        return self._to_schema(player, current_user)

    async def update_player(
        self, player_id: uuid.UUID, data: PlayerUpdate, current_user: User
    ) -> PlayerSchema:
        player = await self._repo.get_by_id(player_id)
        if not player:
            raise NotFoundError("プレイヤーが見つかりません")
        if player.user_id != current_user.id and current_user.role.value != "admin":
            raise ForbiddenError("他のプレイヤーのプロフィールは編集できません")

        updates = data.model_dump(exclude_none=True)

        if "riot_id" in updates:
            riot_input = RiotIdInput(riot_id=updates.pop("riot_id"))
            ign, gamename, tagline = riot_input.parse()
            updates["in_game_name"] = ign
            updates["riot_gamename"] = gamename
            updates["riot_tagline"] = tagline
            # Riot IDが変更されたらPUUIDをリセット（再検証が必要）
            updates["riot_puuid"] = None

        updated = await self._repo.update(player, **updates)
        return self._to_schema(updated, current_user)

    async def delete_player(self, player_id: uuid.UUID, current_user: User) -> None:
        player = await self._repo.get_by_id(player_id)
        if not player:
            raise NotFoundError("プレイヤーが見つかりません")
        if player.user_id != current_user.id and current_user.role.value != "admin":
            raise ForbiddenError("このプレイヤープロフィールを削除する権限がありません")
        await self._repo.delete(player)
