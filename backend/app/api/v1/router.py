from fastapi import APIRouter

from app.api.v1 import analytics, auth, matches, rankings, tournaments

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(tournaments.router)
api_router.include_router(matches.router)
api_router.include_router(rankings.router)
api_router.include_router(analytics.router)
