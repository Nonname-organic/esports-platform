import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, DBSession
from app.schemas.analytics import RankingEntry
from app.schemas.common import ListResponse, Meta
from app.services.ranking import RankingService

router = APIRouter(prefix="/rankings", tags=["ランキング"])


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
