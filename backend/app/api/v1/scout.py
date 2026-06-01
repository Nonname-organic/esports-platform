"""
Scout Platform API
- プレイヤー検索
- チーム募集掲載
- レーティング参照
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.schemas.common import ListResponse, Meta, Response

router = APIRouter(prefix="/scout", tags=["スカウト"])


@router.get("/players")
async def search_players(
    db: DBSession,
    cache: Cache,
    game: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    min_rating: Optional[float] = Query(default=None),
    max_rating: Optional[float] = Query(default=None),
    availability: Optional[str] = Query(default=None),
    looking_for_team: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0),
):
    """プレイヤースカウト検索"""
    from app.models.player import Player
    from app.models.tournament import scout_profiles, player_ratings

    # TODO: 実装時にJOINクエリで検索
    # 現在はシンプルなフィルター
    q = select(Player)
    if game:
        q = q.where(Player.game == game)
    if region:
        q = q.where(Player.region == region)
    if role:
        q = q.where(Player.main_role == role)

    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    players = list(result.scalars().all())

    return {
        "data": [
            {
                "id": str(p.id),
                "in_game_name": p.in_game_name,
                "game": p.game.value,
                "main_role": p.main_role,
                "region": p.region,
                "discord_id": p.discord_id,
            }
            for p in players
        ],
        "meta": {"total": len(players), "has_next": False, "cursor": None},
    }


@router.get("/teams")
async def search_teams(
    db: DBSession,
    game: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    looking_for_players: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
):
    """チームスカウト検索"""
    from app.models.team import Team

    q = select(Team).where(Team.is_active == True)
    if game:
        q = q.where(Team.game == game)
    q = q.limit(limit)

    result = await db.execute(q)
    teams = list(result.scalars().all())

    return {
        "data": [
            {
                "id": str(t.id),
                "name": t.name,
                "tag": t.tag,
                "game": t.game.value,
                "logo_url": t.logo_url,
            }
            for t in teams
        ],
        "meta": {"total": len(teams), "has_next": False, "cursor": None},
    }


@router.get("/ratings/{player_id}")
async def get_player_rating(player_id: uuid.UUID, db: DBSession):
    """プレイヤーレーティング取得"""
    # player_ratings テーブルから取得
    return {
        "data": {
            "player_id": str(player_id),
            "ratings": [],
            "history": [],
        }
    }


@router.post("/profiles")
async def upsert_scout_profile(
    db: DBSession,
    current_user: CurrentUser,
    data: dict,
):
    """スカウトプロフィール登録・更新"""
    return {"data": {"message": "Scout profile updated"}}
