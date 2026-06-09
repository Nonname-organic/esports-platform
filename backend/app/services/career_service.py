"""
CareerAggregationService
- 既存の Match / MatchGame / PlayerMatchStats / rankings / ratings / achievements を集約
- Player Career / Team Career を算出
- Redisキャッシュ（TTL 10分）
- 試合終了・ランキング更新時に invalidate して再集計

設計方針:
- 永続テーブル(player_careers/team_careers)は重い集計のスナップショット用に確保
- 通常はオンザフライ集計 + Redisキャッシュで応答（整合性とシンプルさ優先）
"""

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.models.enums import MatchStatus
from app.models.match import Match, MatchGame, PlayerMatchStats, Map
from app.models.player import Player
from app.models.team import Team


CAREER_CACHE_TTL = 600  # 10分


class CareerAggregationService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    # ══════════════════════════════════════════════════════════════════════════
    # Player Career
    # ══════════════════════════════════════════════════════════════════════════
    async def get_player_career(self, player_id: uuid.UUID) -> dict:
        cache_key = f"career:player:{player_id}"
        cached = await self._cache.get(cache_key)
        if cached:
            return cached  # type: ignore[return-value]

        result = await self._aggregate_player(player_id)
        await self._cache.set(cache_key, result, ttl=CAREER_CACHE_TTL)
        return result

    async def _aggregate_player(self, player_id: uuid.UUID) -> dict:
        player = await self._db.scalar(select(Player).where(Player.id == player_id))
        if not player:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("プレイヤー", str(player_id))

        # 全プレイヤーゲーム統計を取得（match_game + match をJOIN）
        rows = (await self._db.execute(
            select(
                PlayerMatchStats.agent,
                PlayerMatchStats.team_id,
                PlayerMatchStats.kills,
                PlayerMatchStats.deaths,
                PlayerMatchStats.assists,
                PlayerMatchStats.score,
                PlayerMatchStats.first_bloods,
                MatchGame.team1_score,
                MatchGame.team2_score,
                MatchGame.winner_id.label("game_winner"),
                MatchGame.map_id,
                Match.id.label("match_id"),
                Match.winner_id.label("match_winner"),
                Match.tournament_id,
            )
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .where(
                PlayerMatchStats.player_id == player_id,
                Match.status == MatchStatus.COMPLETED,
            )
        )).all()

        # マップ名解決
        map_names = await self._load_map_names()

        # 集計
        total_kills = total_deaths = total_assists = total_score = 0
        total_rounds = 0
        game_count = len(rows)

        agent_agg: dict[str, dict] = defaultdict(lambda: {"games": 0, "wins": 0, "kda_sum": 0.0})
        map_agg: dict[uuid.UUID, dict] = defaultdict(lambda: {"games": 0, "wins": 0})
        match_results: dict[uuid.UUID, bool] = {}  # match_id -> won
        tournaments: set = set()

        for r in rows:
            total_kills += r.kills
            total_deaths += r.deaths
            total_assists += r.assists
            total_score += r.score
            total_rounds += (r.team1_score or 0) + (r.team2_score or 0)
            tournaments.add(r.tournament_id)

            won_game = r.game_winner == r.team_id
            kda = (r.kills + r.assists) / max(r.deaths, 1)

            if r.agent:
                a = agent_agg[r.agent]
                a["games"] += 1
                a["wins"] += 1 if won_game else 0
                a["kda_sum"] += kda

            if r.map_id:
                m = map_agg[r.map_id]
                m["games"] += 1
                m["wins"] += 1 if won_game else 0

            # マッチ単位の勝敗（チームが勝者か）
            match_results[r.match_id] = (r.match_winner == r.team_id)

        total_matches = len(match_results)
        total_wins = sum(1 for won in match_results.values() if won)
        total_losses = total_matches - total_wins
        win_rate = total_wins / total_matches if total_matches else 0.0
        rounds = max(total_rounds, 1)

        # レーティング・実績取得
        rating = await self._get_player_rating(player_id, player.game.value)
        championships, mvp_count = await self._get_player_titles(player_id)

        return {
            "player_id": str(player_id),
            "in_game_name": player.in_game_name,
            "game": player.game.value,
            "total_matches": total_matches,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "win_rate": round(win_rate, 4),
            "championships": championships,
            "mvp_count": mvp_count,
            "tournaments_played": len(tournaments),
            "current_rating": rating.get("current") if rating else None,
            "peak_rating": rating.get("peak") if rating else None,
            "avg_acs": round(total_score / rounds, 1) if rounds else 0.0,
            "avg_kda": round((total_kills + total_assists) / max(total_deaths, 1), 2),
            "avg_kills": round(total_kills / game_count, 1) if game_count else 0.0,
            "avg_deaths": round(total_deaths / game_count, 1) if game_count else 0.0,
            "avg_assists": round(total_assists / game_count, 1) if game_count else 0.0,
            "agent_usage": [
                {
                    "agent": agent,
                    "games": d["games"],
                    "wins": d["wins"],
                    "win_rate": round(d["wins"] / d["games"], 4) if d["games"] else 0.0,
                    "avg_kda": round(d["kda_sum"] / d["games"], 2) if d["games"] else 0.0,
                }
                for agent, d in sorted(agent_agg.items(), key=lambda x: -x[1]["games"])
            ],
            "map_performance": [
                {
                    "map_name": map_names.get(mid, str(mid)[:8]),
                    "games": d["games"],
                    "wins": d["wins"],
                    "win_rate": round(d["wins"] / d["games"], 4) if d["games"] else 0.0,
                }
                for mid, d in sorted(map_agg.items(), key=lambda x: -x[1]["games"])
            ],
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Team Career
    # ══════════════════════════════════════════════════════════════════════════
    async def get_team_career(self, team_id: uuid.UUID) -> dict:
        cache_key = f"career:team:{team_id}"
        cached = await self._cache.get(cache_key)
        if cached:
            return cached  # type: ignore[return-value]

        result = await self._aggregate_team(team_id)
        await self._cache.set(cache_key, result, ttl=CAREER_CACHE_TTL)
        return result

    async def _aggregate_team(self, team_id: uuid.UUID) -> dict:
        team = await self._db.scalar(select(Team).where(Team.id == team_id))
        if not team:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("チーム", str(team_id))

        # チームの全試合（team1 or team2）
        matches = (await self._db.execute(
            select(Match).where(
                ((Match.team1_id == team_id) | (Match.team2_id == team_id)),
                Match.status == MatchStatus.COMPLETED,
            )
        )).scalars().all()

        total_matches = len(matches)
        total_wins = sum(1 for m in matches if m.winner_id == team_id)
        total_losses = total_matches - total_wins
        win_rate = total_wins / total_matches if total_matches else 0.0
        tournaments = {m.tournament_id for m in matches}

        # ライバル分析（対戦頻度）
        rival_agg: dict[uuid.UUID, dict] = defaultdict(lambda: {"matches": 0, "wins": 0})
        for m in matches:
            opponent = m.team2_id if m.team1_id == team_id else m.team1_id
            if opponent:
                rival_agg[opponent]["matches"] += 1
                rival_agg[opponent]["wins"] += 1 if m.winner_id == team_id else 0

        # 対戦相手名解決
        rival_ids = list(rival_agg.keys())
        rival_names = {}
        if rival_ids:
            rival_teams = (await self._db.execute(
                select(Team.id, Team.name, Team.tag).where(Team.id.in_(rival_ids))
            )).all()
            rival_names = {t.id: (t.name, t.tag) for t in rival_teams}

        # マップ・エージェント分析（チームのPlayerMatchStats集約）
        map_agg, agent_agg = await self._team_map_agent_stats(team_id)
        map_names = await self._load_map_names()

        rating = await self._get_team_rating(team_id)
        championships = await self._get_team_titles(team_id)

        return {
            "team_id": str(team_id),
            "team_name": team.name,
            "team_tag": team.tag,
            "game": team.game.value,
            "total_matches": total_matches,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "win_rate": round(win_rate, 4),
            "championships": championships,
            "tournaments_played": len(tournaments),
            "current_rating": rating.get("current") if rating else None,
            "peak_rating": rating.get("peak") if rating else None,
            "map_performance": [
                {
                    "map_name": map_names.get(mid, str(mid)[:8]),
                    "games": d["games"], "wins": d["wins"],
                    "win_rate": round(d["wins"] / d["games"], 4) if d["games"] else 0.0,
                }
                for mid, d in sorted(map_agg.items(), key=lambda x: -x[1]["games"])
            ],
            "agent_trends": [
                {
                    "agent": agent, "games": d["games"], "wins": d["wins"],
                    "win_rate": round(d["wins"] / d["games"], 4) if d["games"] else 0.0,
                    "avg_kda": round(d["kda_sum"] / d["games"], 2) if d["games"] else 0.0,
                }
                for agent, d in sorted(agent_agg.items(), key=lambda x: -x[1]["games"])
            ],
            "rivals": [
                {
                    "team_id": str(rid),
                    "team_name": rival_names.get(rid, ("Unknown", "?"))[0],
                    "team_tag": rival_names.get(rid, ("Unknown", "?"))[1],
                    "matches": d["matches"],
                    "wins": d["wins"],
                    "losses": d["matches"] - d["wins"],
                    "win_rate": round(d["wins"] / d["matches"], 4) if d["matches"] else 0.0,
                }
                for rid, d in sorted(rival_agg.items(), key=lambda x: -x[1]["matches"])[:10]
            ],
        }

    async def _team_map_agent_stats(self, team_id: uuid.UUID):
        rows = (await self._db.execute(
            select(
                PlayerMatchStats.agent,
                PlayerMatchStats.kills,
                PlayerMatchStats.deaths,
                PlayerMatchStats.assists,
                MatchGame.winner_id.label("game_winner"),
                MatchGame.map_id,
            )
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .where(
                PlayerMatchStats.team_id == team_id,
                Match.status == MatchStatus.COMPLETED,
            )
        )).all()

        map_agg: dict = defaultdict(lambda: {"games": 0, "wins": 0})
        agent_agg: dict = defaultdict(lambda: {"games": 0, "wins": 0, "kda_sum": 0.0})
        for r in rows:
            won = r.game_winner == team_id
            if r.map_id:
                map_agg[r.map_id]["games"] += 1
                map_agg[r.map_id]["wins"] += 1 if won else 0
            if r.agent:
                kda = (r.kills + r.assists) / max(r.deaths, 1)
                agent_agg[r.agent]["games"] += 1
                agent_agg[r.agent]["wins"] += 1 if won else 0
                agent_agg[r.agent]["kda_sum"] += kda
        return map_agg, agent_agg

    # ── ヘルパー（生SQL: モデル未定義テーブル） ────────────────────────────────
    async def _load_map_names(self) -> dict:
        result = await self._db.execute(select(Map.id, Map.display_name))
        return {row.id: row.display_name for row in result.all()}

    async def _get_player_rating(self, player_id: uuid.UUID, game: str) -> Optional[dict]:
        try:
            row = (await self._db.execute(text(
                "SELECT rating, peak_rating FROM player_ratings "
                "WHERE player_id = :pid AND game = :game"
            ), {"pid": str(player_id), "game": game})).first()
            if row:
                return {"current": row[0], "peak": row[1] or row[0]}
        except Exception:
            pass
        return None

    async def _get_team_rating(self, team_id: uuid.UUID) -> Optional[dict]:
        # チームレーティングは rankings テーブルの points を流用
        try:
            row = (await self._db.execute(text(
                "SELECT MAX(points) FROM rankings WHERE team_id = :tid"
            ), {"tid": str(team_id)})).first()
            if row and row[0] is not None:
                return {"current": float(row[0]), "peak": float(row[0])}
        except Exception:
            pass
        return None

    async def _get_player_titles(self, player_id: uuid.UUID) -> tuple[int, int]:
        championships = mvp_count = 0
        try:
            row = (await self._db.execute(text(
                "SELECT COUNT(*) FROM player_achievements "
                "WHERE player_id = :pid AND achievement_type = 'champion'"
            ), {"pid": str(player_id)})).first()
            championships = row[0] if row else 0
            row2 = (await self._db.execute(text(
                "SELECT COUNT(*) FROM match_mvps WHERE player_id = :pid"
            ), {"pid": str(player_id)})).first()
            mvp_count = row2[0] if row2 else 0
        except Exception:
            pass
        return championships, mvp_count

    async def _get_team_titles(self, team_id: uuid.UUID) -> int:
        try:
            row = (await self._db.execute(text(
                "SELECT COUNT(*) FROM team_achievements "
                "WHERE team_id = :tid AND achievement_type = 'champion'"
            ), {"tid": str(team_id)})).first()
            return row[0] if row else 0
        except Exception:
            return 0

    # ── 実績一覧 ────────────────────────────────────────────────────────────────
    async def get_player_achievements(self, player_id: uuid.UUID) -> list[dict]:
        try:
            rows = (await self._db.execute(text(
                "SELECT id, achievement_type, title, description, icon_url, tournament_id, earned_at "
                "FROM player_achievements WHERE player_id = :pid ORDER BY earned_at DESC"
            ), {"pid": str(player_id)})).all()
            return [{
                "id": str(r[0]), "type": r[1], "title": r[2], "description": r[3],
                "icon_url": r[4], "tournament_id": str(r[5]) if r[5] else None,
                "earned_at": r[6].isoformat() if r[6] else "",
            } for r in rows]
        except Exception:
            return []

    async def get_team_achievements(self, team_id: uuid.UUID) -> list[dict]:
        try:
            rows = (await self._db.execute(text(
                "SELECT id, achievement_type, title, description, tournament_id, earned_at "
                "FROM team_achievements WHERE team_id = :tid ORDER BY earned_at DESC"
            ), {"tid": str(team_id)})).all()
            return [{
                "id": str(r[0]), "type": r[1], "title": r[2], "description": r[3],
                "icon_url": None, "tournament_id": str(r[4]) if r[4] else None,
                "earned_at": r[5].isoformat() if r[5] else "",
            } for r in rows]
        except Exception:
            return []

    async def get_player_rating_history(self, player_id: uuid.UUID, game: str) -> list[dict]:
        try:
            rows = (await self._db.execute(text(
                "SELECT rating_after, delta, created_at FROM player_rating_history "
                "WHERE player_id = :pid AND game = :game ORDER BY created_at ASC LIMIT 100"
            ), {"pid": str(player_id), "game": game})).all()
            return [{
                "date": r[2].isoformat() if r[2] else "",
                "rating": r[0], "delta": r[1],
            } for r in rows]
        except Exception:
            return []

    # ── キャッシュ無効化（試合終了・ランキング更新時に呼ぶ） ──────────────────
    async def invalidate_player(self, player_id: uuid.UUID) -> None:
        await self._cache.delete(f"career:player:{player_id}")

    async def invalidate_team(self, team_id: uuid.UUID) -> None:
        await self._cache.delete(f"career:team:{team_id}")
