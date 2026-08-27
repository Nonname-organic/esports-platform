import uuid

from fastapi import APIRouter, File, UploadFile

from app.core.dependencies import Cache, CurrentUser, DBSession, OrganizerUser
from app.core.exceptions import ValidationError
from app.schemas.common import Response
from app.schemas.match import (
    BanPickCreate,
    GamePlayerStatsUpdate,
    MatchDetail,
    MatchResultCreate,
    ScoreUpdate,
)
from app.services.match import MatchService
from app.services.scoreboard_import import ScoreboardImportService

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


@router.post("/{match_id}/games/{game_number}/player-stats", status_code=204)
async def save_game_player_stats(
    match_id: uuid.UUID,
    game_number: int,
    data: GamePlayerStatsUpdate,
    db: DBSession,
    cache: Cache,
    current_user: OrganizerUser,
):
    """1マップ分のスコアと選手成績を保存する（スコアボード取り込みの確定先）"""
    service = MatchService(db, cache)
    await service.save_game_player_stats(match_id, game_number, data, current_user)


@router.post("/{match_id}/scoreboard-ocr")
async def parse_scoreboard(
    match_id: uuid.UUID,
    db: DBSession,
    current_user: OrganizerUser,
    file: UploadFile = File(...),
):
    """
    VALORANTのスコアボード画像を解析して選手成績の候補を返す。

    この時点では保存せず、運営が内容を確認・修正したうえで
    /matches/{id}/result へ登録する。
    """
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise ValidationError("PNG・JPEG・WebP のスクリーンショットのみ対応しています")

    contents = await file.read()
    service = ScoreboardImportService(db)
    return {"data": await service.parse(match_id, contents), "meta": None}


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
