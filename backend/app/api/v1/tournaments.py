import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.dependencies import Cache, CurrentUser, DBSession, OrganizerUser
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.enums import GameType, RegistrationStatus, TournamentStatus
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.tournament import (
    BracketResponse,
    RegistrationInfo,
    RegistrationRequest,
    StatusChangeRequest,
    TournamentCreate,
    TournamentDetail,
    TournamentSummary,
    TournamentUpdate,
)
from app.services.tournament import TournamentService

router = APIRouter(prefix="/tournaments", tags=["大会管理"])


def _build_detail(tournament, count: int) -> TournamentDetail:
    return TournamentDetail(
        id=str(tournament.id),
        name=tournament.name,
        game=tournament.game,
        format=tournament.format,
        status=tournament.status,
        max_teams=tournament.max_teams,
        registered_teams=count,
        start_at=tournament.start_at,
        prize_pool=tournament.prize_pool,
        banner_url=tournament.banner_url,
        description=tournament.description,
        rules=tournament.rules,
        organizer_id=str(tournament.organizer_id),
        registration_start_at=tournament.registration_start_at,
        registration_end_at=tournament.registration_end_at,
        check_in_start_at=tournament.check_in_start_at,
        end_at=tournament.end_at,
        require_check_in=tournament.require_check_in,
        created_at=tournament.created_at,
        updated_at=tournament.updated_at,
    )


