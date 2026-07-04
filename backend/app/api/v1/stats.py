"""公開ライブ統計 API（Live Experience）。"""

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, DBSession
from app.schemas.common import Response
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["統計"])


@router.get("/overview", response_model=Response[dict])
async def get_stats_overview(db: DBSession, cache: Cache):
    """Live Status Bar / Statistics Card 用の集約値（live + totals）。公開・短TTLキャッシュ。"""
    data = await StatsService(db, cache).overview()
    return Response(data=data, meta=None)


@router.get("/champions", response_model=Response[list[dict]])
async def get_recent_champions(
    db: DBSession, cache: Cache, limit: int = Query(default=3, ge=1, le=10),
):
    """直近の優勝チーム（Winner Highlight 用）。TournamentReport から読み取り集約。"""
    data = await StatsService(db, cache).recent_champions(limit=limit)
    return Response(data=data, meta=None)
