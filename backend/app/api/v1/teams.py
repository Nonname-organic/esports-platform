import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.models.enums import GameType
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.team import (
    AddMemberRequest,
    TeamCreate,
    TeamDetailSchema,
    TeamMemberSchema,
    TeamSummarySchema,
    TeamUpdate,
)
from app.schemas.career import TeamCareerSchema, AchievementItem, RivalItem
from app.services.team import TeamService
from app.services.career_service import CareerAggregationService

router = APIRouter(prefix="/teams", tags=["チーム管理"])


# ── Career / Achievements / Rivals ──────────────────────────────────────────
@router.get("/{team_id}/career", response_model=Response[TeamCareerSchema])
async def get_team_career(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    career = await service.get_team_career(team_id)
    return Response(data=TeamCareerSchema(**career), meta=None)


@router.get("/{team_id}/achievements", response_model=Response[list[AchievementItem]])
async def get_team_achievements(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    achievements = await service.get_team_achievements(team_id)
    return Response(data=[AchievementItem(**a) for a in achievements], meta=None)


@router.get("/{team_id}/rivals", response_model=Response[list[RivalItem]])
async def get_team_rivals(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    career = await service.get_team_career(team_id)
    return Response(data=[RivalItem(**r) for r in career["rivals"]], meta=None)


def _team_detail(team) -> TeamDetailSchema:
    return TeamDetailSchema(
        id=team.id,
        name=team.name,
        tag=team.tag,
        game=team.game.value,
        logo_url=team.logo_url,
        owner_id=team.owner_id,
        is_active=team.is_active,
        created_at=team.created_at,
        description=team.description,
        country=team.country,
        banner_url=team.banner_url,
        twitter_handle=team.twitter_handle,
        updated_at=team.updated_at,
    )


def _team_summary(team) -> TeamSummarySchema:
    return TeamSummarySchema(
        id=team.id,
        name=team.name,
        tag=team.tag,
        game=team.game.value,
        logo_url=team.logo_url,
        owner_id=team.owner_id,
        is_active=team.is_active,
        created_at=team.created_at,
    )


# ── GET /teams ────────────────────────────────────────────────────────────────
@router.get("", response_model=ListResponse[TeamSummarySchema])
async def list_teams(
    db: DBSession,
    cache: Cache,
    game: Optional[GameType] = Query(default=None),
    cursor: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    service = TeamService(db, cache)
    teams, has_next = await service.list_teams(game=game, limit=limit, cursor=cursor)
    items = [_team_summary(t) for t in teams]
    next_cursor = str(items[-1].id) if has_next and items else None
    return ListResponse(
        data=items,
        meta=Meta(total=None, cursor=next_cursor, has_next=has_next),
    )


# ── POST /teams ───────────────────────────────────────────────────────────────
@router.post("", response_model=Response[TeamDetailSchema], status_code=201)
async def create_team(
    data: TeamCreate,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    team = await service.create_team(data, current_user)
    return Response(data=_team_detail(team), meta=None)


# ── GET /teams/{id} ───────────────────────────────────────────────────────────
@router.get("/{team_id}", response_model=Response[TeamDetailSchema])
async def get_team(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = TeamService(db, cache)
    team = await service.get_team(team_id)
    return Response(data=_team_detail(team), meta=None)


# ── PATCH /teams/{id} ────────────────────────────────────────────────────────
@router.patch("/{team_id}", response_model=Response[TeamDetailSchema])
async def update_team(
    team_id: uuid.UUID,
    data: TeamUpdate,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    team = await service.update_team(team_id, data, current_user)
    return Response(data=_team_detail(team), meta=None)


# ── DELETE /teams/{id} ───────────────────────────────────────────────────────
@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    await service.delete_team(team_id, current_user)


# ── GET /teams/{id}/members ───────────────────────────────────────────────────
@router.get("/{team_id}/members", response_model=Response[list[TeamMemberSchema]])
async def list_members(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = TeamService(db, cache)
    members = await service.get_members(team_id)
    return Response(data=[TeamMemberSchema(**m) for m in members], meta=None)


# ── POST /teams/{id}/members ──────────────────────────────────────────────────
@router.post("/{team_id}/members", response_model=Response[TeamMemberSchema], status_code=201)
async def add_member(
    team_id: uuid.UUID,
    data: AddMemberRequest,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    member = await service.add_member(team_id, data, current_user)
    return Response(data=TeamMemberSchema(**member), meta=None)


# ── DELETE /teams/{id}/members/{player_id} ────────────────────────────────────
@router.delete("/{team_id}/members/{player_id}", status_code=204)
async def remove_member(
    team_id: uuid.UUID,
    player_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    await service.remove_member(team_id, player_id, current_user)
