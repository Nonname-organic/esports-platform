import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.services.ranking import RankingService

logger = logging.getLogger(__name__)


async def handle_match_result(
    body: dict, db: AsyncSession, cache: RedisCache
) -> None:
    """試合結果イベントを受け取りランキングを更新する。"""
    tournament_id = uuid.UUID(body["tournament_id"])
    winner_id = uuid.UUID(body["winner_id"])
    loser_id = uuid.UUID(body["loser_id"])
    winner_score = body.get("winner_score", 1)
    loser_score = body.get("loser_score", 0)

    ranking_service = RankingService(db, cache)
    await ranking_service.update_after_match(
        tournament_id=tournament_id,
        winner_id=winner_id,
        loser_id=loser_id,
        winner_game_wins=winner_score,
        loser_game_wins=loser_score,
    )
    logger.info(
        f"Ranking updated for tournament={tournament_id} "
        f"winner={winner_id} loser={loser_id}"
    )
