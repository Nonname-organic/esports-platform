"""
Scout Platform API
- Player/Team Discovery
- Recruitment Board
- Recommendation Engine
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.schemas.common import Response
from app.schemas.scout import (
    ScoutPlayerCard, ScoutTeamCard, RecruitmentCreate, RecruitmentUpdate,
    RecruitmentPostSchema, ApplicationCreate, ApplicationSchema, RecommendationItem,
)
from app.services.scout_service import ScoutService

router = APIRouter(prefix="/scout", tags=["スカウト"])


# ── Player Discovery ──────────────────────────────────────────────────────────
@router.get("/players", response_model=Response[list[ScoutPlayerCard]])
async def discover_players(
    db: DBSession,
    cache: Cache,
    game: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    rank: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    min_win_rate: Optional[float] = Query(default=None, ge=0, le=1),
    min_rating: Optional[float] = Query(default=None),
    min_tournaments: Optional[int] = Query(default=None, ge=0),
    looking_only: bool = Query(default=False),
    sort_by: str = Query(default="scout_rating"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    service = ScoutService(db, cache)
    cards = await service.search_players(
        game=game, role=role, rank=rank, region=region,
        min_win_rate=min_win_rate, min_rating=min_rating, min_tournaments=min_tournaments,
        looking_only=looking_only, sort_by=sort_by, limit=limit, offset=offset,
    )
    return Response(data=[ScoutPlayerCard(**c) for c in cards], meta=None)


# ── Team Discovery ──────────────────────────────────────────────────────────
@router.get("/teams", response_model=Response[list[ScoutTeamCard]])
async def discover_teams(
    db: DBSession,
    cache: Cache,
    game: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    recruiting_only: bool = Query(default=False),
    min_avg_rating: Optional[float] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    service = ScoutService(db, cache)
    cards = await service.search_teams(
        game=game, region=region, recruiting_only=recruiting_only,
        min_avg_rating=min_avg_rating, limit=limit, offset=offset,
    )
    return Response(data=[ScoutTeamCard(**c) for c in cards], meta=None)


# ── Recruitment Board ─────────────────────────────────────────────────────────
@router.get("/recruitment", response_model=Response[list[RecruitmentPostSchema]])
async def list_recruitment(
    db: DBSession,
    cache: Cache,
    post_type: Optional[str] = Query(default=None),
    game: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    service = ScoutService(db, cache)
    posts = await service.list_posts(post_type=post_type, game=game, limit=limit, offset=offset)
    return Response(data=[RecruitmentPostSchema(**p) for p in posts], meta=None)


@router.post("/recruitment", response_model=Response[RecruitmentPostSchema], status_code=201)
async def create_recruitment(
    data: RecruitmentCreate, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = ScoutService(db, cache)
    post = await service.create_post(current_user.id, data)
    count = 0
    return Response(data=RecruitmentPostSchema(
        id=str(post.id), author_id=str(post.author_id), post_type=post.post_type,
        team_id=str(post.team_id) if post.team_id else None,
        player_id=str(post.player_id) if post.player_id else None,
        game=post.game, title=post.title, description=post.description,
        required_roles=post.required_roles, min_rank=post.min_rank, regions=post.regions,
        is_open=post.is_open, application_count=count, created_at=post.created_at,
    ), meta=None)


@router.patch("/recruitment/{post_id}", status_code=204)
async def update_recruitment(
    post_id: uuid.UUID, data: RecruitmentUpdate,
    db: DBSession, cache: Cache, current_user: CurrentUser,
):
    service = ScoutService(db, cache)
    await service.update_post(post_id, current_user.id, data)


@router.delete("/recruitment/{post_id}", status_code=204)
async def delete_recruitment(
    post_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = ScoutService(db, cache)
    await service.delete_post(post_id, current_user.id)


@router.post("/recruitment/apply", response_model=Response[ApplicationSchema], status_code=201)
async def apply_recruitment(
    data: ApplicationCreate, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = ScoutService(db, cache)
    app = await service.apply(current_user.id, data)
    return Response(data=ApplicationSchema(
        id=str(app.id), post_id=str(app.post_id), applicant_id=str(app.applicant_id),
        kind=app.kind, message=app.message, status=app.status, created_at=app.created_at,
    ), meta=None)


# ── Recommendation Engine ─────────────────────────────────────────────────────
@router.get("/recommendations/teams/{player_id}", response_model=Response[list[RecommendationItem]])
async def recommend_teams(player_id: uuid.UUID, db: DBSession, cache: Cache, limit: int = Query(default=10)):
    service = ScoutService(db, cache)
    recs = await service.recommend_teams_for_player(player_id, limit=limit)
    return Response(data=[RecommendationItem(**r) for r in recs], meta=None)


@router.get("/recommendations/players/{team_id}", response_model=Response[list[RecommendationItem]])
async def recommend_players(team_id: uuid.UUID, db: DBSession, cache: Cache, limit: int = Query(default=10)):
    service = ScoutService(db, cache)
    recs = await service.recommend_players_for_team(team_id, limit=limit)
    return Response(data=[RecommendationItem(**r) for r in recs], meta=None)
