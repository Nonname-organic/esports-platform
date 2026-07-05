"""TournamentImmersionService — 大会詳細ページの Read Model（ADR-0017）。

既存 Repository を read-only で束ね、没入UI用の表示DTOを返す。保存禁止・集計のみ。
Live UI は Event に依存せずこの Read Model をポーリングする（将来 WS/SSE へ差し替え可）。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import RedisCache
from app.core.storage import resign_stored_url
from app.models.enums import MatchStatus, TournamentStatus
from app.models.match import Match
from app.repositories.match import MatchRepository
from app.repositories.tournament import TournamentRepository
from app.repositories.tournament_report import TournamentReportRepository

OVERVIEW_TTL = 30
STATS_TTL = 30
LIVE_TTL = 10
UPCOMING_LIMIT = 5


def _stream_platform(url: str) -> str:
    u = url.lower()
    if "twitch" in u:
        return "twitch"
    if "youtube" in u or "youtu.be" in u:
        return "youtube"
    if "kick" in u:
        return "kick"
    return "other"


class TournamentImmersionService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._repo = TournamentRepository(db)
        self._matches = MatchRepository(db)
        self._reports = TournamentReportRepository(db)
        self._cache = cache

    # ── public ────────────────────────────────────────────────────────────────
    async def overview(self, tournament_id: uuid.UUID) -> dict:
        key = f"tournament_overview:{tournament_id}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        data = await self._overview(tournament_id)
        await self._cache.set(key, data, ttl=OVERVIEW_TTL)
        return data

    async def live_status(self, tournament_id: uuid.UUID) -> dict:
        key = f"tournament_live:{tournament_id}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        data = await self._live(tournament_id)
        await self._cache.set(key, data, ttl=LIVE_TTL)
        return data

    async def statistics(self, tournament_id: uuid.UUID) -> dict:
        key = f"tournament_statistics:{tournament_id}"
        cached = await self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        data = await self._statistics(tournament_id)
        await self._cache.set(key, data, ttl=STATS_TTL)
        return data

    # ── impl ──────────────────────────────────────────────────────────────────
    async def _overview(self, tournament_id: uuid.UUID) -> dict:
        t = await self._repo.get_by_id(tournament_id)
        if not t:
            raise NotFoundError("大会", str(tournament_id))
        matches = await self._matches.get_tournament_matches_full(tournament_id)
        registered = await self._repo.get_registered_teams_count(tournament_id)

        ongoing = [m for m in matches if m.status == MatchStatus.ONGOING]
        current = self._match_dto(ongoing[0]) if ongoing else None

        # Stream: rules JSONB > 現在試合の stream_url
        stream = None
        rules = t.rules or {}
        stream_url = None
        if isinstance(rules, dict):
            stream_url = rules.get("stream_url") or rules.get("stream")
        if not stream_url and ongoing and ongoing[0].stream_url:
            stream_url = ongoing[0].stream_url
        if stream_url:
            stream = {"url": stream_url, "platform": _stream_platform(stream_url), "is_live": bool(ongoing)}

        result = None
        if t.status == TournamentStatus.COMPLETED:
            result = await self._result(tournament_id)

        return {
            "id": str(t.id),
            "name": t.name,
            "game": t.game.value if hasattr(t.game, "value") else str(t.game),
            "format": t.format.value if hasattr(t.format, "value") else str(t.format),
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "banner_url": resign_stored_url(t.banner_url),
            "prize_pool": float(t.prize_pool) if t.prize_pool is not None else None,
            "prize_currency": t.prize_currency,
            "start_at": t.start_at.isoformat() if t.start_at else None,
            "end_at": t.end_at.isoformat() if t.end_at else None,
            "registration_end_at": t.registration_end_at.isoformat() if t.registration_end_at else None,
            "max_teams": t.max_teams,
            "registered_teams": registered,
            "current_match": current,
            "stream": stream,
            "result": result,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _live(self, tournament_id: uuid.UUID) -> dict:
        t = await self._repo.get_by_id(tournament_id)
        if not t:
            raise NotFoundError("大会", str(tournament_id))
        matches = await self._matches.get_tournament_matches_full(tournament_id)

        total = len(matches)
        completed = sum(1 for m in matches if m.status == MatchStatus.COMPLETED)
        ongoing = [m for m in matches if m.status == MatchStatus.ONGOING]
        scheduled = [m for m in matches if m.status == MatchStatus.SCHEDULED]

        # current round = 未完了の最小ラウンド。全完了なら最大ラウンド。
        pending_rounds = [m.round_number for m in matches if m.status != MatchStatus.COMPLETED]
        current_round = min(pending_rounds) if pending_rounds else (max((m.round_number for m in matches), default=None))

        upcoming = [
            self._match_dto(m) for m in sorted(
                (m for m in scheduled if m.team1_id and m.team2_id),
                key=lambda m: (m.scheduled_at or datetime.max.replace(tzinfo=timezone.utc), m.round_number, m.match_number),
            )
        ][:UPCOMING_LIMIT]

        return {
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "total_matches": total,
            "completed_matches": completed,
            "ongoing_matches": len(ongoing),
            "scheduled_matches": len(scheduled),
            "remaining_matches": max(total - completed, 0),
            "progress": round(completed / total, 4) if total else 0.0,
            "current_round": current_round,
            "start_at": t.start_at.isoformat() if t.start_at else None,
            "end_at": t.end_at.isoformat() if t.end_at else None,
            "current_match": self._match_dto(ongoing[0]) if ongoing else None,
            "live_matches": [self._match_dto(m) for m in ongoing],
            "upcoming": upcoming,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _statistics(self, tournament_id: uuid.UUID) -> dict:
        t = await self._repo.get_by_id(tournament_id)
        if not t:
            raise NotFoundError("大会", str(tournament_id))
        matches = await self._matches.get_tournament_matches_full(tournament_id)
        registered = await self._repo.get_registered_teams_count(tournament_id)

        total = len(matches)
        completed = sum(1 for m in matches if m.status == MatchStatus.COMPLETED)
        result = await self._result(tournament_id) if t.status == TournamentStatus.COMPLETED else None

        return {
            "participants": registered,
            "max_teams": t.max_teams,
            "matches": total,
            "completed_matches": completed,
            "completion_rate": round(completed / total, 4) if total else 0.0,
            "prize_pool": float(t.prize_pool) if t.prize_pool is not None else None,
            "prize_currency": t.prize_currency,
            "mvp": (result or {}).get("mvp") if result else None,
            "champion": (result or {}).get("champion") if result else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _result(self, tournament_id: uuid.UUID) -> Optional[dict]:
        report = await self._reports.get_by_tournament(tournament_id)
        data = report.data if report and report.data else None
        if not data:
            return None
        mvp = data.get("mvp")
        mvp_name = mvp.get("player_name") if isinstance(mvp, dict) else (mvp if isinstance(mvp, str) else None)
        return {
            "champion": data.get("champion"),
            "runner_up": data.get("runner_up"),
            "mvp": mvp_name,
        }

    # ── serialization ──────────────────────────────────────────────────────────
    def _team_dto(self, team) -> Optional[dict]:
        if not team:
            return None
        return {
            "id": str(team.id),
            "name": team.name,
            "tag": team.tag,
            "logo_url": resign_stored_url(team.logo_url),
        }

    def _match_dto(self, m: Match) -> dict:
        score1 = sum(1 for g in m.games if g.winner_id and g.winner_id == m.team1_id)
        score2 = sum(1 for g in m.games if g.winner_id and g.winner_id == m.team2_id)
        current_game = None
        if m.games:
            undecided = [g for g in m.games if not g.winner_id]
            g = undecided[0] if undecided else m.games[-1]
            current_game = {
                "game_number": g.game_number,
                "map": g.map.display_name if getattr(g, "map", None) else None,
                "t1_rounds": g.team1_score or 0,
                "t2_rounds": g.team2_score or 0,
            }
        return {
            "id": str(m.id),
            "round_number": m.round_number,
            "status": m.status.value if hasattr(m.status, "value") else str(m.status),
            "format": m.format.value if hasattr(m.format, "value") else str(m.format),
            "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
            "stream_url": m.stream_url,
            "team1": self._team_dto(m.team1),
            "team2": self._team_dto(m.team2),
            "score1": score1,
            "score2": score2,
            "current_game": current_game,
        }
