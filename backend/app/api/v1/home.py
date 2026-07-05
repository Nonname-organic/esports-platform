"""Home Personalization API（ADR-0019 / Read Model・公開・追加のみ）。"""

from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, DBSession
from app.home.aggregator import HomeAggregator
from app.home.base import HomeContext
from app.schemas.common import Response

router = APIRouter(prefix="/home", tags=["ホーム"])


def _ctx(game: Optional[str]) -> HomeContext:
    return HomeContext(user_id=None, game=game)


@router.get("", response_model=Response[dict])
async def get_home(db: DBSession, cache: Cache, game: Optional[str] = Query(default=None)):
    """ホーム全体（recommendations/predictions/trending/live/activity/insights）。"""
    data = await HomeAggregator(db, cache).home(_ctx(game))
    return Response(data=data, meta=None)


@router.get("/recommendations", response_model=Response[list[dict]])
async def get_home_recommendations(db: DBSession, cache: Cache, game: Optional[str] = Query(default=None)):
    data = await HomeAggregator(db, cache).widget("recommendations", _ctx(game))
    return Response(data=data, meta=None)


@router.get("/predictions", response_model=Response[dict])
async def get_home_predictions(db: DBSession, cache: Cache, game: Optional[str] = Query(default=None)):
    data = await HomeAggregator(db, cache).widget("predictions", _ctx(game))
    return Response(data=data, meta=None)


@router.get("/trending", response_model=Response[dict])
async def get_home_trending(db: DBSession, cache: Cache, game: Optional[str] = Query(default=None)):
    data = await HomeAggregator(db, cache).widget("trending", _ctx(game))
    return Response(data=data, meta=None)


@router.get("/live", response_model=Response[dict])
async def get_home_live(db: DBSession, cache: Cache):
    data = await HomeAggregator(db, cache).widget("live", _ctx(None))
    return Response(data=data, meta=None)
