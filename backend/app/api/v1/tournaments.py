import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, CurrentUser, DBSession, OrganizerUser
from app.models.enums import GameType, TournamentStatus
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.tournament import (
    BracketResponse,
    RegistrationRequest,
    TournamentCreate,
    TournamentDetail,
    TournamentSummary,
    TournamentUpdate,
)
from app.services.tournament import TournamentService

router = APIRouter(prefix="/tournaments", tags=["大会管理"])


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
        summary = TournamentSummary(
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
        )
        items.append(summary)

    next_cursor = str(tournaments[-1].id) if has_next and tournaments else None
    return ListResponse(
        data=items,
        meta=Meta(has_next=has_next, cursor=next_cursor),
    )


@router.post("", response_model=Response[TournamentDetail], status_code=201)
async def create_tournament(
    data: TournamentCreate,
    db: DBSession,
    cache: Cache,
    current_user: OrganizerUser,
):
    service = TournamentService(db, cache)
    tournament = await service.create(data, current_user)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(
        data=TournamentDetail(
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
    )


@router.get("/{tournament_id}", response_model=Response[TournamentDetail])
async def get_tournament(
    tournament_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
):
    service = TournamentService(db, cache)
    tournament = await service.get_detail(tournament_id)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(
        data=TournamentDetail(
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
    )


@router.patch("/{tournament_id}", response_model=Response[TournamentDetail])
async def update_tournament(
    tournament_id: uuid.UUID,
    data: TournamentUpdate,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TournamentService(db, cache)
    tournament = await service.update(tournament_id, data, current_user)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(
        data=TournamentDetail(
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
    )


@router.post("/{tournament_id}/register", status_code=204)
async def register_team(
    tournament_id: uuid.UUID,
    data: RegistrationRequest,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TournamentService(db, cache)
    await service.register_team(tournament_id, uuid.UUID(data.team_id), data.notes)


@router.post(
    "/{tournament_id}/bracket",
    response_model=Response[BracketResponse],
    status_code=201,
)
async def generate_bracket(
    tournament_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TournamentService(db, cache)
    bracket = await service.generate_bracket(tournament_id, current_user)
    return Response(data=bracket)


@router.get("/{tournament_id}/bracket", response_model=Response[BracketResponse])
async def get_bracket(
    tournament_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
):
    service = TournamentService(db, cache)
    bracket = await service.get_bracket(tournament_id)
    return Response(data=bracket)
