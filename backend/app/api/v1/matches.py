import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from app.core.config import settings
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


class ReasonBody(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


@router.patch("/{match_id}/start", status_code=204)
async def start_match(
    match_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    current_user: MatchOrganizer,
    data: ReasonBody | None = None,
):
    """開始で出場登録を固定する（RC4）。スターターが足りないチームがあれば理由が必須（D14）。"""
    service = MatchService(db, cache)
    await service.start_match(match_id, current_user, reason=data.reason if data else None)


class ForfeitBody(BaseModel):
    winner_id: uuid.UUID
    reason: str = Field(..., min_length=1, max_length=1000)


@router.post("/{match_id}/forfeit", status_code=204)
async def record_forfeit_without_start(match_id: uuid.UUID, data: ForfeitBody, db: DBSession, cache: Cache,
                                       current_user: MatchOrganizer) -> None:
    """開始を経ない不戦勝（RC4 Q04）。出場登録を固定せず、マップ・成績は記録しない。"""
    await MatchService(db, cache).record_forfeit_without_start(match_id, data.winner_id, data.reason, current_user)


class LineupBody(BaseModel):
    starters: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    bench: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    reason: str | None = Field(default=None, max_length=1000)


@router.get("/{match_id}/lineups", response_model=Response[dict[str, Any]])
async def get_lineups(match_id: uuid.UUID, db: DBSession, cache: Cache):
    """両チームの出場登録と、マップごとの実出場（D18: 試合を見られる人に公開）。"""
    from app.services.match import lock_match  # noqa: F401  (読み取りだけ。ロックは取らない)
    from app.models.match import Match
    from app.services.roster import LineupService
    match = await db.get(Match, match_id)
    if match is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("試合", str(match_id))
    return Response(data=await LineupService(db, cache).get_lineups(match))


@router.put("/{match_id}/lineups/{team_id}", response_model=Response[dict[str, Any]])
async def put_lineup(match_id: uuid.UUID, team_id: uuid.UUID, data: LineupBody, db: DBSession, cache: Cache,
                     current_user: CurrentUser):
    """出場登録を置き換える。開始の前はチーム、固定の後は主催者（理由つき）、完了の後は管理者の訂正。"""
    from app.services.match import lock_match
    from app.services.roster import LineupService
    match = await lock_match(db, match_id)
    if match is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("試合", str(match_id))
    service = LineupService(db, cache)
    await service.put_lineup(match, team_id, data.starters, data.bench, data.reason, current_user)
    return Response(data=await service.get_lineups(match))


class SubstitutionBody(BaseModel):
    team_id: uuid.UUID
    kind: str = Field(..., pattern="^(between_maps|mid_map|fill)$")
    out_player_id: uuid.UUID | None = None
    in_player_id: uuid.UUID
    at_round: int | None = Field(default=None, ge=0, le=99)
    reason: str | None = Field(default=None, max_length=1000)


def _sub(s) -> dict[str, Any]:
    return {"id": str(s.id), "game_number": s.game_number, "team_id": str(s.team_id), "kind": s.kind,
            "out_lineup_entry_id": str(s.out_lineup_entry_id) if s.out_lineup_entry_id else None,
            "in_lineup_entry_id": str(s.in_lineup_entry_id), "at_round": s.at_round, "reason": s.reason,
            "status": s.status, "requested_at": s.requested_at, "approved_at": s.approved_at}


@router.get("/{match_id}/substitutions", response_model=Response[list[dict[str, Any]]])
async def list_substitutions(match_id: uuid.UUID, db: DBSession, cache: Cache):
    from sqlalchemy import select
    from app.models.roster import MatchSubstitution
    rows = (await db.execute(select(MatchSubstitution).where(MatchSubstitution.match_id == match_id)
                             .order_by(MatchSubstitution.game_number, MatchSubstitution.requested_at))).scalars()
    return Response(data=[_sub(s) for s in rows])


@router.post("/{match_id}/games/{game_number}/substitutions", response_model=Response[dict[str, Any]], status_code=201)
async def submit_substitution(match_id: uuid.UUID, game_number: int, data: SubstitutionBody, db: DBSession,
                              cache: Cache, current_user: CurrentUser):
    """交代の申請（キャプテン・オーナー）か、主催者・管理者の理由つきの直接の記録（D27）。"""
    from app.services.match import lock_match
    from app.services.roster import SubstitutionService
    if not 1 <= game_number <= 9:
        raise ValidationError("マップの番号が不正です")
    match = await lock_match(db, match_id)
    if match is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("試合", str(match_id))
    sub = await SubstitutionService(db, cache).submit(
        match, game_number=game_number, team_id=data.team_id, kind=data.kind, out_player_id=data.out_player_id,
        in_player_id=data.in_player_id, at_round=data.at_round, reason=data.reason, user=current_user)
    return Response(data=_sub(sub))


@router.post("/{match_id}/substitutions/{sub_id}/{decision}", response_model=Response[dict[str, Any]])
async def decide_substitution(match_id: uuid.UUID, sub_id: uuid.UUID, decision: str, db: DBSession, cache: Cache,
                              current_user: MatchOrganizer):
    from app.services.match import lock_match
    from app.services.roster import SubstitutionService
    if decision not in ("approve", "reject"):
        raise ValidationError("approve か reject を指定してください")
    match = await lock_match(db, match_id)
    if match is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("試合", str(match_id))
    sub = await SubstitutionService(db, cache).decide(match, sub_id, decision == "approve", current_user)
    return Response(data=_sub(sub))


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

    # nginx の上限は添付ファイル（10MB）に合わせてあるため、OCR は従来どおり 5MB で止める。
    # 上限を1バイト超える分までしか読まない（大きなファイルを丸ごとメモリに載せない）
    contents = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
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
async def reopen_match(match_id: uuid.UUID, db: DBSession, cache: Cache, current_user: MatchOrganizer,
                       data: ReasonBody | None = None) -> None:
    """確定済みの結果を取り消して進行中へ戻す（次の試合が未開始の場合のみ）。

    RC4: 大会の完了の後は管理者だけが理由つきで行える（Q15）。バイと legacy の大会は再開しない。
    """
    await MatchService(db, cache).reopen_match(match_id, current_user, reason=data.reason if data else None)
