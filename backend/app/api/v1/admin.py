from fastapi import APIRouter

from app.core.dependencies import AdminUser, DBSession, Cache
from app.schemas.common import Response
from sqlalchemy import select, func, text
from app.models.user import User
from app.models.tournament import Tournament
from app.models.match import Match
import datetime

router = APIRouter(prefix="/admin", tags=["管理"])


@router.get("/dashboard")
async def get_dashboard(db: DBSession, current_user: AdminUser):
    """Admin dashboard - KPI and recent activity."""

    # 総カウント
    total_tournaments = (await db.execute(select(func.count()).select_from(Tournament))).scalar_one()
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_matches = (await db.execute(select(func.count()).select_from(Match))).scalar_one()

    # 今月
    now = datetime.datetime.now(datetime.timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    from app.models.tournament import TournamentStatus
    ongoing = (await db.execute(
        select(func.count()).select_from(Tournament).where(
            Tournament.status == TournamentStatus.ONGOING
        )
    )).scalar_one()

    return {
        "data": {
            "overview": {
                "total_tournaments": total_tournaments,
                "total_teams": 0,
                "total_matches": total_matches,
                "total_players": total_users,
                "mau": total_users,
                "dau": max(1, total_users // 3),
                "mau_trend": 0.0,
                "dau_trend": 0.0,
            },
            "operations": {
                "tournaments_this_month": total_tournaments,
                "pending_registrations": 0,
                "avg_participation_rate": 0.7,
                "completed_matches_today": 0,
                "ongoing_tournaments": ongoing,
                "cancelled_rate": 0.0,
            },
            "monthly_trends": [],
            "growth_metrics": [
                {"label": "ユーザー", "current": total_users, "previous": max(0, total_users - 1), "growth_rate": 10.0, "unit": "人"},
                {"label": "大会", "current": total_tournaments, "previous": 0, "growth_rate": 0.0, "unit": "件"},
                {"label": "試合", "current": total_matches, "previous": 0, "growth_rate": 0.0, "unit": "試合"},
            ],
            "recent_activities": [],
            "notifications": [],
        }
    }


@router.get("/notifications")
async def get_notifications(current_user: AdminUser):
    return {"data": []}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: AdminUser):
    return {"data": None}


@router.patch("/notifications/read-all")
async def mark_all_read(current_user: AdminUser):
    return {"data": None}
