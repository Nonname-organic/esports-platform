from fastapi import APIRouter, Query

from app.core.dependencies import AdminUser, DBSession, Cache
from app.schemas.common import Response
from app.services.audit_service import AuditService
from sqlalchemy import select, func, text
from app.models.user import User
from app.models.tournament import Tournament, TournamentRegistration
from app.models.match import Match
from app.models.team import Team
from app.models.player import Player
from app.models.domain_event import DomainEvent
from app.models.enums import MatchStatus, RegistrationStatus
import datetime
from typing import Optional

router = APIRouter(prefix="/admin", tags=["管理"])


@router.get("/audit", response_model=Response[list[dict]])
async def get_audit_log(
    db: DBSession, current_user: AdminUser,
    entity_type: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """全体監査ログ（Admin限定 / ADR-0012）。"""
    items = await AuditService(db).list(
        entity_type=entity_type, action=action, limit=limit, offset=offset,
    )
    return Response(data=items, meta=None)


@router.get("/dashboard")
async def get_dashboard(db: DBSession, current_user: AdminUser):
    """Admin dashboard - KPI と運営指標。

    以前は total_teams=0、dau=総ユーザー数÷3、参加率=0.7、成長率=10.0 と
    いった作った数字を返していた。運営が判断に使う画面なので実データで出す。
    算出元が無いものは 0 や空のまま返し、それらしい値を作らない。
    """
    from app.models.tournament import TournamentStatus

    now = datetime.datetime.now(datetime.timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async def count(stmt) -> int:
        return int((await db.execute(stmt)).scalar() or 0)

    total_tournaments = await count(select(func.count()).select_from(Tournament))
    total_users = await count(select(func.count()).select_from(User))
    total_matches = await count(select(func.count()).select_from(Match))
    total_teams = await count(select(func.count()).select_from(Team))
    total_players = await count(select(func.count()).select_from(Player))

    # 稼働ユーザーは domain_events の actor から数える。イベントが無い環境では 0
    async def active_since(since: datetime.datetime, until=None) -> int:
        stmt = select(func.count(func.distinct(DomainEvent.actor_id))).where(
            DomainEvent.actor_id.isnot(None), DomainEvent.created_at >= since
        )
        if until is not None:
            stmt = stmt.where(DomainEvent.created_at < until)
        return await count(stmt)

    day = datetime.timedelta(days=1)
    month = datetime.timedelta(days=30)
    dau = await active_since(now - day)
    mau = await active_since(now - month)
    dau_prev = await active_since(now - day * 2, now - day)
    mau_prev = await active_since(now - month * 2, now - month)

    def growth(current: int, previous: int) -> float:
        """前期比（%）。比較できないときは 0 を返し、伸び率を作らない。"""
        if previous <= 0:
            return 0.0
        return round((current - previous) / previous * 100, 1)

    ongoing = await count(
        select(func.count()).select_from(Tournament)
        .where(Tournament.status == TournamentStatus.ONGOING)
    )
    cancelled = await count(
        select(func.count()).select_from(Tournament)
        .where(Tournament.status == TournamentStatus.CANCELLED)
    )
    tournaments_this_month = await count(
        select(func.count()).select_from(Tournament)
        .where(Tournament.created_at >= month_start)
    )
    pending_registrations = await count(
        select(func.count()).select_from(TournamentRegistration)
        .where(TournamentRegistration.status == RegistrationStatus.PENDING)
    )
    completed_matches_today = await count(
        select(func.count()).select_from(Match).where(
            Match.status == MatchStatus.COMPLETED, Match.ended_at >= day_start
        )
    )
    # 参加率は「埋まった枠 / 用意した枠」。定員未設定の大会は分母から外す。
    # 登録チーム数はテーブルに持っていないので、承認済みの登録を数える
    filled = await count(
        select(func.count()).select_from(TournamentRegistration)
        .join(Tournament, Tournament.id == TournamentRegistration.tournament_id)
        .where(
            TournamentRegistration.status == RegistrationStatus.APPROVED,
            Tournament.max_teams > 0,
        )
    )
    capacity = await count(
        select(func.coalesce(func.sum(Tournament.max_teams), 0))
        .where(Tournament.max_teams > 0)
    )
    participation = round(filled / capacity, 4) if capacity else 0.0

    users_prev = await count(
        select(func.count()).select_from(User).where(User.created_at < month_start)
    )
    tournaments_prev = await count(
        select(func.count()).select_from(Tournament)
        .where(Tournament.created_at < month_start)
    )
    matches_prev = total_matches - await count(
        select(func.count()).select_from(Match).where(Match.created_at >= month_start)
    )

    return {
        "data": {
            "overview": {
                "total_tournaments": total_tournaments,
                "total_teams": total_teams,
                "total_matches": total_matches,
                "total_players": total_players,
                "mau": mau,
                "dau": dau,
                "mau_trend": growth(mau, mau_prev),
                "dau_trend": growth(dau, dau_prev),
            },
            "operations": {
                "tournaments_this_month": tournaments_this_month,
                "pending_registrations": pending_registrations,
                "avg_participation_rate": participation,
                "completed_matches_today": completed_matches_today,
                "ongoing_tournaments": ongoing,
                "cancelled_rate": round(cancelled / total_tournaments, 4)
                if total_tournaments else 0.0,
            },
            # 月次推移と活動履歴は集計の置き場がまだ無い。埋めずに空で返す
            "monthly_trends": [],
            "growth_metrics": [
                {"label": "ユーザー", "current": total_users,
                 "previous": users_prev, "growth_rate": growth(total_users, users_prev),
                 "unit": "人"},
                {"label": "大会", "current": total_tournaments,
                 "previous": tournaments_prev,
                 "growth_rate": growth(total_tournaments, tournaments_prev),
                 "unit": "件"},
                {"label": "試合", "current": total_matches,
                 "previous": matches_prev,
                 "growth_rate": growth(total_matches, matches_prev),
                 "unit": "試合"},
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
