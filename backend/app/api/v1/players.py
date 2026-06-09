import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.player import GAME_ROLES, PlayerCreate, PlayerSchema, PlayerUpdate
from app.schemas.career import PlayerCareerSchema, AchievementItem, RatingPoint
from app.services.player import PlayerService
from app.services.career_service import CareerAggregationService

router = APIRouter(prefix="/players", tags=["プレイヤー管理"])


# ── Career / Achievements / Ratings ─────────────────────────────────────────
@router.get("/{player_id}/career", response_model=Response[PlayerCareerSchema])
async def get_player_career(player_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    career = await service.get_player_career(player_id)
    return Response(data=PlayerCareerSchema(**career), meta=None)


@router.get("/{player_id}/achievements", response_model=Response[list[AchievementItem]])
async def get_player_achievements(player_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    achievements = await service.get_player_achievements(player_id)
    return Response(data=[AchievementItem(**a) for a in achievements], meta=None)


@router.get("/{player_id}/rating-history", response_model=Response[list[RatingPoint]])
async def get_player_rating_history(
    player_id: uuid.UUID, db: DBSession, cache: Cache,
    game: str = Query(default="VALORANT"),
):
    service = CareerAggregationService(db, cache)
    history = await service.get_player_rating_history(player_id, game)
    return Response(data=[RatingPoint(**h) for h in history], meta=None)


@router.get("/roles", tags=["プレイヤー管理"])
async def get_game_roles():
    """ゲーム別ロール一覧（フロントエンドのセレクター用）"""
    return {"data": GAME_ROLES}


@router.get("", response_model=ListResponse[PlayerSchema])
async def list_players(
    db: DBSession,
    cache: Cache,
    game: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    cursor: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    service = PlayerService(db, cache)
    players, has_next = await service.list_players(
        game=game, region=region, limit=limit, cursor=cursor
    )
    next_cursor = str(players[-1].id) if has_next and players else None
    return ListResponse(
        data=players,
        meta=Meta(total=None, cursor=next_cursor, has_next=has_next),
    )


@router.get("/me", response_model=Response[Optional[PlayerSchema]])
async def get_my_player(db: DBSession, cache: Cache, current_user: CurrentUser):
    """自分のプレイヤープロフィールを取得（なければnull）"""
    service = PlayerService(db, cache)
    player = await service.get_my_player(current_user.id)
    return Response(data=player, meta=None)


@router.post("", response_model=Response[PlayerSchema], status_code=201)
async def create_player(
    data: PlayerCreate, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = PlayerService(db, cache)
    player = await service.create_player(data, current_user)
    return Response(data=player, meta=None)


@router.get("/{player_id}", response_model=Response[PlayerSchema])
async def get_player(player_id: uuid.UUID, db: DBSession, cache: Cache):
    service = PlayerService(db, cache)
    player = await service.get_player(player_id)
    return Response(data=player, meta=None)


@router.patch("/{player_id}", response_model=Response[PlayerSchema])
async def update_player(
    player_id: uuid.UUID,
    data: PlayerUpdate,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = PlayerService(db, cache)
    player = await service.update_player(player_id, data, current_user)
    return Response(data=player, meta=None)


@router.delete("/{player_id}", status_code=204)
async def delete_player(
    player_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = PlayerService(db, cache)
    await service.delete_player(player_id, current_user)