@router.get("", response_model=ListResponse[TournamentSummary])
async def list_tournaments(
    db: DBSession,
    cache: Cache,
    game: GameType | None = Query(default=None),
    status: TournamentStatus | None = Query(default=None),
    cursor: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    service = TournamentService(db, cache)
    tournaments, has_next = await service._repo.list_by_game_status(
        game=game, status=status, limit=limit, cursor=cursor
    )

    items = []
    for t in tournaments:
        count = await service._repo.get_registered_teams_count(t.id)
        items.append(TournamentSummary(
            id=str(t.id),
            name=t.name,
            game=t.game,
            format=t.format,
            status=t.status,
            max_teams=t.max_teams,
            registered_teams=count,
            start_at=t.start_at,
            prize_pool=t.prize_pool,
            banner_url=t.banner_url,
        ))

    next_cursor = str(tournaments[-1].id) if has_next and tournaments else None
    return ListResponse(data=items, meta=Meta(has_next=has_next, cursor=next_cursor))


@router.get("/mine", response_model=Response[list[TournamentDetail]])
async def list_my_tournaments(db: DBSession, cache: Cache, current_user: OrganizerUser):
    """主催者自身の大会一覧"""
    service = TournamentService(db, cache)
    tournaments = await service.get_my_tournaments(current_user.id)
    items = []
    for t in tournaments:
        count = await service._repo.get_registered_teams_count(t.id)
        items.append(_build_detail(t, count))
    return Response(data=items, meta=None)


@router.post("", response_model=Response[TournamentDetail], status_code=201)
async def create_tournament(
    data: TournamentCreate, db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    service = TournamentService(db, cache)
    tournament = await service.create(data, current_user)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(data=_build_detail(tournament, count), meta=None)


@router.get("/{tournament_id}", response_model=Response[TournamentDetail])
async def get_tournament(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    service = TournamentService(db, cache)
    tournament = await service.get_detail(tournament_id)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(data=_build_detail(tournament, count), meta=None)


@router.patch("/{tournament_id}", response_model=Response[TournamentDetail])
async def update_tournament(
    tournament_id: uuid.UUID, data: TournamentUpdate,
    db: DBSession, cache: Cache, current_user: CurrentUser,
):
    service = TournamentService(db, cache)
    tournament = await service.update(tournament_id, data, current_user)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(data=_build_detail(tournament, count), meta=None)


@router.patch("/{tournament_id}/status", response_model=Response[TournamentDetail])
async def change_tournament_status(
    tournament_id: uuid.UUID, data: StatusChangeRequest,
    db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    """大会ステータス変更（ドラフト→受付開始→受付終了→開催中→完了）"""
    service = TournamentService(db, cache)
    tournament = await service.change_status(tournament_id, data.status, current_user)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(data=_build_detail(tournament, count), meta=None)


@router.delete("/{tournament_id}", status_code=204)
async def delete_tournament(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    service = TournamentService(db, cache)
    await service.delete(tournament_id, current_user)


@router.get("/{tournament_id}/registrations", response_model=Response[list[RegistrationInfo]])
async def list_registrations(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    """大会への参加申請一覧（主催者専用）"""
    service = TournamentService(db, cache)
    regs = await service.list_registrations(tournament_id, current_user)
    items = [
        RegistrationInfo(
            id=str(r.id),
            team_id=str(r.team_id),
            team_name=r.team.name if r.team else "Unknown",
            team_tag=r.team.tag if r.team else "???",
            team_logo_url=r.team.logo_url if r.team else None,
            status=r.status.value,
            notes=r.notes,
            registered_at=r.registered_at,
        )
        for r in regs
    ]
    return Response(data=items, meta=None)


@router.patch("/{tournament_id}/registrations/{registration_id}", response_model=Response[RegistrationInfo])
async def update_registration(
    tournament_id: uuid.UUID,
    registration_id: uuid.UUID,
    status: RegistrationStatus = Query(..., description="approve/reject/pending"),
    db: DBSession = ...,
    cache: Cache = ...,
    current_user: OrganizerUser = ...,
):
    """参加申請を承認・却下"""
    service = TournamentService(db, cache)
    reg = await service.update_registration(tournament_id, registration_id, status, current_user)
    return Response(
        data=RegistrationInfo(
            id=str(reg.id),
            team_id=str(reg.team_id),
            team_name=reg.team.name if reg.team else "Unknown",
            team_tag=reg.team.tag if reg.team else "???",
            team_logo_url=reg.team.logo_url if reg.team else None,
            status=reg.status.value,
            notes=reg.notes,
            registered_at=reg.registered_at,
        ),
        meta=None,
    )


@router.post("/{tournament_id}/register", status_code=204)
async def register_team(
    tournament_id: uuid.UUID, data: RegistrationRequest,
    db: DBSession, cache: Cache, current_user: CurrentUser,
):
    service = TournamentService(db, cache)
    await service.register_team(tournament_id, uuid.UUID(data.team_id), data.notes)


async def _user_registration(db, tournament_id: uuid.UUID, user):
    """ログインユーザーの所属チームの、この大会への登録を解決。"""
    from app.models.player import Player
    from app.models.team import TeamMember
    from app.schemas.tournament import RegistrationInfo  # noqa: F401 (型参照回避)

    player = (await db.execute(select(Player).where(Player.user_id == user.id))).scalar_one_or_none()
    if not player:
        return None
    team_ids = (
        await db.execute(
            select(TeamMember.team_id).where(
                TeamMember.player_id == player.id, TeamMember.left_at.is_(None)
            )
        )
    ).scalars().all()
    if not team_ids:
        return None
    from app.models.tournament import TournamentRegistration
    return (
        await db.execute(
            select(TournamentRegistration).where(
                TournamentRegistration.tournament_id == tournament_id,
                TournamentRegistration.team_id.in_(team_ids),
            )
        )
    ).scalar_one_or_none()


@router.get("/{tournament_id}/check-in/me")
async def my_check_in(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
):
    """自分のチームのチェックイン状態（フロントのボタン表示用）。"""
    reg = await _user_registration(db, tournament_id, current_user)
    if not reg:
        return {"data": {"registered": False, "checked_in": False}}
    return {"data": {
        "registered": True,
        "approved": reg.status == RegistrationStatus.APPROVED,
        "checked_in": reg.checked_in_at is not None,
        "team_id": str(reg.team_id),
        "checked_in_at": reg.checked_in_at.isoformat() if reg.checked_in_at else None,
    }}


@router.post("/{tournament_id}/check-in", status_code=200)
async def check_in(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
):
    """Webからチェックイン（自分の所属チームの登録を出席にする）。"""
    reg = await _user_registration(db, tournament_id, current_user)
    if not reg:
        raise NotFoundError("登録", "この大会にあなたのチームは登録されていません")
    if reg.status != RegistrationStatus.APPROVED:
        raise BusinessRuleError("承認済みの登録のみチェックインできます")
    reg.checked_in_at = datetime.now(timezone.utc)
    reg.checked_in_via = "web"
    await db.flush()
    return {"data": {"checked_in": True, "team_id": str(reg.team_id),
                     "checked_in_at": reg.checked_in_at.isoformat()}}


@router.post("/{tournament_id}/bracket", response_model=Response[BracketResponse], status_code=201)
async def generate_bracket(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
):
    service = TournamentService(db, cache)
    bracket = await service.generate_bracket(tournament_id, current_user)
    return Response(data=bracket)


@router.get("/{tournament_id}/bracket", response_model=Response[BracketResponse])
async def get_bracket(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    service = TournamentService(db, cache)
    bracket = await service.get_bracket(tournament_id)
    return Response(data=bracket)
