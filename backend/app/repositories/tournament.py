import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import GameType, RegistrationStatus, TournamentStatus
from app.models.tournament import (
    Bracket,
    Ranking,
    Tournament,
    TournamentRegistration,
)
from app.repositories.base import BaseRepository


class TournamentRepository(BaseRepository[Tournament]):
    def __init__(self, db: AsyncSession):
        super().__init__(Tournament, db)

    async def get_with_details(self, tournament_id: uuid.UUID) -> Tournament | None:
        result = await self._db.execute(
            select(Tournament)
            .where(Tournament.id == tournament_id)
            .options(selectinload(Tournament.organizer))
        )
        return result.scalar_one_or_none()

    async def list_by_game_status(
        self,
        game: GameType | None = None,
        status: TournamentStatus | None = None,
        is_public: bool = True,
        limit: int = 20,
        cursor: uuid.UUID | None = None,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
    ) -> tuple[list[Tournament], bool]:
        filters = [Tournament.is_public == is_public]
        if game:
            filters.append(Tournament.game == game)
        if status:
            filters.append(Tournament.status == status)
        if cursor:
            filters.append(Tournament.id < cursor)
        # 期間（月）で絞り込み: 受付期間 or 開催期間 が [from_at, to_at) と重なる大会
        if from_at and to_at:
            reg_overlap = and_(
                Tournament.registration_start_at < to_at,
                Tournament.registration_end_at >= from_at,
            )
            event_overlap = and_(
                Tournament.start_at < to_at,
                func.coalesce(Tournament.end_at, Tournament.start_at) >= from_at,
            )
            filters.append(or_(reg_overlap, event_overlap))

        stmt = (
            select(Tournament)
            .where(and_(*filters))
            .order_by(Tournament.start_at.desc().nullslast(), Tournament.id.desc())
            .limit(limit + 1)
        )
        result = await self._db.execute(stmt)
        items = list(result.scalars().all())
        has_next = len(items) > limit
        return items[:limit], has_next

    async def get_registered_teams_count(self, tournament_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.count(TournamentRegistration.id)).where(
                and_(
                    TournamentRegistration.tournament_id == tournament_id,
                    TournamentRegistration.status == RegistrationStatus.APPROVED,
                )
            )
        )
        return result.scalar_one()

    async def get_registration(
        self, tournament_id: uuid.UUID, team_id: uuid.UUID
    ) -> TournamentRegistration | None:
        result = await self._db.execute(
            select(TournamentRegistration).where(
                and_(
                    TournamentRegistration.tournament_id == tournament_id,
                    TournamentRegistration.team_id == team_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_registration(
        self,
        tournament_id: uuid.UUID,
        team_id: uuid.UUID,
        notes: str | None = None,
        status: RegistrationStatus = RegistrationStatus.PENDING,
    ) -> TournamentRegistration:
        reg = TournamentRegistration(
            tournament_id=tournament_id,
            team_id=team_id,
            status=status,
            notes=notes,
            registered_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._db.add(reg)
        await self._db.flush()
        return reg

    async def get_approved_registrations(
        self, tournament_id: uuid.UUID
    ) -> list[TournamentRegistration]:
        result = await self._db.execute(
            select(TournamentRegistration)
            .where(
                and_(
                    TournamentRegistration.tournament_id == tournament_id,
                    TournamentRegistration.status == RegistrationStatus.APPROVED,
                )
            )
            .order_by(TournamentRegistration.seed.asc().nullslast())
            .options(selectinload(TournamentRegistration.team))
        )
        return list(result.scalars().all())

    async def create_brackets(
        self, tournament_id: uuid.UUID, brackets_data: list[dict]
    ) -> list[Bracket]:
        brackets = [Bracket(**data, tournament_id=tournament_id) for data in brackets_data]
        self._db.add_all(brackets)
        await self._db.flush()
        return brackets

    async def list_by_organizer(
        self, organizer_id: uuid.UUID, limit: int = 50
    ) -> list[Tournament]:
        result = await self._db.execute(
            select(Tournament)
            .where(Tournament.organizer_id == organizer_id)
            .order_by(Tournament.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_registrations(
        self, tournament_id: uuid.UUID
    ) -> list[TournamentRegistration]:
        result = await self._db.execute(
            select(TournamentRegistration)
            .where(TournamentRegistration.tournament_id == tournament_id)
            .options(selectinload(TournamentRegistration.team))
            .order_by(TournamentRegistration.registered_at.asc())
        )
        return list(result.scalars().all())

    async def get_registration_by_id(
        self, registration_id: uuid.UUID
    ) -> TournamentRegistration | None:
        result = await self._db.execute(
            select(TournamentRegistration)
            .where(TournamentRegistration.id == registration_id)
            .options(selectinload(TournamentRegistration.team))
        )
        return result.scalar_one_or_none()

    async def update_registration_status(
        self, reg: TournamentRegistration, status: RegistrationStatus
    ) -> TournamentRegistration:
        reg.status = status
        reg.updated_at = datetime.now(timezone.utc)
        await self._db.flush()
        return reg

    async def get_brackets_with_matches(self, tournament_id: uuid.UUID) -> list[Bracket]:
        from app.models.match import Match

        result = await self._db.execute(
            select(Bracket)
            .where(Bracket.tournament_id == tournament_id)
            .options(
                selectinload(Bracket.matches).options(
                    selectinload(Match.team1),
                    selectinload(Match.team2),
                    selectinload(Match.winner),
                )
            )
            .order_by(Bracket.round_number.asc())
        )
        return list(result.scalars().all())


class RankingRepository(BaseRepository[Ranking]):
    def __init__(self, db: AsyncSession):
        super().__init__(Ranking, db)

    async def get_tournament_rankings(
        self, tournament_id: uuid.UUID, limit: int = 50
    ) -> list[Ranking]:
        result = await self._db.execute(
            select(Ranking)
            .where(Ranking.tournament_id == tournament_id)
            .options(selectinload(Ranking.team))
            .order_by(Ranking.rank_position.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # 1試合分の成績として渡され、既存値に足し込むべき項目
    _RANKING_CUMULATIVE_FIELDS = frozenset(
        {"points", "wins", "losses", "game_wins", "game_losses"}
    )

    async def upsert_ranking(
        self, tournament_id: uuid.UUID, team_id: uuid.UUID, **stats
    ) -> Ranking:
        """
        1試合分の結果をチームの大会成績に反映する。

        呼び出し側は「その試合で得た値」（勝ちなら wins=1, points=3）を渡すため、
        既存レコードには代入ではなく加算する。代入すると何試合勝っても
        wins=1 のままになる。
        """
        existing = await self._db.execute(
            select(Ranking).where(
                and_(
                    Ranking.tournament_id == tournament_id,
                    Ranking.team_id == team_id,
                )
            )
        )
        ranking = existing.scalar_one_or_none()
        if ranking:
            for key, value in stats.items():
                if key in self._RANKING_CUMULATIVE_FIELDS:
                    setattr(ranking, key, (getattr(ranking, key) or 0) + value)
                else:
                    setattr(ranking, key, value)
            ranking.updated_at = datetime.now(timezone.utc)
        else:
            ranking = Ranking(
                tournament_id=tournament_id,
                team_id=team_id,
                # 順位は直後の recalculate_positions で確定する。
                # NOT NULL 制約があるため仮の値を入れておく
                rank_position=0,
                **stats,
                updated_at=datetime.now(timezone.utc),
            )
            self._db.add(ranking)
        await self._db.flush()
        return ranking

    async def recalculate_positions(self, tournament_id: uuid.UUID) -> None:
        """ポイント降順でランキング順位を再計算。"""
        rankings = await self._db.execute(
            select(Ranking)
            .where(Ranking.tournament_id == tournament_id)
            .order_by(Ranking.points.desc(), Ranking.wins.desc())
        )
        for i, ranking in enumerate(rankings.scalars().all(), start=1):
            ranking.rank_position = i
        await self._db.flush()
