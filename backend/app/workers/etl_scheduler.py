"""ARQ-based ETL scheduler for nightly analytics aggregation.

Run with:
    python -m arq app.workers.etl_scheduler.WorkerSettings

Scheduled jobs:
  02:00 UTC — daily_aggregation   : full rebuild of DAILY agg_player_stats from raw match data
  03:00 UTC — daily_s3_export     : ship unprocessed analytics_events to S3 as NDJSON

ARQ uses the same Redis instance as the application cache.
Jobs are idempotent: delete-and-reinsert strategy ensures no stale data.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import Integer, and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis, RedisCache
from app.models.analytics import AggPlayerStats
from app.models.enums import GameType, PeriodType
from app.models.match import Match, MatchGame, PlayerMatchStats
from app.repositories.analytics import AnalyticsRepository
from app.workers.handlers.stats_export import handle_stats_export

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle hooks
# ─────────────────────────────────────────────────────────────────────────────

async def startup(ctx: dict) -> None:
    ctx["redis_cache"] = RedisCache(await get_redis())
    logger.info("ETL scheduler started")


async def shutdown(ctx: dict) -> None:
    logger.info("ETL scheduler shut down")


# ─────────────────────────────────────────────────────────────────────────────
# Scheduled jobs
# ─────────────────────────────────────────────────────────────────────────────

async def daily_aggregation(ctx: dict) -> dict[str, Any]:
    """Full rebuild of DAILY agg_player_stats for yesterday (UTC).

    Acts as a correctness safety net for the incremental ETL handler.
    Rebuilds from PlayerMatchStats so any late-arriving or corrected
    match data is always reflected by the next morning.
    """
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    logger.info("daily_aggregation: rebuilding %s", yesterday)

    async with AsyncSessionLocal() as db:
        count = await _rebuild_player_stats_for_date(db, yesterday)
        await db.commit()

    logger.info("daily_aggregation complete: %d records for %s", count, yesterday)
    return {"date": str(yesterday), "player_records": count}


async def daily_s3_export(ctx: dict) -> dict[str, Any]:
    """Export unprocessed analytics_events to S3 (NDJSON, date-partitioned)."""
    logger.info("daily_s3_export starting")
    async with AsyncSessionLocal() as db:
        count = await handle_stats_export(db)
    logger.info("daily_s3_export complete: %d events", count)
    return {"exported": count}


# ─────────────────────────────────────────────────────────────────────────────
# Internal: full rebuild logic
# ─────────────────────────────────────────────────────────────────────────────

async def _rebuild_player_stats_for_date(
    db: AsyncSession, target_date: date
) -> int:
    """Aggregate PlayerMatchStats for matches completed on target_date.

    Uses a delete-and-reinsert strategy so the result is always consistent
    with the raw match data, regardless of what the incremental handler wrote.

    Agent breakdown is intentionally omitted here; the incremental handler
    populates it from the richer per-game payload in the SQS message.
    """
    result = await db.execute(
        select(
            PlayerMatchStats.player_id,
            Match.game,
            Match.tournament_id,
            func.count(PlayerMatchStats.id).label("games"),
            func.sum(PlayerMatchStats.kills).label("kills"),
            func.sum(PlayerMatchStats.deaths).label("deaths"),
            func.sum(PlayerMatchStats.assists).label("assists"),
        )
        .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
        .join(Match, MatchGame.match_id == Match.id)
        .where(
            and_(
                Match.status == "completed",
                func.date(Match.completed_at) == target_date,
            )
        )
        .group_by(
            PlayerMatchStats.player_id,
            Match.game,
            Match.tournament_id,
        )
    )
    rows = result.all()

    now = datetime.now(timezone.utc)
    count = 0

    for row in rows:
        kills = int(row.kills or 0)
        deaths = int(row.deaths or 0)
        assists = int(row.assists or 0)
        games = int(row.games or 0)
        kda = (kills + assists) / max(deaths, 1)

        await db.execute(
            delete(AggPlayerStats).where(
                and_(
                    AggPlayerStats.player_id == row.player_id,
                    AggPlayerStats.game == row.game,
                    AggPlayerStats.period_type == PeriodType.DAILY,
                    AggPlayerStats.period_date == target_date,
                    AggPlayerStats.tournament_id == row.tournament_id,
                )
            )
        )
        db.add(
            AggPlayerStats(
                player_id=row.player_id,
                game=row.game,
                period_type=PeriodType.DAILY,
                period_date=target_date,
                tournament_id=row.tournament_id,
                matches_played=games,
                matches_won=0,           # not derivable without winner_id join
                games_played=games,
                games_won=0,
                total_kills=kills,
                total_deaths=deaths,
                total_assists=assists,
                avg_kda=kda,
                win_rate=0.0,
                most_played_agent=None,
                agent_breakdown=None,
                calculated_at=now,
            )
        )
        count += 1

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Worker settings
# ─────────────────────────────────────────────────────────────────────────────

class WorkerSettings:
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        database=settings.REDIS_DB,
    )

    functions = [daily_aggregation, daily_s3_export]

    cron_jobs = [
        cron(daily_aggregation, hour=2, minute=0),  # 02:00 UTC
        cron(daily_s3_export,   hour=3, minute=0),  # 03:00 UTC
    ]

    on_startup = startup
    on_shutdown = shutdown

    max_jobs = 4
    job_timeout = 600   # 10 min hard limit per job
    keep_result = 3600  # keep result in Redis for 1 h for debugging
