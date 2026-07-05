"""シーズン API（時間窓 / ADR-0016・read-only）。"""

from fastapi import APIRouter

from app.schemas.common import Response
from app.seasons.dto import SeasonInfo
from app.seasons.service import SeasonService

router = APIRouter(prefix="/seasons", tags=["シーズン"])


@router.get("", response_model=Response[list[SeasonInfo]])
async def list_seasons():
    """Current / Previous / All Time のシーズン一覧。"""
    return Response(data=[SeasonInfo(**s) for s in SeasonService().list()], meta=None)
