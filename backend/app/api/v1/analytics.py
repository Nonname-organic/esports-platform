import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, DBSession
from app.models.enums import GameType, PeriodType
from app.schemas.analytics import (
    CompositionStatsResponse,
    MapStatsResponse,
    PlayerStatsResponse,
    RankingEntry,
    TournamentSummaryResponse,
)
from app.schemas.common import ListResponse, Meta, Response
from app.services.analytics import AnalyticsService
from app.services.analytics_dashboard import AnalyticsDashboardService
from app.services.ranking import RankingService

router = APIRouter(prefix="/analytics", tags=["分析"])


def _dash(db, cache) -> AnalyticsDashboardService:
    return AnalyticsDashboardService(db, cache)


# ── BI Dashboard（リアルタイム集計・追加のみ / フロント types に一致） ───────────
@router.get("/winrate", response_model=Response[dict])
async def get_winrate(
    db: DBSession, cache: Cache,
    game: GameType = Query(...),
    tournament_id: uuid.UUID | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    team_id: uuid.UUID | None = Query(default=None),
):
    """全体KPI（大会数/総試合/勝率/人気MAP・エージェント）+ マップ別/エージェント別勝率。"""
    data = await _dash(db, cache).winrate(game, tournament_id, date_from, date_to, team_id)
    return Response(data=data, meta=None)


@router.get("/maps", response_model=ListResponse[dict])
async def get_maps(
    db: DBSession, cache: Cache,
    game: GameType = Query(...),
    tournament_id: uuid.UUID | None = Query(default=None),
):
    """マップ使用率・勝率。"""
    data = await _dash(db, cache).by_map(game, tournament_id)
    return ListResponse(data=data, meta=Meta(total=len(data), has_next=False))


@router.get("/agents", response_model=ListResponse[dict])
async def get_agents(
    db: DBSession, cache: Cache,
    game: GameType = Query(...),
    tournament_id: uuid.UUID | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """エージェント使用率・勝率・KDA。"""
    data = await _dash(db, cache).by_agent(game, tournament_id, date_from, date_to)
    return ListResponse(data=data, meta=Meta(total=len(data), has_next=False))


@router.get("/trend", response_model=ListResponse[dict])
async def get_trend(
    db: DBSession, cache: Cache,
    game: GameType = Query(...),
    period: str = Query(default="30d", pattern="^(7d|30d|90d|all)$"),
    tournament_id: uuid.UUID | None = Query(default=None),
):
    """日次トレンド（試合数/勝率/KDA/平均試合時間）。"""
    data = await _dash(db, cache).trend(game, period, tournament_id)
    return ListResponse(data=data, meta=Meta(total=len(data), has_next=False))


@router.get("/players", response_model=ListResponse[dict])
async def get_player_rankings(
    db: DBSession, cache: Cache,
    game: GameType = Query(...),
    tournament_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    """プレイヤーランキング（KDA/勝率上位）。"""
    data = await _dash(db, cache).players(game, tournament_id, limit)
    return ListResponse(data=data, meta=Meta(total=len(data), has_next=False))


@router.get("/heatmap", response_model=ListResponse[dict])
async def get_heatmap(
    db: DBSession, cache: Cache,
    game: GameType = Query(...),
    tournament_id: uuid.UUID | None = Query(default=None),
):
    """MAP × エージェント 勝率ヒートマップ。"""
    data = await _dash(db, cache).heatmap(game, tournament_id)
    return ListResponse(data=data, meta=Meta(total=len(data), has_next=False))


@router.get("/rankings/{tournament_id}", response_model=ListResponse[RankingEntry])
async def get_analytics_rankings(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache,
    limit: int = Query(default=50, ge=1, le=100),
):
    """大会ランキング（既存 RankingService を再利用）。"""
    entries = await RankingService(db, cache).get_tournament_rankings(tournament_id, limit)
    return ListResponse(data=entries, meta=Meta(total=len(entries), has_next=False))


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
