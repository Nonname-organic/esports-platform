import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import CacheKeys, CacheTTL, RedisCache
from app.repositories.tournament import RankingRepository, TournamentRepository
from app.schemas.analytics import RankingEntry


class RankingService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._repo = RankingRepository(db)
        self._tournament_repo = TournamentRepository(db)
        self._cache = cache

    async def get_tournament_rankings(
        self, tournament_id: uuid.UUID, limit: int = 50
    ) -> list[RankingEntry]:
        cache_key = CacheKeys.RANKING_TOURNAMENT.replace("{id}", str(tournament_id))
        cached = await self._cache.get(cache_key)
        if cached:
            return [RankingEntry(**r) for r in cached]

        tournament = await self._tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))

        rankings = await self._repo.get_tournament_rankings(tournament_id, limit)
        entries = [
            RankingEntry(
                rank_position=r.rank_position,
                team_id=str(r.team_id),
                team_name=r.team.name if r.team else "",
                team_tag=r.team.tag if r.team else "",
                team_logo_url=r.team.logo_url if r.team else None,
                points=r.points,
                wins=r.wins,
                losses=r.losses,
                game_wins=r.game_wins,
                game_losses=r.game_losses,
                win_rate=r.wins / max(r.wins + r.losses, 1),
            )
            for r in rankings
        ]

        await self._cache.set(
            cache_key,
            [e.model_dump() for e in entries],
            ttl=CacheTTL.RANKING,
        )
        return entries

    async def update_after_match(
        self,
        tournament_id: uuid.UUID,
        winner_id: uuid.UUID,
        loser_id: uuid.UUID,
        winner_game_wins: int,
        loser_game_wins: int,
    ) -> None:
        """試合結果を受けてランキングを更新する。Workerから呼ばれる。"""
        WIN_POINTS = 3
        LOSS_POINTS = 0

        # 勝者の更新
        winner_ranking = await self._repo.upsert_ranking(
            tournament_id=tournament_id,
            team_id=winner_id,
            points=WIN_POINTS,
            wins=1,
            losses=0,
            game_wins=winner_game_wins,
            game_losses=loser_game_wins,
        )
        # 敗者の更新
        await self._repo.upsert_ranking(
            tournament_id=tournament_id,
            team_id=loser_id,
            points=LOSS_POINTS,
            wins=0,
            losses=1,
            game_wins=loser_game_wins,
            game_losses=winner_game_wins,
        )

        # 全ランキングの順位を再計算
        await self._repo.recalculate_positions(tournament_id)

        # キャッシュ無効化
        await self._cache.delete(
            CacheKeys.RANKING_TOURNAMENT.replace("{id}", str(tournament_id))
        )
