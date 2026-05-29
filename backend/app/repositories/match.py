import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import MatchStatus
from app.models.match import BanPick, Match, MatchGame, MatchResult, PlayerMatchStats
from app.repositories.base import BaseRepository


class MatchRepository(BaseRepository[Match]):
    def __init__(self, db: AsyncSession):
        super().__init__(Match, db)

    async def get_full_detail(self, match_id: uuid.UUID) -> Match | None:
        result = await self._db.execute(
            select(Match)
            .where(Match.id == match_id)
            .options(
                selectinload(Match.team1),
                selectinload(Match.team2),
                selectinload(Match.winner),
                selectinload(Match.games).options(
                    selectinload(MatchGame.map),
                    selectinload(MatchGame.player_stats),
                ),
                selectinload(Match.ban_picks).options(
                    selectinload(BanPick.map),
                    selectinload(BanPick.team),
                ),
                selectinload(Match.result),
            )
        )
        return result.scalar_one_or_none()

    async def get_tournament_matches(
        self, tournament_id: uuid.UUID, status: MatchStatus | None = None
    ) -> list[Match]:
        filters = [Match.tournament_id == tournament_id]
        if status:
            filters.append(Match.status == status)

        result = await self._db.execute(
            select(Match)
            .where(and_(*filters))
            .options(selectinload(Match.team1), selectinload(Match.team2))
            .order_by(Match.round_number.asc(), Match.match_number.asc())
        )
        return list(result.scalars().all())

    async def get_game(
        self, match_id: uuid.UUID, game_number: int
    ) -> MatchGame | None:
        result = await self._db.execute(
            select(MatchGame).where(
                and_(
                    MatchGame.match_id == match_id,
                    MatchGame.game_number == game_number,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_game(self, match_id: uuid.UUID, game_number: int) -> MatchGame:
        game = MatchGame(match_id=match_id, game_number=game_number)
        self._db.add(game)
        await self._db.flush()
        return game

    async def upsert_game_score(
        self,
        match_id: uuid.UUID,
        game_number: int,
        **kwargs,
    ) -> MatchGame:
        game = await self.get_game(match_id, game_number)
        if game is None:
            game = MatchGame(match_id=match_id, game_number=game_number, **kwargs)
            self._db.add(game)
        else:
            for k, v in kwargs.items():
                setattr(game, k, v)
        await self._db.flush()
        await self._db.refresh(game)
        return game

    async def create_ban_pick(
        self,
        match_id: uuid.UUID,
        team_id: uuid.UUID,
        action: str,
        map_id: uuid.UUID,
        order: int,
    ) -> BanPick:
        bp = BanPick(
            match_id=match_id,
            team_id=team_id,
            action=action,
            map_id=map_id,
            order=order,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(bp)
        await self._db.flush()
        return bp

    async def create_result(
        self,
        match_id: uuid.UUID,
        winner_id: uuid.UUID,
        loser_id: uuid.UUID,
        winner_score: int,
        loser_score: int,
        was_forfeit: bool = False,
        confirmed_by: uuid.UUID | None = None,
    ) -> MatchResult:
        result = MatchResult(
            match_id=match_id,
            winner_id=winner_id,
            loser_id=loser_id,
            winner_score=winner_score,
            loser_score=loser_score,
            was_forfeit=was_forfeit,
            confirmed_by=confirmed_by,
            confirmed_at=datetime.now(timezone.utc) if confirmed_by else None,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(result)
        await self._db.flush()
        return result

    async def bulk_create_player_stats(
        self, stats_list: list[dict]
    ) -> list[PlayerMatchStats]:
        stats = [
            PlayerMatchStats(**data, created_at=datetime.now(timezone.utc))
            for data in stats_list
        ]
        self._db.add_all(stats)
        await self._db.flush()
        return stats

    async def get_match_count_by_status(
        self, tournament_id: uuid.UUID
    ) -> dict[MatchStatus, int]:
        result = await self._db.execute(
            select(Match.status, func.count(Match.id))
            .where(Match.tournament_id == tournament_id)
            .group_by(Match.status)
        )
        return {status: count for status, count in result.all()}
