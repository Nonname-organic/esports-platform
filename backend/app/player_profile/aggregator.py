"""PlayerProfileAggregator — 世界レベル Player Profile の Read Model（ADR-0018）。

既存 CareerAggregationService / RankingAggregator / Achievement / Activity を read-only で
合成し、AI Analysis（Provider）を付加する。保存禁止。Redis キャッシュ。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import RedisCache
from app.core.storage import resign_stored_url
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.player_profile.analysis import PlayerAnalysisProvider, RuleBasedAnalysisProvider
from app.player_profile.history import PlayerHistoryAggregator
from app.rankings.aggregator import RankingAggregator
from app.services.activity_service import ActivityService
from app.services.career_service import CareerAggregationService

PROFILE_TTL = 900     # 15分
ANALYSIS_TTL = 1800   # 30分


class PlayerProfileAggregator:
    def __init__(self, db: AsyncSession, cache: RedisCache, *, provider: Optional[PlayerAnalysisProvider] = None):
        self._db = db
        self._cache = cache
        # AI Provider は差し替え可能（現状 RuleBased）
        self._provider: PlayerAnalysisProvider = provider or RuleBasedAnalysisProvider()

    async def analysis(self, player_id: uuid.UUID) -> dict:
        key = f"player_analysis:{player_id}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        player = await self._require_player(player_id)
        career = await CareerAggregationService(self._db, self._cache).get_player_career(player_id)
        data = await self._provider.analyze(player=self._basic_dict(player, None), career=career)
        await self._cache.set(key, data, ttl=ANALYSIS_TTL)
        return data

    async def history(self, player_id: uuid.UUID) -> list[dict]:
        await self._require_player(player_id)
        return await PlayerHistoryAggregator(self._db).history(player_id)

    async def profile(self, player_id: uuid.UUID) -> dict:
        key = f"player_profile:{player_id}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        player = await self._require_player(player_id)
        team = await self._active_team(player_id)
        career = await CareerAggregationService(self._db, self._cache).get_player_career(player_id)
        basic = self._basic_dict(player, team)

        rank = await RankingAggregator(self._db, self._cache).player_rank_card(player_id)
        achievements = await CareerAggregationService(self._db, self._cache).get_player_achievements(player_id)
        history = await PlayerHistoryAggregator(self._db).history(player_id)
        analysis = await self._provider.analyze(player=basic, career=career)
        activity = await ActivityService(self._db).player_activity(player_id, limit=10)

        result = {
            "basic": basic,
            "career": career,
            "rank": rank,
            "achievements": achievements,
            "history": history,
            "analysis": analysis,
            "activity": activity,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._cache.set(key, result, ttl=PROFILE_TTL)
        return result

    # ── helpers ─────────────────────────────────────────────────────────────
    async def _require_player(self, player_id: uuid.UUID) -> Player:
        player = await self._db.scalar(select(Player).where(Player.id == player_id))
        if not player:
            raise NotFoundError("プレイヤー", str(player_id))
        return player

    async def _active_team(self, player_id: uuid.UUID) -> Optional[dict]:
        row = (await self._db.execute(
            select(Team.id, Team.name, Team.tag, Team.logo_url)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.player_id == player_id, TeamMember.left_at.is_(None))
            .limit(1)
        )).first()
        if not row:
            return None
        return {"id": str(row.id), "name": row.name, "tag": row.tag, "logo_url": resign_stored_url(row.logo_url)}

    def _basic_dict(self, player: Player, team: Optional[dict]) -> dict:
        return {
            "id": str(player.id),
            "in_game_name": player.in_game_name,
            "game": player.game.value if hasattr(player.game, "value") else str(player.game),
            "bio": player.bio,
            "main_role": player.main_role,
            "avatar_url": resign_stored_url(getattr(player, "avatar_url", None)),
            "team": team,
        }
