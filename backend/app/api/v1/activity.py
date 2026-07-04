"""公開アクティビティ・タイムライン API（Live Activity / ADR-0011）。"""

from fastapi import APIRouter, Query

from app.core.dependencies import DBSession
from app.schemas.common import Response
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activity", tags=["アクティビティ"])


@router.get("/feed", response_model=Response[list[dict]])
async def get_activity_feed(
    db: DBSession,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """プラットフォーム全体の公開活動タイムライン（visibility=public のみ・新しい順）。"""
    items = await ActivityService(db).global_activity(limit=limit, offset=offset)
    return Response(data=items, meta=None)
