"""StatsService — 公開ライブ統計（Live Experience / 読み取り専用）。

Live Status Bar と Statistics Card 用の集約値を安価な COUNT で算出する。
Redis に短TTL(15秒)でキャッシュし「ライブ感」と負荷のバランスを取る。
新テーブルは作らない（Growth Policy: Additive・read-only）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.models.domain_event import DomainEvent
from app.models.enums import MatchStatus, TournamentStatus
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.tournament_report import TournamentReport

STATS_CACHE_TTL = 15          # 秒（ライブ感優先の短TTL）
ONLINE_WINDOW_MIN = 30        # オンライン概算の対象窓（分）


class StatsService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    async def overview(self) -> dict:
        cache_key = "stats:overview"
        cached = await self._cache.get(cache_key)
        if cached:
            return cached  # type: ignore[return-value]
        data = await self._compute()
        await self._cache.set(cache_key, data, ttl=STATS_CACHE_TTL)
        return data

    async def _compute(self) -> dict:
        ongoing_tournaments = await self._db.scalar(
            select(func.count()).select_from(Tournament).where(Tournament.status == TournamentStatus.ONGOING)
        )
        registration_open_tournaments = await self._db.scalar(
            select(func.count()).select_from(Tournament).where(Tournament.status == TournamentStatus.REGISTRATION_OPEN)
        )
        ongoing_matches = await self._db.scalar(
            select(func.count()).select_from(Match).where(Match.status == MatchStatus.ONGOING)
        )
        total_tournaments = await self._db.scalar(select(func.count()).select_from(Tournament))
        total_teams = await self._db.scalar(select(func.count()).select_from(Team))
        total_players = await self._db.scalar(select(func.count()).select_from(Player))
        total_matches = await self._db.scalar(select(func.count()).select_from(Match))
        # 総優勝チーム数 = 完了大会数（1大会につき王者1）。MVP受賞数は既存テーブルから防御的に集計。
        champions = await self._db.scalar(
            select(func.count()).select_from(Tournament).where(Tournament.status == TournamentStatus.COMPLETED)
        )

        return {
            "live": {
                "ongoing_tournaments": int(ongoing_tournaments or 0),
                "registration_open_tournaments": int(registration_open_tournaments or 0),
                "ongoing_matches": int(ongoing_matches or 0),
                "online_participants": await self._estimate_online(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "totals": {
                "tournaments": int(total_tournaments or 0),
                "teams": int(total_teams or 0),
                "players": int(total_players or 0),
                "matches": int(total_matches or 0),
                "champions": int(champions or 0),
                "mvps": await self._count_mvps(),
            },
        }

    async def _count_mvps(self) -> int:
        """MVP受賞総数。データ源（match_mvps）が無い環境では 0（防御的）。"""
        try:
            row = (await self._db.execute(text("SELECT COUNT(*) FROM match_mvps"))).first()
            return int(row[0]) if row and row[0] is not None else 0
        except Exception:
            return 0

    async def recent_champions(self, limit: int = 3) -> list[dict]:
        """直近の優勝チーム（materialized な TournamentReport から / 読み取り専用）。"""
        cache_key = f"stats:champions:{limit}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        rows = (await self._db.execute(
            select(TournamentReport.data, Tournament.id, Tournament.name, Tournament.game, Tournament.end_at)
            .join(Tournament, Tournament.id == TournamentReport.tournament_id)
            .where(Tournament.status == TournamentStatus.COMPLETED)
            .order_by(TournamentReport.generated_at.desc())
            .limit(limit)
        )).all()

        out: list[dict] = []
        for data, tid, name, game, end_at in rows:
            d = data or {}
            champ = d.get("champion") or {}
            mvp = d.get("mvp")
            mvp_name = mvp.get("player_name") if isinstance(mvp, dict) else (mvp if isinstance(mvp, str) else None)
            if not champ.get("team_name"):
                continue
            out.append({
                "tournament_id": str(tid),
                "tournament_name": name,
                "game": game.value if hasattr(game, "value") else str(game),
                "champion_team_id": champ.get("team_id"),
                "champion_team_name": champ.get("team_name"),
                "mvp_name": mvp_name,
                "ended_at": end_at.isoformat() if end_at else None,
            })
        await self._cache.set(cache_key, out, ttl=60)
        return out

    async def _estimate_online(self) -> int:
        """直近アクティブなactor数の概算（domain_events の distinct actor / 過去30分）。

        リアルなプレゼンス基盤は持たないため近似値。0 の場合はフロント側が
        Mock フォールバックで賑わいを補完できる（数値の出所はどちらでも良い設計）。
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=ONLINE_WINDOW_MIN)
        count = await self._db.scalar(
            select(func.count(func.distinct(DomainEvent.actor_id)))
            .where(DomainEvent.actor_id.isnot(None), DomainEvent.created_at >= cutoff)
        )
        return int(count or 0)
