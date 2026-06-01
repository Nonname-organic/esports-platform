from fastapi import APIRouter

from app.api.v1 import admin, analytics, auth, matches, players, rankings, teams, tournaments, upload

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(tournaments.router)
api_router.include_router(matches.router)
api_router.include_router(rankings.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
api_router.include_router(teams.router)
api_router.include_router(players.router)
api_router.include_router(upload.router)
