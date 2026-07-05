import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, DBSession
from app.rankings.aggregator import RankingAggregator
from app.rankings.tiers import list_tiers
from app.schemas.analytics import RankingEntry
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.ranking import LeaderboardEntry, RankCard, TierInfo
from app.services.ranking import RankingService

router = APIRouter(prefix="/rankings", tags=["ランキング"])


# ── 競技ランキング（グローバル/シーズン・読み取り集約 / ADR-0015） ──────────────
@router.get("/tiers", response_model=Response[list[TierInfo]])
async def get_ranking_tiers():
    """Tier 定義一覧（バッジ表示のSSOT）。"""
    return Response(data=[TierInfo(**t) for t in list_tiers()], meta=None)


@router.get("/global", response_model=ListResponse[LeaderboardEntry])
async def get_global_rankings(
    db: DBSession,
    cache: Cache,
    game: Optional[str] = Query(default=None),
    season: str = Query(default="all", pattern="^(all|current)$"),
    limit: int = Query(default=50, ge=1, le=100),
):
    """チームのグローバル/シーズン・リーダーボード。"""
    board = await RankingAggregator(db, cache).global_team_leaderboard(game=game, season=season, limit=limit)
    return ListResponse(
        data=[LeaderboardEntry(**e) for e in board],
        meta=Meta(total=len(board), has_next=False),
    )


@router.get("/team/{team_id}", response_model=Response[RankCard])
async def get_team_rank_card(
    team_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    season: str = Query(default="all", pattern="^(all|current)$"),
):
    """1チームのランクカード（順位/RP/Tier/次Tier進捗）。公開ページ・チームページ向け。"""
    card = await RankingAggregator(db, cache).team_rank_card(team_id, season=season)
    return Response(data=RankCard(**card), meta=None)


@router.get(
    "/tournaments/{tournament_id}",
    response_model=ListResponse[RankingEntry],
)
async def get_tournament_rankings(
    tournament_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    limit: int = Query(default=50, ge=1, le=100),
):
    service = RankingService(db, cache)
    entries = await service.get_tournament_rankings(tournament_id, limit)
    return ListResponse(
        data=entries,
        meta=Meta(total=len(entries), has_next=False),
    )
