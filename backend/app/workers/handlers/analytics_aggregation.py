"""Incremental ETL handler: aggregates stats from a single match result event.

Called immediately after match_result_registered via the SQS consumer.
Handles DAILY and TOURNAMENT period aggregations; WEEKLY/MONTHLY are
rebuilt nightly by etl_scheduler.py from scratch.

Expected event body:
{
  "event_type": "match_result_registered",
  "match_id": "<uuid>",
  "tournament_id": "<uuid>",
  "game": "VALORANT",
  "winner_id": "<team-uuid>",
  "loser_id":  "<team-uuid>",
  "winner_score": 2,
  "loser_score":  1,
  "maps": [                          # optional
    {
      "map_id": "<uuid>",
      "winner_side": "attack",       # "attack" | "defense"
      "duration_seconds": 3600,
      "rounds_played": 25
    }
  ],
  "player_stats": [                  # optional; one entry per game (not per match)
    {
      "player_id": "<uuid>",
      "team_id":   "<uuid>",
      "agent":     "Jett",
      "kills": 25, "deaths": 15, "assists": 10,
      "map_id": "<uuid>",            # which game/map this stat belongs to
      "game_won": true
    }
  ]
}
"""

import uuid
import logging
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import CacheKeys, RedisCache
from app.models.enums import GameType, PeriodType
from app.repositories.analytics import AnalyticsRepository

logger = logging.getLogger(__name__)


async def handle_analytics_aggregation(
    body: dict, db: AsyncSession, cache: RedisCache
) -> None:
    try:
        await _aggregate(body, db, cache)
    except Exception:
        logger.exception(
            "analytics_aggregation failed for match=%s", body.get("match_id")
        )
        raise


async def _aggregate(body: dict, db: AsyncSession, cache: RedisCache) -> None:
    tournament_id = uuid.UUID(body["tournament_id"])
    winner_id = uuid.UUID(body["winner_id"])
    loser_id = uuid.UUID(body["loser_id"])
    game = GameType(body["game"])
    today = datetime.now(timezone.utc).date()

    repo = AnalyticsRepository(db)

    # Determine total match duration from maps if available
    maps: list[dict] = body.get("maps", [])
    total_duration: float | None = None
    if maps:
        durations = [m["duration_seconds"] for m in maps if m.get("duration_seconds")]
        total_duration = sum(durations) if durations else None

    # ── 1. Team stats: DAILY and TOURNAMENT ──────────────────────────────
    for team_id, won in [(winner_id, True), (loser_id, False)]:
        for period_type, t_id in [
            (PeriodType.DAILY, None),
            (PeriodType.TOURNAMENT, tournament_id),
        ]:
            await repo.upsert_team_stats_delta(
                team_id=team_id,
                game=game,
                period_type=period_type,
                period_date=today,
                tournament_id=t_id,
                won=won,
                game_duration_seconds=total_duration,
            )

    # ── 2. Map stats ─────────────────────────────────────────────────────
    for map_data in maps:
        if not map_data.get("map_id"):
            continue
        map_id = uuid.UUID(map_data["map_id"])
        winner_side = map_data.get("winner_side", "attack")
        duration = map_data.get("duration_seconds")
        rounds = map_data.get("rounds_played", 0)

        # Global (no tournament scope) + tournament-scoped
        for t_id in [None, tournament_id]:
            await repo.upsert_map_stats_delta(
                map_id=map_id,
                game=game,
                tournament_id=t_id,
                winner_side=winner_side,
                duration_seconds=float(duration) if duration else None,
                rounds_played=rounds,
                calculated_date=today,
            )

    # ── 3. Player stats + composition stats ──────────────────────────────
    player_stats: list[dict] = body.get("player_stats", [])

    if player_stats:
        # Group by player_id so BO3/BO5 entries don't over-count matches_played.
        # Each key maps to all game-level entries for that player in this match.
        from collections import defaultdict

        by_player: dict[str, list[dict]] = defaultdict(list)
        for ps in player_stats:
            by_player[ps["player_id"]].append(ps)

        for player_id_str, games in by_player.items():
            player_id = uuid.UUID(player_id_str)
            team_id = uuid.UUID(games[0]["team_id"])
            won_match = team_id == winner_id

            total_kills = sum(int(g.get("kills", 0)) for g in games)
            total_deaths = sum(int(g.get("deaths", 0)) for g in games)
            total_assists = sum(int(g.get("assists", 0)) for g in games)
            n_games = len(games)
            n_won = sum(1 for g in games if bool(g.get("game_won", won_match)))

            # Agent breakdown: {"Jett": {"games": 2, "wins": 1}, ...}
            agent_breakdown: dict[str, dict] = {}
            for g in games:
                ag = g.get("agent")
                if ag:
                    entry = agent_breakdown.setdefault(ag, {"games": 0, "wins": 0})
                    entry["games"] += 1
                    if bool(g.get("game_won", won_match)):
                        entry["wins"] += 1

            for period_type, t_id in [
                (PeriodType.DAILY, None),
                (PeriodType.TOURNAMENT, tournament_id),
            ]:
                await repo.upsert_player_stats_delta(
                    player_id=player_id,
                    game=game,
                    period_type=period_type,
                    period_date=today,
                    tournament_id=t_id,
                    match_won=won_match,
                    games_played=n_games,
                    games_won=n_won,
                    kills=total_kills,
                    deaths=total_deaths,
                    assists=total_assists,
                    agent_breakdown_delta=agent_breakdown or None,
                )

        # Composition stats: group player_stats by (team_id, map_id)
        await _update_composition_stats(
            repo=repo,
            player_stats=player_stats,
            winner_id=winner_id,
            game=game,
            tournament_id=tournament_id,
            today=today,
        )

    # ── 4. Invalidate Redis caches ────────────────────────────────────────
    await _bust_caches(cache, game, tournament_id, player_stats)

    logger.info(
        "analytics aggregated tournament=%s game=%s players=%d maps=%d",
        tournament_id,
        game,
        len(player_stats),
        len(maps),
    )


