import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from app.core.dependencies import Cache, CurrentUser, DBSession, OrganizerUser
from app.core.exceptions import ValidationError
from app.models.enums import MatchStatus
from app.models.user import User
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.match import (
    BanPickCreate,
    GamePlayerStatsUpdate,
    MatchDetail,
    MatchResultCreate,
    MatchSummary,
    ScoreUpdate,
)
from app.services.match import MatchService
from app.services.scoreboard_import import ScoreboardImportService

router = APIRouter(prefix="/matches", tags=["試合管理"])


async def _require_match_organizer(
    match_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    current_user: OrganizerUser,
) -> User:
    """この試合の運営だけを通す。ADMIN か、その試合が属する大会の主催者。

    ロールしか見ない OrganizerUser では、別の大会の主催者が他人の試合を
    操作できてしまう。試合を変える route と、処理の重い取り込み route は
    こちらを使う。Dependency なので route 本体より先に走り、拒否された
    リクエストはサービス層にも OCR にも届かない。
    """
    await MatchService(db, cache).require_organizer_authority(match_id, current_user)
    return current_user


MatchOrganizer = Annotated[User, Depends(_require_match_organizer)]


@router.get("", response_model=ListResponse[MatchSummary])
async def list_matches(
    tournament_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    status: MatchStatus | None = None,
):
    """大会の試合一覧。試合タブとブラケット表示が使う。"""
    service = MatchService(db, cache)
    matches = await service.list_by_tournament(tournament_id, status)
    return ListResponse(
        data=matches,
        meta=Meta(total=len(matches), cursor=None, has_next=False),
    )


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
    current_user: MatchOrganizer,
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
    current_user: MatchOrganizer,
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
    await service.register_ban_pick(match_id, data, current_user)


@router.post("/{match_id}/games/{game_number}/player-stats", status_code=204)
async def save_game_player_stats(
    match_id: uuid.UUID,
    game_number: int,
    data: GamePlayerStatsUpdate,
    db: DBSession,
    cache: Cache,
    current_user: MatchOrganizer,
):
    """1マップ分のスコアと選手成績を保存する（スコアボード取り込みの確定先）"""
    service = MatchService(db, cache)
    await service.save_game_player_stats(match_id, game_number, data, current_user)


@router.post("/{match_id}/scoreboard-ocr")
async def parse_scoreboard(
    match_id: uuid.UUID,
    db: DBSession,
    current_user: MatchOrganizer,
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
    current_user: MatchOrganizer,
):
    service = MatchService(db, cache)
    await service.register_result(match_id, data, current_user)


class StreamUrlUpdate(BaseModel):
    """配信試合の指定。空文字・null で解除する。"""
    stream_url: str | None = Field(default=None, max_length=500)


@router.patch("/{match_id}/stream", response_model=Response[dict])
async def set_stream_url(
    match_id: uuid.UUID,
    data: StreamUrlUpdate,
    db: DBSession,
    cache: Cache,
    current_user: OrganizerUser,
):
    """この試合を配信対象にする（配信URLを設定・解除する）。

    どの試合を配信するかはブラケット上で示したいので、試合側に持たせる。
    """
    service = MatchService(db, cache)
    url = await service.set_stream_url(match_id, data.stream_url, current_user)
    return Response(data={"match_id": str(match_id), "stream_url": url}, meta=None)
