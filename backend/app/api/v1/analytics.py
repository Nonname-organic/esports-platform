import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, DBSession
from app.models.enums import GameType, PeriodType
from app.schemas.analytics import (
    CompositionStatsResponse,
    MapStatsResponse,
    PlayerStatsResponse,
    TournamentSummaryResponse,
)
from app.schemas.common import ListResponse, Meta, Response
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["分析"])


@router.get("/players/{player_id}/stats", response_model=Response[PlayerStatsResponse])
async def get_player_stats(
    player_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    game: GameType = Query(...),
    period_type: PeriodType = Query(default=PeriodType.ALL_TIME),
    tournament_id: uuid.UUID | None = Query(default=None),
):
    service = AnalyticsService(db, cache)
    stats = await service.get_player_stats(player_id, game, period_type, tournament_id)
    return Response(data=stats)


@router.get("/maps/stats", response_model=ListResponse[MapStatsResponse])
async def get_map_stats(
    db: DBSession,
    cache: Cache,
    game: GameType = Query(...),
    tournament_id: uuid.UUID | None = Query(default=None),
):
    service = AnalyticsService(db, cache)
    stats = await service.get_map_stats(game, tournament_id)
    return ListResponse(data=stats, meta=Meta(total=len(stats), has_next=False))


@router.get("/compositions", response_model=ListResponse[CompositionStatsResponse])
async def get_composition_stats(
    db: DBSession,
    cache: Cache,
    game: GameType = Query(...),
    tournament_id: uuid.UUID | None = Query(default=None),
    map_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    service = AnalyticsService(db, cache)
    stats = await service.get_composition_stats(game, tournament_id, map_id, limit)
    return ListResponse(data=stats, meta=Meta(total=len(stats), has_next=False))


@router.get(
    "/tournaments/{tournament_id}/summary",
    response_model=Response[TournamentSummaryResponse],
)
async def get_tournament_summary(
    tournament_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
):
    service = AnalyticsService(db, cache)
    summary = await service.get_tournament_summary(tournament_id)
    return Response(data=summary)
