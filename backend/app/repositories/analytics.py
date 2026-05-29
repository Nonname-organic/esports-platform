import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import (
    AggCompositionStats,
    AggMapStats,
    AggPlayerStats,
    AggTeamStats,
    AnalyticsEvent,
)
from app.models.enums import GameType, PeriodType
from app.repositories.base import BaseRepository


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ──────────────────────────────────────────────
    # Read methods
    # ──────────────────────────────────────────────

    async def get_player_stats(
        self,
        player_id: uuid.UUID,
        game: GameType,
        period_type: PeriodType,
        tournament_id: uuid.UUID | None = None,
    ) -> AggPlayerStats | None:
        filters = [
            AggPlayerStats.player_id == player_id,
            AggPlayerStats.game == game,
            AggPlayerStats.period_type == period_type,
        ]
        if tournament_id:
            filters.append(AggPlayerStats.tournament_id == tournament_id)

        result = await self._db.execute(
            select(AggPlayerStats)
            .where(and_(*filters))
            .order_by(desc(AggPlayerStats.calculated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_team_stats(
        self,
        team_id: uuid.UUID,
        game: GameType,
        period_type: PeriodType,
        tournament_id: uuid.UUID | None = None,
    ) -> AggTeamStats | None:
        filters = [
            AggTeamStats.team_id == team_id,
            AggTeamStats.game == game,
            AggTeamStats.period_type == period_type,
        ]
        if tournament_id:
            filters.append(AggTeamStats.tournament_id == tournament_id)

        result = await self._db.execute(
            select(AggTeamStats)
            .where(and_(*filters))
            .order_by(desc(AggTeamStats.calculated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_map_stats(
        self,
        game: GameType,
        tournament_id: uuid.UUID | None = None,
    ) -> list[AggMapStats]:
        filters = [AggMapStats.game == game]
        if tournament_id:
            filters.append(AggMapStats.tournament_id == tournament_id)
        else:
            filters.append(AggMapStats.tournament_id == None)  # noqa: E711

        result = await self._db.execute(
            select(AggMapStats)
            .where(and_(*filters))
            .order_by(desc(AggMapStats.total_games))
        )
        return list(result.scalars().all())

    async def get_composition_stats(
        self,
        game: GameType,
        tournament_id: uuid.UUID | None = None,
        map_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[AggCompositionStats]:
        filters = [
            AggCompositionStats.game == game,
            AggCompositionStats.games_played >= 3,
        ]
        if tournament_id:
            filters.append(AggCompositionStats.tournament_id == tournament_id)
        if map_id:
            filters.append(AggCompositionStats.map_id == map_id)

        result = await self._db.execute(
            select(AggCompositionStats)
            .where(and_(*filters))
            .order_by(desc(AggCompositionStats.win_rate))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_unprocessed_events(self, limit: int = 1000) -> list[AnalyticsEvent]:
        result = await self._db.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.processed == False)  # noqa: E712
            .order_by(AnalyticsEvent.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────────
    # Write methods
    # ──────────────────────────────────────────────

    async def record_event(
        self,
        event_type: str,
        payload: dict,
        tournament_id: uuid.UUID | None = None,
        team_id: uuid.UUID | None = None,
        player_id: uuid.UUID | None = None,
        match_id: uuid.UUID | None = None,
        source: str = "application",
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(
            event_type=event_type,
            source=source,
            tournament_id=tournament_id,
            team_id=team_id,
            player_id=player_id,
            match_id=match_id,
            payload=payload,
            processed=False,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(event)
        await self._db.flush()
        return event

    async def mark_events_processed(self, event_ids: list[uuid.UUID]) -> None:
        if not event_ids:
            return
        await self._db.execute(
            update(AnalyticsEvent)
            .where(AnalyticsEvent.id.in_(event_ids))
            .values(processed=True)
        )

    # ──────────────────────────────────────────────
    # Incremental upsert helpers (called after each match)
    # ──────────────────────────────────────────────

    async def upsert_team_stats_delta(
        self,
        team_id: uuid.UUID,
        game: GameType,
        period_type: PeriodType,
        period_date: date,
        tournament_id: uuid.UUID | None,
        won: bool,
        game_duration_seconds: float | None = None,
    ) -> None:
        """Increment win/loss counts for a team after a single match."""
        now = datetime.now(timezone.utc)
        filters = [
            AggTeamStats.team_id == team_id,
            AggTeamStats.game == game,
            AggTeamStats.period_type == period_type,
            AggTeamStats.period_date == period_date,
            AggTeamStats.tournament_id == tournament_id,
        ]

        result = await self._db.execute(
            select(AggTeamStats).where(and_(*filters)).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.matches_played += 1
            if won:
                existing.wins += 1
                existing.current_streak = max(0, existing.current_streak) + 1
                existing.best_win_streak = max(
                    existing.best_win_streak, existing.current_streak
                )
            else:
                existing.losses += 1
                existing.current_streak = min(0, existing.current_streak) - 1

            existing.win_rate = existing.wins / existing.matches_played

            if game_duration_seconds is not None:
                n = existing.matches_played
                prev = float(existing.avg_game_duration_seconds or 0)
                # Welford online mean update
                existing.avg_game_duration_seconds = prev + (game_duration_seconds - prev) / n

            existing.calculated_at = now
        else:
            streak = 1 if won else -1
            self._db.add(
                AggTeamStats(
                    team_id=team_id,
                    game=game,
                    period_type=period_type,
                    period_date=period_date,
                    tournament_id=tournament_id,
                    matches_played=1,
                    wins=1 if won else 0,
                    losses=0 if won else 1,
                    win_rate=1.0 if won else 0.0,
                    current_streak=streak,
                    best_win_streak=1 if won else 0,
                    avg_game_duration_seconds=game_duration_seconds,
                    calculated_at=now,
                )
            )

    async def upsert_player_stats_delta(
        self,
        player_id: uuid.UUID,
        game: GameType,
        period_type: PeriodType,
        period_date: date,
        tournament_id: uuid.UUID | None,
        match_won: bool,
        games_played: int,
        games_won: int,
        kills: int,
        deaths: int,
        assists: int,
        agent_breakdown_delta: dict[str, Any] | None = None,
    ) -> None:
        """Increment per-player stats by one match's aggregated totals.

        Accepts pre-summed totals for all games within a single match so that
        BO3/BO5 matches don't cause over-counting of matches_played.
        KDA is re-derived from cumulative raw totals, which is more accurate
        than a running mean over per-match KDA values.
        """
        now = datetime.now(timezone.utc)
        filters = [
            AggPlayerStats.player_id == player_id,
            AggPlayerStats.game == game,
            AggPlayerStats.period_type == period_type,
            AggPlayerStats.period_date == period_date,
            AggPlayerStats.tournament_id == tournament_id,
        ]

        result = await self._db.execute(
            select(AggPlayerStats).where(and_(*filters)).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.matches_played += 1
            if match_won:
                existing.matches_won += 1
            existing.games_played += games_played
            existing.games_won += games_won
            existing.total_kills += kills
            existing.total_deaths += deaths
            existing.total_assists += assists
            # KDA from cumulative totals — always accurate, no numerical drift
            existing.avg_kda = (
                (existing.total_kills + existing.total_assists)
                / max(existing.total_deaths, 1)
            )
            existing.win_rate = existing.games_won / existing.games_played

            if agent_breakdown_delta:
                breakdown: dict[str, Any] = existing.agent_breakdown or {}
                for agent, delta in agent_breakdown_delta.items():
                    entry = breakdown.setdefault(agent, {"games": 0, "wins": 0})
                    entry["games"] += delta.get("games", 0)
                    entry["wins"] += delta.get("wins", 0)
                existing.most_played_agent = max(
                    breakdown, key=lambda a: breakdown[a]["games"]
                )
                existing.agent_breakdown = breakdown

            existing.calculated_at = now
        else:
            kda = (kills + assists) / max(deaths, 1)
            win_rate = games_won / max(games_played, 1)
            most_played = (
                max(agent_breakdown_delta, key=lambda a: agent_breakdown_delta[a]["games"])
                if agent_breakdown_delta
                else None
            )
            self._db.add(
                AggPlayerStats(
                    player_id=player_id,
                    game=game,
                    period_type=period_type,
                    period_date=period_date,
                    tournament_id=tournament_id,
                    matches_played=1,
                    matches_won=1 if match_won else 0,
                    games_played=games_played,
                    games_won=games_won,
                    total_kills=kills,
                    total_deaths=deaths,
                    total_assists=assists,
                    avg_kda=kda,
                    win_rate=win_rate,
                    most_played_agent=most_played,
                    agent_breakdown=agent_breakdown_delta,
                    calculated_at=now,
                )
            )

    async def upsert_map_stats_delta(
        self,
        map_id: uuid.UUID,
        game: GameType,
        tournament_id: uuid.UUID | None,
        winner_side: str,  # "attack" | "defense"
        duration_seconds: float | None,
        rounds_played: int,
        calculated_date: date,
    ) -> None:
        """Increment map pick/win-side counts after a single game."""
        now = datetime.now(timezone.utc)
        filters = [
            AggMapStats.map_id == map_id,
            AggMapStats.game == game,
            AggMapStats.tournament_id == tournament_id,
            AggMapStats.calculated_date == calculated_date,
        ]

        result = await self._db.execute(
            select(AggMapStats).where(and_(*filters)).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.total_games += 1
            existing.total_rounds += rounds_played
            if winner_side == "attack":
                existing.attack_side_wins += 1
            else:
                existing.defense_side_wins += 1
            total = existing.total_games
            existing.attack_win_rate = existing.attack_side_wins / total

            if duration_seconds is not None:
                prev = float(existing.avg_duration_seconds or 0)
                existing.avg_duration_seconds = prev + (duration_seconds - prev) / total

            existing.calculated_at = now
        else:
            attack_wins = 1 if winner_side == "attack" else 0
            defense_wins = 1 if winner_side == "defense" else 0
            self._db.add(
                AggMapStats(
                    map_id=map_id,
                    game=game,
                    tournament_id=tournament_id,
                    total_games=1,
                    attack_side_wins=attack_wins,
                    defense_side_wins=defense_wins,
                    attack_win_rate=float(attack_wins),
                    total_rounds=rounds_played,
                    avg_duration_seconds=duration_seconds,
                    round_distribution=None,
                    calculated_date=calculated_date,
                    calculated_at=now,
                )
            )

    async def upsert_composition_stats_delta(
        self,
        game: GameType,
        tournament_id: uuid.UUID | None,
        map_id: uuid.UUID | None,
        composition: list[str],  # sorted agent/hero names
        won: bool,
        avg_kills: float | None,
        avg_deaths: float | None,
        calculated_date: date,
    ) -> None:
        """Increment composition win/loss counts after a single game."""
        now = datetime.now(timezone.utc)
        # JSONB array equality: cast to JSON for comparison
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSONB

        filters = [
            AggCompositionStats.game == game,
            AggCompositionStats.tournament_id == tournament_id,
            AggCompositionStats.map_id == map_id,
            AggCompositionStats.composition == cast(composition, JSONB),
            AggCompositionStats.calculated_date == calculated_date,
        ]

        result = await self._db.execute(
            select(AggCompositionStats).where(and_(*filters)).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.games_played += 1
            if won:
                existing.wins += 1
            existing.win_rate = existing.wins / existing.games_played
            # Running average kills/deaths
            n = existing.games_played
            if avg_kills is not None:
                prev_k = float(existing.avg_kills or 0)
                existing.avg_kills = prev_k + (avg_kills - prev_k) / n
            if avg_deaths is not None:
                prev_d = float(existing.avg_deaths or 0)
                existing.avg_deaths = prev_d + (avg_deaths - prev_d) / n
            existing.calculated_at = now
        else:
            self._db.add(
                AggCompositionStats(
                    game=game,
                    tournament_id=tournament_id,
                    map_id=map_id,
                    composition=composition,
                    games_played=1,
                    wins=1 if won else 0,
                    win_rate=1.0 if won else 0.0,
                    avg_kills=avg_kills,
                    avg_deaths=avg_deaths,
                    calculated_date=calculated_date,
                    calculated_at=now,
                )
            )
