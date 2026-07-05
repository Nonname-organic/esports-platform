"""RankingAggregator — 横断的な競技ランキングを既存データから集約（read-only / ADR-0015）。

RP は完了大会の placement から算出（PLACEMENT_RP）。Tier は RP のしきい値（tier_for）。
Season は時間窓（all / current=四半期）。DB書き込みは行わない。Redis キャッシュ（TTL15分）。
TeamRanking / PlayerRanking（将来）は同一 tier SSOT を利用する。
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
from app.models.enums import GameType, RegistrationStatus, TournamentStatus
from app.models.team import Team
from app.models.tournament import Tournament, TournamentRegistration
from app.models.tournament_report import TournamentReport
from app.rankings.tiers import PLACEMENT_RP, next_tier_for, tier_for, tier_progress
from app.reports.aggregator import TournamentReportAggregator

RANKING_CACHE_TTL = 900  # 15分
DEFAULT_LIMIT = 100
FULL_LIMIT = 100000
TOP4_CUTOFF = 4


def _season_window(season: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """season='current' のとき現在の四半期 [start, end) を返す。'all' は (None, None)。"""
    if season != "current":
        return None, None
    now = datetime.now(timezone.utc)
    q = (now.month - 1) // 3
    start_month = q * 3 + 1
    start = datetime(now.year, start_month, 1, tzinfo=timezone.utc)
    end = (
        datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        if start_month + 3 > 12
        else datetime(now.year, start_month + 3, 1, tzinfo=timezone.utc)
    )
    return start, end


def _placements(data: dict) -> dict[str, str]:
    """report data から team_id -> placement ラベルの写像を作る。"""
    champ = (data.get("champion") or {}).get("team_id")
    runner = (data.get("runner_up") or {}).get("team_id")
    out: dict[str, str] = {}
    for idx, s in enumerate(data.get("standings") or []):
        tid = s.get("team_id")
        if not tid:
            continue
        if tid == champ:
            out[tid] = "champion"
        elif tid == runner:
            out[tid] = "runner_up"
        elif idx < TOP4_CUTOFF:
            out[tid] = "top4"
        else:
            out[tid] = "participated"
    if champ and champ not in out:
        out[champ] = "champion"
    if runner and runner not in out:
        out[runner] = "runner_up"
    return out


class RankingAggregator:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    # ── グローバル/シーズン リーダーボード ────────────────────────────────────
    async def global_team_leaderboard(
        self, *, game: Optional[str] = None, season: str = "all", limit: int = DEFAULT_LIMIT,
    ) -> list[dict]:
        cache_key = f"ranking:{game or 'all'}:{season}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached[:limit]  # type: ignore[index]

        board = await self._compute(game=game, season=season)
        await self._cache.set(cache_key, board, ttl=RANKING_CACHE_TTL)
        return board[:limit]

    async def _compute(self, *, game: Optional[str], season: str) -> list[dict]:
        start, end = _season_window(season)

        q = select(Tournament.id).where(Tournament.status == TournamentStatus.COMPLETED)
        if game:
            try:
                q = q.where(Tournament.game == GameType(game))
            except ValueError:
                return []
        if start and end:
            q = q.where(Tournament.end_at >= start, Tournament.end_at < end)
        tournament_ids = list((await self._db.execute(q)).scalars().all())

        agg: dict[str, dict] = {}
        for tid in tournament_ids:
            data = await self._report_data(tid)
            if not data:
                continue
            placements = _placements(data)
            standings = {s.get("team_id"): s for s in (data.get("standings") or []) if s.get("team_id")}
            for team_id, label in placements.items():
                a = agg.setdefault(team_id, {
                    "rp": 0, "tournaments": 0, "championships": 0, "runner_ups": 0, "top4": 0,
                    "wins": 0, "losses": 0,
                })
                a["rp"] += PLACEMENT_RP.get(label, 0)
                a["tournaments"] += 1
                if label == "champion":
                    a["championships"] += 1
                elif label == "runner_up":
                    a["runner_ups"] += 1
                elif label == "top4":
                    a["top4"] += 1
                s = standings.get(team_id) or {}
                a["wins"] += int(s.get("wins", 0) or 0)
                a["losses"] += int(s.get("losses", 0) or 0)

        if not agg:
            return []

        ids = [uuid.UUID(t) for t in agg.keys()]
        rows = (await self._db.execute(
            select(Team.id, Team.name, Team.tag, Team.logo_url, Team.game).where(Team.id.in_(ids))
        )).all()
        info = {str(r.id): r for r in rows}

        entries: list[dict] = []
        for team_id, a in agg.items():
            r = info.get(team_id)
            if not r:
                continue
            rp = a["rp"]
            tier = tier_for(rp)
            total = a["wins"] + a["losses"]
            entries.append({
                "team_id": team_id,
                "team_name": r.name,
                "team_tag": r.tag,
                "team_logo_url": resign_stored_url(r.logo_url),
                "game": r.game.value if hasattr(r.game, "value") else str(r.game),
                "rp": rp,
                "tier_key": tier["key"],
                "tier_label": tier["label"],
                "tier_color": tier["color"],
                "progress": tier_progress(rp),
                "tournaments": a["tournaments"],
                "championships": a["championships"],
                "runner_ups": a["runner_ups"],
                "top4": a["top4"],
                "wins": a["wins"],
                "losses": a["losses"],
                "win_rate": round(a["wins"] / total, 4) if total else 0.0,
            })

        entries.sort(key=lambda e: (e["rp"], e["championships"], e["wins"]), reverse=True)
        for i, e in enumerate(entries, 1):
            e["rank"] = i
        return entries

    # ── チーム・ランクカード（Team Page 連携用に完全共通化） ───────────────────
    async def team_rank_card(self, team_id: uuid.UUID, *, season: str = "all") -> dict:
        """1チームのランクカード（順位 / RP / Tier / 次Tier進捗 / History）。"""
        team = await self._db.scalar(select(Team).where(Team.id == team_id))
        if not team:
            raise NotFoundError("チーム", str(team_id))

        # キャッシュ済み全体ボードを再利用して順位を引く
        board = await self.global_team_leaderboard(game=None, season=season, limit=FULL_LIMIT)
        tid = str(team_id)
        found = next((e for e in board if e["team_id"] == tid), None)
        rp = found["rp"] if found else 0
        tier = tier_for(rp)
        nxt = next_tier_for(rp)
        return {
            "team_id": tid,
            "team_name": team.name,
            "team_tag": team.tag,
            "game": team.game.value if hasattr(team.game, "value") else str(team.game),
            "rp": rp,
            "rank": found["rank"] if found else None,
            "total_ranked": len(board),
            "tier_key": tier["key"],
            "tier_label": tier["label"],
            "tier_color": tier["color"],
            "next_tier_label": nxt["label"] if nxt else None,
            "next_tier_rp": nxt["min_rp"] if nxt else None,
            "progress": tier_progress(rp),
            "championships": found["championships"] if found else 0,
            "tournaments": found["tournaments"] if found else 0,
            "history": await self._team_history(team_id, season=season),
        }

    async def _team_history(self, team_id: uuid.UUID, *, season: str) -> list[dict]:
        """チームの RP 履歴（完了大会ごと / 時系列・累積RP）。"""
        start, end = _season_window(season)
        q = (
            select(Tournament.id, Tournament.name, Tournament.end_at)
            .join(TournamentRegistration, TournamentRegistration.tournament_id == Tournament.id)
            .where(
                TournamentRegistration.team_id == team_id,
                TournamentRegistration.status == RegistrationStatus.APPROVED,
                Tournament.status == TournamentStatus.COMPLETED,
            )
        )
        if start and end:
            q = q.where(Tournament.end_at >= start, Tournament.end_at < end)
        q = q.order_by(Tournament.end_at.asc())
        rows = (await self._db.execute(q)).all()

        cumulative = 0
        out: list[dict] = []
        for tid, name, end_at in rows:
            data = await self._report_data(tid)
            if not data:
                continue
            label = _placements(data).get(str(team_id))
            if not label:
                continue
            gained = PLACEMENT_RP.get(label, 0)
            cumulative += gained
            out.append({
                "tournament_id": str(tid),
                "tournament_name": name,
                "ended_at": end_at.isoformat() if end_at else None,
                "placement": label,
                "rp_gained": gained,
                "cumulative_rp": cumulative,
            })
        return out

    async def _report_data(self, tournament_id: uuid.UUID) -> Optional[dict]:
        """materialized Report を優先、無ければオンザフライ集計。"""
        report = await self._db.scalar(
            select(TournamentReport).where(TournamentReport.tournament_id == tournament_id)
        )
        if report and report.data:
            return report.data
        try:
            return await TournamentReportAggregator(self._db).aggregate(tournament_id)
        except Exception:
            return None
