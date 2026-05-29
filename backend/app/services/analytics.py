import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import CacheKeys, CacheTTL, RedisCache
from app.models.enums import GameType, PeriodType
from app.models.match import Match, MatchGame, PlayerMatchStats
from app.models.player import Player
from app.models.tournament import Tournament
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    CompositionStatsResponse,
    MapStatsResponse,
    PlayerStatsResponse,
    TeamStatsResponse,
    TournamentSummaryResponse,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._repo = AnalyticsRepository(db)
        self._cache = cache
        self._db = db

    async def get_player_stats(
        self,
        player_id: uuid.UUID,
        game: GameType,
        period_type: PeriodType,
        tournament_id: uuid.UUID | None = None,
    ) -> PlayerStatsResponse:
        cache_key = (
            CacheKeys.PLAYER_STATS
            .replace("{id}", str(player_id))
            .replace("{period}", f"{game}:{period_type}")
        )
        cached = await self._cache.get(cache_key)
        if cached:
            return PlayerStatsResponse(**cached)

        # 集計テーブルから取得を試みる
        stats = await self._repo.get_player_stats(player_id, game, period_type, tournament_id)

        if stats:
            result_data = await self._db.execute(
                select(Player).where(Player.id == player_id)
            )
            player = result_data.scalar_one_or_none()
            if not player:
                raise NotFoundError("選手", str(player_id))

            response = PlayerStatsResponse(
                player_id=str(player_id),
                in_game_name=player.in_game_name,
                game=stats.game,
                period_type=stats.period_type,
                period_date=stats.period_date,
                matches_played=stats.matches_played,
                matches_won=stats.matches_won,
                games_played=stats.games_played,
                games_won=stats.games_won,
                total_kills=stats.total_kills,
                total_deaths=stats.total_deaths,
                total_assists=stats.total_assists,
                avg_kda=float(stats.avg_kda),
                win_rate=float(stats.win_rate),
                most_played_agent=stats.most_played_agent,
                agent_breakdown=stats.agent_breakdown,
            )
        else:
            # 集計テーブルが空の場合はリアルタイム計算（デモ用）
            response = await self._calculate_player_stats_realtime(player_id, game)

        await self._cache.set(cache_key, response.model_dump(), ttl=CacheTTL.PLAYER_STATS)
        return response

    async def _calculate_player_stats_realtime(
        self, player_id: uuid.UUID, game: GameType
    ) -> PlayerStatsResponse:
        """集計テーブルが未作成時のフォールバック計算。デモ用。"""
        from datetime import date

        result = await self._db.execute(
            select(Player).where(Player.id == player_id)
        )
        player = result.scalar_one_or_none()
        if not player:
            raise NotFoundError("選手", str(player_id))

        stats_result = await self._db.execute(
            select(
                func.count(PlayerMatchStats.id).label("games_played"),
                func.sum(PlayerMatchStats.kills).label("total_kills"),
                func.sum(PlayerMatchStats.deaths).label("total_deaths"),
                func.sum(PlayerMatchStats.assists).label("total_assists"),
            ).where(PlayerMatchStats.player_id == player_id)
        )
        row = stats_result.one()

        games = row.games_played or 0
        kills = row.total_kills or 0
        deaths = row.total_deaths or 0
        assists = row.total_assists or 0

        return PlayerStatsResponse(
            player_id=str(player_id),
            in_game_name=player.in_game_name,
            game=game,
            period_type=PeriodType.ALL_TIME,
            period_date=date.today(),
            matches_played=0,
            matches_won=0,
            games_played=games,
            games_won=0,
            total_kills=kills,
            total_deaths=deaths,
            total_assists=assists,
            avg_kda=(kills + assists) / max(deaths, 1),
            win_rate=0.0,
            most_played_agent=None,
            agent_breakdown=None,
        )

    async def get_map_stats(
        self,
        game: GameType,
        tournament_id: uuid.UUID | None = None,
    ) -> list[MapStatsResponse]:
        cache_key = CacheKeys.MAP_STATS.replace("{game}", game.value)
        cached = await self._cache.get(cache_key)
        if cached:
            return [MapStatsResponse(**s) for s in cached]

        stats_list = await self._repo.get_map_stats(game, tournament_id)
        responses = [
            MapStatsResponse(
                map_id=str(s.map_id),
                map_name="",  # JOIN は別途
                game=s.game,
                total_games=s.total_games,
                attack_side_wins=s.attack_side_wins,
                defense_side_wins=s.defense_side_wins,
                attack_win_rate=float(s.attack_win_rate),
                avg_duration_seconds=float(s.avg_duration_seconds) if s.avg_duration_seconds else None,
                round_distribution=s.round_distribution,
            )
            for s in stats_list
        ]

        await self._cache.set(cache_key, [r.model_dump() for r in responses], ttl=CacheTTL.MAP_STATS)
        return responses

    async def get_composition_stats(
        self,
        game: GameType,
        tournament_id: uuid.UUID | None = None,
        map_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[CompositionStatsResponse]:
        stats_list = await self._repo.get_composition_stats(game, tournament_id, map_id, limit)
        return [
            CompositionStatsResponse(
                composition=s.composition,
                games_played=s.games_played,
                wins=s.wins,
                win_rate=float(s.win_rate),
                avg_kills=float(s.avg_kills) if s.avg_kills else None,
                avg_deaths=float(s.avg_deaths) if s.avg_deaths else None,
            )
            for s in stats_list
        ]

    async def get_tournament_summary(
        self, tournament_id: uuid.UUID
    ) -> TournamentSummaryResponse:
        result = await self._db.execute(
            select(Tournament).where(Tournament.id == tournament_id)
        )
        tournament = result.scalar_one_or_none()
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))

        # 試合数集計
        match_counts = await self._db.execute(
            select(
                func.count(Match.id).label("total"),
                func.count(Match.id).filter(Match.status == "completed").label("completed"),
            ).where(Match.tournament_id == tournament_id)
        )
        counts = match_counts.one()

        # KDAトップ選手
        top_kda = await self._db.execute(
            select(
                PlayerMatchStats.player_id,
                func.avg(
                    (PlayerMatchStats.kills + PlayerMatchStats.assists)
                    / func.nullif(PlayerMatchStats.deaths, 0)
                ).label("avg_kda"),
                func.sum(PlayerMatchStats.kills).label("total_kills"),
            )
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .where(Match.tournament_id == tournament_id)
            .group_by(PlayerMatchStats.player_id)
            .order_by(func.avg(
                (PlayerMatchStats.kills + PlayerMatchStats.assists)
                / func.nullif(PlayerMatchStats.deaths, 0)
            ).desc().nullslast())
            .limit(5)
        )

        return TournamentSummaryResponse(
            tournament_id=str(tournament_id),
            tournament_name=tournament.name,
            game=tournament.game,
            total_matches=counts.total or 0,
            completed_matches=counts.completed or 0,
            total_teams=0,
            top_teams=[],
            top_players_kda=[
                {"player_id": str(r.player_id), "avg_kda": float(r.avg_kda or 0)}
                for r in top_kda.all()
            ],
            most_played_map=None,
            avg_match_duration_seconds=None,
        )