async def _update_composition_stats(
    repo: AnalyticsRepository,
    player_stats: list[dict],
    winner_id: uuid.UUID,
    game: GameType,
    tournament_id: uuid.UUID,
    today: date,
) -> None:
    """Derives compositions per (team, map) and upserts them.

    Compositions are sorted alphabetically so ["Jett","Sage"] ==
    ["Sage","Jett"] and compare correctly as JSONB.
    """
    from collections import defaultdict

    # {(team_id_str, map_id_str): [stat_dicts]}
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for ps in player_stats:
        key = (ps["team_id"], ps.get("map_id", ""))
        groups[key].append(ps)

    for (team_id_str, map_id_str), group in groups.items():
        team_id = uuid.UUID(team_id_str)
        map_id = uuid.UUID(map_id_str) if map_id_str else None

        agents = sorted(ps["agent"] for ps in group if ps.get("agent"))
        if not agents:
            continue

        won = team_id == winner_id
        avg_kills = sum(ps.get("kills", 0) for ps in group) / len(group)
        avg_deaths = sum(ps.get("deaths", 0) for ps in group) / len(group)

        for t_id in [None, tournament_id]:
            await repo.upsert_composition_stats_delta(
                game=game,
                tournament_id=t_id,
                map_id=map_id,
                composition=agents,
                won=won,
                avg_kills=avg_kills,
                avg_deaths=avg_deaths,
                calculated_date=today,
            )


async def _bust_caches(
    cache: RedisCache,
    game: GameType,
    tournament_id: uuid.UUID,
    player_stats: list[dict],
) -> None:
    await cache.delete_pattern(
        CacheKeys.MAP_STATS.replace("{game}", game.value)
    )
    await cache.delete_pattern(
        f"cache:composition:{game.value}:*"
    )
    await cache.delete(
        CacheKeys.RANKING_TOURNAMENT.replace("{id}", str(tournament_id))
    )
    # Invalidate per-player caches
    for ps in player_stats:
        player_id = ps.get("player_id")
        if player_id:
            await cache.delete_pattern(
                f"cache:player:{player_id}:stats:*"
            )
