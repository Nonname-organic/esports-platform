"""公開ライブ統計 API（Live Experience）。"""

from fastapi import APIRouter

from app.core.dependencies import Cache, DBSession
from app.schemas.common import Response
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["統計"])


@router.get("/overview", response_model=Response[dict])
async def get_stats_overview(db: DBSession, cache: Cache):
    """Live Status Bar / Statistics Card 用の集約値（live + totals）。公開・短TTLキャッシュ。"""
    data = await StatsService(db, cache).overview()
    return Response(data=data, meta=None)
