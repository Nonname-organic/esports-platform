"""RankingAggregator — 横断的な競技ランキングを既存データから集約（read-only / ADR-0015）。

RP は完了大会の placement から算出（PLACEMENT_RP）。Tier は RP のしきい値（tier_for）。
Season は時間窓（all / current=四半期）。DB書き込みは行わない。Redis キャッシュ（TTL15分）。
TeamRanking / PlayerRanking（将来）は同一 tier SSOT を利用する。
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import RedisCache
from app.core.storage import resign_stored_url
from app.models.enums import GameType, RegistrationStatus, TournamentStatus
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.models.tournament import Tournament, TournamentRegistration
from app.models.tournament_report import TournamentReport
from app.rankings.tiers import MVP_RP, PLACEMENT_RP, next_tier_for, tier_for, tier_progress
from app.reports.aggregator import TournamentReportAggregator
from app.seasons.utils import season_label
from app.seasons.utils import season_window as _season_window

RANKING_CACHE_TTL = 900  # 15分
DEFAULT_LIMIT = 100
FULL_LIMIT = 100000
TOP4_CUTOFF = 4


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
        """1チームのランクカード。primary=all-time、加えて Current/Previous シーズンRPを内包。"""
        cache_key = f"team_rank_card:{team_id}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        team = await self._db.scalar(select(Team).where(Team.id == team_id))
        if not team:
            raise NotFoundError("チーム", str(team_id))

        tid = str(team_id)
        board = await self.global_team_leaderboard(game=None, season="all", limit=FULL_LIMIT)
        found = next((e for e in board if e["team_id"] == tid), None)
        rp = found["rp"] if found else 0
        tier = tier_for(rp)
        nxt = next_tier_for(rp)

        seasons = await self._team_seasons(tid)
        cur_rp = next((s["rp"] for s in seasons if s["key"] == "current"), 0)
        prev_rp = next((s["rp"] for s in seasons if s["key"] == "previous"), 0)
        best_tier = tier_for(max(cur_rp, prev_rp))
        wins = found["wins"] if found else 0
        losses = found["losses"] if found else 0

        card = {
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
            "current_season_rp": cur_rp,
            "previous_season_rp": prev_rp,
            "best_season_tier": best_tier["label"],
            "best_season_tier_color": best_tier["color"],
            "matches": wins + losses,
            "wins": wins,
            "losses": losses,
            "win_rate": found["win_rate"] if found else 0.0,
            "seasons": seasons,
            "history": await self._team_history(team_id, season="all"),
        }
        await self._cache.set(cache_key, card, ttl=RANKING_CACHE_TTL)
        return card

    async def _team_rp_map(self, *, season: str) -> dict[str, int]:
        board = await self.global_team_leaderboard(game=None, season=season, limit=FULL_LIMIT)
        return {e["team_id"]: e["rp"] for e in board}

    async def _team_seasons(self, team_id_str: str) -> list[dict]:
        """Current / Previous シーズンの {rp, rank, tier}（Season History 用）。"""
        out: list[dict] = []
        for key in ("current", "previous"):
            board = await self.global_team_leaderboard(game=None, season=key, limit=FULL_LIMIT)
            ent = next((e for e in board if e["team_id"] == team_id_str), None)
            s_rp = ent["rp"] if ent else 0
            st = tier_for(s_rp)
            out.append({
                "key": key, "label": season_label(key), "rp": s_rp,
                "rank": ent["rank"] if ent else None,
                "tier_label": st["label"], "tier_color": st["color"],
            })
        return out

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

    # ── Player Ranking（Team RP SSOT の再利用 + MVP ボーナス / ADR-0016） ────────
    async def global_player_leaderboard(
        self, *, game: Optional[str] = None, season: str = "all", limit: int = DEFAULT_LIMIT,
    ) -> list[dict]:
        cache_key = f"ranking:players:{game or 'all'}:{season}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached[:limit]  # type: ignore[index]
        board = await self._compute_players(game=game, season=season)
        await self._cache.set(cache_key, board, ttl=RANKING_CACHE_TTL)
        return board[:limit]

    async def _compute_players(self, *, game: Optional[str], season: str) -> list[dict]:
        team_rp = await self._team_rp_map(season=season)  # {team_id: rp}
        if not team_rp:
            return []
        team_ids = [uuid.UUID(t) for t in team_rp.keys()]

        rows = (await self._db.execute(
            select(TeamMember.player_id, TeamMember.team_id).where(TeamMember.team_id.in_(team_ids))
        )).all()
        agg: dict[str, int] = {}
        for player_id, team_id in rows:
            agg[str(player_id)] = agg.get(str(player_id), 0) + team_rp.get(str(team_id), 0)
        if not agg:
            return []

        mvp_counts = await self._mvp_counts()
        for pid, cnt in mvp_counts.items():
            if pid in agg:
                agg[pid] += cnt * MVP_RP

        ids = [uuid.UUID(p) for p in agg.keys()]
        prows = (await self._db.execute(
            select(Player.id, Player.in_game_name, Player.game).where(Player.id.in_(ids))
        )).all()
        info = {str(r.id): r for r in prows}

        entries: list[dict] = []
        for pid, rp in agg.items():
            r = info.get(pid)
            if not r:
                continue
            pgame = r.game.value if hasattr(r.game, "value") else str(r.game)
            if game and pgame != game:
                continue
            tier = tier_for(rp)
            entries.append({
                "player_id": pid,
                "in_game_name": r.in_game_name,
                "game": pgame,
                "rp": rp,
                "tier_key": tier["key"],
                "tier_label": tier["label"],
                "tier_color": tier["color"],
                "progress": tier_progress(rp),
                "mvps": mvp_counts.get(pid, 0),
            })
        entries.sort(key=lambda e: (e["rp"], e["mvps"]), reverse=True)
        for i, e in enumerate(entries, 1):
            e["rank"] = i
        return entries

    async def player_rank_card(self, player_id: uuid.UUID) -> dict:
        """1プレイヤーのランクカード（Team RP 合計 + MVP / all-time primary + season内訳）。"""
        cache_key = f"player_rank_card:{player_id}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        player = await self._db.scalar(select(Player).where(Player.id == player_id))
        if not player:
            raise NotFoundError("プレイヤー", str(player_id))

        team_ids = [str(t) for t in (await self._db.execute(
            select(TeamMember.team_id).where(TeamMember.player_id == player_id)
        )).scalars().all()]
        mvp = await self._player_mvp(player_id)

        async def _rp(season: str) -> int:
            m = await self._team_rp_map(season=season)
            return sum(m.get(t, 0) for t in team_ids)

        rp = await _rp("all") + mvp * MVP_RP
        tier = tier_for(rp)
        nxt = next_tier_for(rp)

        pid = str(player_id)
        # 順位は player leaderboard（各シーズン）から
        seasons: list[dict] = []
        for key in ("current", "previous"):
            pboard_k = await self.global_player_leaderboard(game=None, season=key, limit=FULL_LIMIT)
            ent = next((e for e in pboard_k if e["player_id"] == pid), None)
            s_rp = ent["rp"] if ent else 0
            st = tier_for(s_rp)
            seasons.append({
                "key": key, "label": season_label(key), "rp": s_rp,
                "rank": ent["rank"] if ent else None,
                "tier_label": st["label"], "tier_color": st["color"],
            })
        cur_rp = next((s["rp"] for s in seasons if s["key"] == "current"), 0)
        prev_rp = next((s["rp"] for s in seasons if s["key"] == "previous"), 0)
        best_tier = tier_for(max(cur_rp, prev_rp))

        pboard = await self.global_player_leaderboard(game=None, season="all", limit=FULL_LIMIT)
        found = next((e for e in pboard if e["player_id"] == pid), None)

        # 勝敗は既存 CareerAggregationService を再利用
        from app.services.career_service import CareerAggregationService
        try:
            career = await CareerAggregationService(self._db, self._cache).get_player_career(player_id)
        except Exception:
            career = {}

        card = {
            "player_id": pid,
            "in_game_name": player.in_game_name,
            "game": player.game.value if hasattr(player.game, "value") else str(player.game),
            "rp": rp,
            "rank": found["rank"] if found else None,
            "total_ranked": len(pboard),
            "tier_key": tier["key"],
            "tier_label": tier["label"],
            "tier_color": tier["color"],
            "next_tier_label": nxt["label"] if nxt else None,
            "next_tier_rp": nxt["min_rp"] if nxt else None,
            "progress": tier_progress(rp),
            "current_season_rp": cur_rp,
            "previous_season_rp": prev_rp,
            "best_season_tier": best_tier["label"],
            "best_season_tier_color": best_tier["color"],
            "mvps": mvp,
            "championships": int(career.get("championships", 0) or 0),
            "matches": int(career.get("total_matches", 0) or 0),
            "wins": int(career.get("total_wins", 0) or 0),
            "losses": int(career.get("total_losses", 0) or 0),
            "win_rate": float(career.get("win_rate", 0.0) or 0.0),
            "seasons": seasons,
        }
        await self._cache.set(cache_key, card, ttl=RANKING_CACHE_TTL)
        return card

    async def _mvp_counts(self) -> dict[str, int]:
        """全プレイヤーのMVP数（match_mvps）。テーブルが無ければ空（防御的）。"""
        try:
            rows = (await self._db.execute(text("SELECT player_id, COUNT(*) FROM match_mvps GROUP BY player_id"))).all()
            return {str(r[0]): int(r[1]) for r in rows}
        except Exception:
            return {}

    async def _player_mvp(self, player_id: uuid.UUID) -> int:
        try:
            row = (await self._db.execute(
                text("SELECT COUNT(*) FROM match_mvps WHERE player_id = :pid"), {"pid": str(player_id)}
            )).first()
            return int(row[0]) if row and row[0] is not None else 0
        except Exception:
            return 0
