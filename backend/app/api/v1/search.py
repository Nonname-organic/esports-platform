"""グローバル検索 API（機能④ / ADR-0013）。"""

from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import DBSession
from app.schemas.common import Response
from app.search.service import SearchService

router = APIRouter(prefix="/search", tags=["検索"])


@router.get("", response_model=Response[dict])
async def global_search(
    db: DBSession,
    q: str = Query(..., min_length=2, max_length=100),
    types: Optional[str] = Query(default=None, description="カンマ区切り: team,player,tournament,match"),
    limit: int = Query(default=8, ge=1, le=20),
):
    """横断検索。{players, teams, tournaments, matches} を返す。"""
    type_list = [t.strip() for t in types.split(",")] if types else None
    data = await SearchService(db).search(q, types=type_list, limit=limit)
    return Response(data=data, meta=None)
