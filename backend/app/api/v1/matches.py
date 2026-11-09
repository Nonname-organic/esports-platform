import uuid
from typing import Any

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import Cache, CurrentUser, DBSession, OrganizerUser
from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import MatchStatus
from app.models.match import Match
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.match import (
    BanPickCreate,
    GamePlayerStatsUpdate,
    MatchDetail,
    MatchResultCreate,
    MatchSummary,
    ScoreUpdate,
)
from app.services.match import MatchService, ensure_can_manage_match
from app.services.scoreboard_import import ScoreboardImportService

router = APIRouter(prefix="/matches", tags=["試合管理"])


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
    await service.register_ban_pick(match_id, data, current_user)


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

    # OCR は重い処理なので、権限を確かめてから画像を読む
    match = await db.get(Match, match_id)
    if not match:
        raise NotFoundError("試合", str(match_id))
    await ensure_can_manage_match(db, match, current_user)

    contents = await file.read()
    # nginx の上限は添付ファイル（10MB）に合わせてあるため、OCR は従来どおり 5MB で止める
    if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError("スクリーンショットは5MB以下にしてください")
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


# ── 対戦チームによる結果報告 → 相手チームの確認（主催者は従来どおり直接確定できる） ──
class ResultReportBody(BaseModel):
    winner_id: uuid.UUID


class DisputeBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


@router.get("/{match_id}/report", response_model=Response[dict[str, Any]])
async def get_result_report(
    match_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
) -> Response[dict[str, Any]]:
    """報告の状態と、ログイン中の利用者ができる操作（報告・確認・異議）。"""
    from app.services.match_report import MatchReportService
    return Response(data=await MatchReportService(db, cache).state(match_id, current_user))


@router.post("/{match_id}/report", response_model=Response[dict[str, str]])
async def report_result(
    match_id: uuid.UUID, data: ResultReportBody, db: DBSession, cache: Cache, current_user: CurrentUser,
) -> Response[dict[str, str]]:
    """対戦チームのオーナー・キャプテンが結果を報告する（主催者は即確定）。"""
    from app.services.match_report import MatchReportService
    status = await MatchReportService(db, cache).report(match_id, data.winner_id, current_user)
    return Response(data={"status": status})


@router.post("/{match_id}/report/confirm", response_model=Response[dict[str, str]])
async def confirm_result_report(
    match_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
) -> Response[dict[str, str]]:
    """相手チーム（または主催者）が報告内容を確認し、結果を確定する。"""
    from app.services.match_report import MatchReportService
    return Response(data={"status": await MatchReportService(db, cache).confirm(match_id, current_user)})


@router.post("/{match_id}/report/dispute", response_model=Response[dict[str, str]])
async def dispute_result_report(
    match_id: uuid.UUID, data: DisputeBody, db: DBSession, cache: Cache, current_user: CurrentUser,
) -> Response[dict[str, str]]:
    """相手チームが報告に異議を出す。主催者が結果の登録で裁定する。"""
    from app.services.match_report import MatchReportService
    status = await MatchReportService(db, cache).dispute(match_id, data.reason, current_user)
    return Response(data={"status": status})


@router.post("/{match_id}/reopen", status_code=204)
async def reopen_match(match_id: uuid.UUID, db: DBSession, cache: Cache, current_user: OrganizerUser) -> None:
    """確定済みの結果を取り消して進行中へ戻す（次の試合が未開始の場合のみ）。"""
    await MatchService(db, cache).reopen_match(match_id, current_user)
