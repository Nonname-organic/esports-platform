import uuid

from fastapi import APIRouter

from app.core.dependencies import Cache, CurrentUser, DBSession, OrganizerUser
from app.schemas.common import Response
from app.schemas.match import (
    BanPickCreate,
    MatchDetail,
    MatchResultCreate,
    ScoreUpdate,
)
from app.services.match import MatchService

router = APIRouter(prefix="/matches", tags=["試合管理"])


@router.get("/{match_id}", response_model=Response[MatchDetail])
async def get_match(match_id: uuid.UUID, db: DBSession, cache: Cache):
    service = MatchService(db, cache)
    detail = await service.get_detail(match_id)
    return Response(data=detail)


@router.patch("/{match_id}/start", status_code=204)
async def start_match(
    match_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    current_user: OrganizerUser,
):
    service = MatchService(db, cache)
    await service.start_match(match_id, current_user)


@router.post("/{match_id}/games/{game_number}/score", status_code=204)
async def update_game_score(
    match_id: uuid.UUID,
    game_number: int,
    data: ScoreUpdate,
    db: DBSession,
    cache: Cache,
    current_user: OrganizerUser,
):
    service = MatchService(db, cache)
    await service.update_game_score(match_id, game_number, data, current_user)


@router.post("/{match_id}/banpick", status_code=204)
async def register_ban_pick(
    match_id: uuid.UUID,
    data: BanPickCreate,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = MatchService(db, cache)
    await service.register_ban_pick(match_id, data)


@router.post("/{match_id}/result", status_code=204)
async def register_result(
    match_id: uuid.UUID,
    data: MatchResultCreate,
    db: DBSession,
    cache: Cache,
    current_user: OrganizerUser,
):
    service = MatchService(db, cache)
    await service.register_result(match_id, data, current_user)
