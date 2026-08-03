"""AnalyticsDashboardService — BIダッシュボード用のリアルタイム集計（read-only）。

既存の集計テーブルは空/未整備なことがあるため、トランザクションテーブル
（matches / match_games / player_match_stats）から直接集計する。既存 AnalyticsService は不変。
フロントの型（types/analytics.ts）に合わせた dict を返す。Redis 短TTLキャッシュ。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.models.enums import BanPickAction, GameType, MatchStatus, TournamentStatus
from app.models.match import BanPick, Map, Match, MatchGame, PlayerMatchStats
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.models.tournament import Tournament
from app.models.user import User

TTL = 300  # 5分


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class AnalyticsDashboardService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    # ── 共通フィルタ（Match/Tournament を join 済み前提の条件） ─────────────────
    def _match_conds(
        self, game: GameType, tournament_id: Optional[uuid.UUID],
        date_from: Optional[str], date_to: Optional[str],
    ) -> list:
        conds = [Tournament.game == game, Match.status == MatchStatus.COMPLETED]
        if tournament_id:
            conds.append(Match.tournament_id == tournament_id)
        df, dt = _parse_dt(date_from), _parse_dt(date_to)
        occurred = func.coalesce(Match.started_at, Match.created_at)
        if df:
            conds.append(occurred >= df)
        if dt:
            conds.append(occurred < dt)
        return conds

    # ── overview（KPI: 大会数 / 総試合 / 人気MAP・エージェント 等） ──────────────
    async def overview(
        self, game: GameType, tournament_id: Optional[uuid.UUID] = None,
        date_from: Optional[str] = None, date_to: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
    ) -> dict:
        c = self._match_conds(game, tournament_id, date_from, date_to)

        # マッチ / 大会 / チーム
        m_base = select(Match).join(Tournament, Match.tournament_id == Tournament.id).where(*c)
        if team_id:
            m_base = m_base.where((Match.team1_id == team_id) | (Match.team2_id == team_id))
        m_sub = m_base.subquery()
        total_matches = await self._db.scalar(select(func.count()).select_from(m_sub)) or 0
        total_tournaments = await self._db.scalar(
            select(func.count(func.distinct(Match.tournament_id)))
            .select_from(Match).join(Tournament, Match.tournament_id == Tournament.id).where(*c)
        ) or 0

        # ゲーム集計（MatchGame）
        g_join = (
            select(MatchGame)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .where(*c)
        )
        g_sub = g_join.subquery()
        total_games = await self._db.scalar(select(func.count()).select_from(g_sub)) or 0
        avg_dur = await self._db.scalar(
            select(func.avg(MatchGame.duration_seconds))
            .select_from(MatchGame).join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id).where(*c)
        )

        # 全体勝率: team指定=そのチームのマッチ勝率 / 無指定=team1(先攻列基準)勝率の近似
        if team_id:
            wins = await self._db.scalar(
                select(func.count()).select_from(Match)
                .join(Tournament, Match.tournament_id == Tournament.id)
                .where(*c, Match.winner_id == team_id)
            ) or 0
            overall_win_rate = round(wins / total_matches, 4) if total_matches else 0.0
        else:
            t1_wins = await self._db.scalar(
                select(func.count()).select_from(Match)
                .join(Tournament, Match.tournament_id == Tournament.id)
                .where(*c, Match.winner_id == Match.team1_id)
            ) or 0
            overall_win_rate = round(t1_wins / total_matches, 4) if total_matches else 0.0

        # 人気MAP
        top_map = (await self._db.execute(
            select(Map.display_name, func.count().label("g"))
            .select_from(MatchGame)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .join(Map, MatchGame.map_id == Map.id)
            .where(*c).group_by(Map.display_name).order_by(func.count().desc()).limit(1)
        )).first()

        # 人気エージェント
        top_agent = (await self._db.execute(
            select(PlayerMatchStats.agent, func.count().label("g"))
            .select_from(PlayerMatchStats)
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .where(*c, PlayerMatchStats.agent.isnot(None))
            .group_by(PlayerMatchStats.agent).order_by(func.count().desc()).limit(1)
        )).first()

        # アクティブチーム / プレイヤー
        active_teams = await self._db.scalar(
            select(func.count(func.distinct(func.coalesce(Match.team1_id, Match.team2_id))))
            .select_from(Match).join(Tournament, Match.tournament_id == Tournament.id).where(*c)
        ) or 0
        active_players = await self._db.scalar(
            select(func.count(func.distinct(PlayerMatchStats.player_id)))
            .select_from(PlayerMatchStats)
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id).where(*c)
        ) or 0

        return {
            "total_matches": int(total_matches),
            "total_games": int(total_games),
            "total_tournaments": int(total_tournaments),
            "overall_win_rate": overall_win_rate,
            "avg_match_duration_seconds": float(avg_dur) if avg_dur is not None else None,
            "most_played_map": top_map[0] if top_map else None,
            "most_played_agent": top_agent[0] if top_agent else None,
            "active_teams": int(active_teams),
            "active_players": int(active_players),
        }

    # ── by_map（マップ使用率・勝率） ──────────────────────────────────────────
    async def by_map(
        self, game: GameType, tournament_id: Optional[uuid.UUID] = None,
        date_from: Optional[str] = None, date_to: Optional[str] = None,
    ) -> list[dict]:
        c = self._match_conds(game, tournament_id, date_from, date_to)
        rows = (await self._db.execute(
            select(
                Map.id, Map.display_name,
                func.count().label("total_games"),
                func.sum(case((MatchGame.winner_id == Match.team1_id, 1), else_=0)).label("t1"),
                func.sum(case((MatchGame.winner_id == Match.team2_id, 1), else_=0)).label("t2"),
                func.avg(MatchGame.duration_seconds).label("avg_dur"),
            )
            .select_from(MatchGame)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .join(Map, MatchGame.map_id == Map.id)
            .where(*c)
            .group_by(Map.id, Map.display_name)
            .order_by(func.count().desc())
        )).all()
        out = []
        for map_id, name, total, t1, t2, avg_dur in rows:
            total = int(total or 0)
            out.append({
                "map_id": str(map_id),
                "map_name": name,
                "game": game.value,
                "total_games": total,
                "attack_side_wins": int(t1 or 0),
                "defense_side_wins": int(t2 or 0),
                "attack_win_rate": round((t1 or 0) / total, 4) if total else 0.0,
                "avg_duration_seconds": float(avg_dur) if avg_dur is not None else None,
                "round_distribution": None,
            })
        return out

    # ── by_agent（エージェント使用率・勝率・KDA） ─────────────────────────────
    async def by_agent(
        self, game: GameType, tournament_id: Optional[uuid.UUID] = None,
        date_from: Optional[str] = None, date_to: Optional[str] = None,
    ) -> list[dict]:
        c = self._match_conds(game, tournament_id, date_from, date_to)
        rows = (await self._db.execute(
            select(
                PlayerMatchStats.agent,
                func.count().label("games"),
                func.sum(case((MatchGame.winner_id == PlayerMatchStats.team_id, 1), else_=0)).label("wins"),
                func.avg((PlayerMatchStats.kills + PlayerMatchStats.assists) / func.nullif(PlayerMatchStats.deaths, 0)).label("kda"),
                func.avg(PlayerMatchStats.kills).label("k"),
                func.avg(PlayerMatchStats.deaths).label("d"),
                func.avg(PlayerMatchStats.assists).label("a"),
            )
            .select_from(PlayerMatchStats)
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .where(*c, PlayerMatchStats.agent.isnot(None))
            .group_by(PlayerMatchStats.agent)
            .order_by(func.count().desc())
        )).all()
        total_picks = sum(int(r.games or 0) for r in rows) or 1
        out = []
        for r in rows:
            games = int(r.games or 0)
            wins = int(r.wins or 0)
            out.append({
                "agent": r.agent,
                "games": games,
                "wins": wins,
                "losses": games - wins,
                "win_rate": round(wins / games, 4) if games else 0.0,
                "pick_rate": round(games / total_picks, 4),
                "ban_rate": 0.0,
                "avg_kda": round(float(r.kda), 2) if r.kda is not None else 0.0,
                "avg_kills": round(float(r.k), 1) if r.k is not None else 0.0,
                "avg_deaths": round(float(r.d), 1) if r.d is not None else 0.0,
                "avg_assists": round(float(r.a), 1) if r.a is not None else 0.0,
            })
        return out

    # ── winrate バンドル（overview + by_map + by_agent） ───────────────────────
    async def winrate(
        self, game: GameType, tournament_id: Optional[uuid.UUID] = None,
        date_from: Optional[str] = None, date_to: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
    ) -> dict:
        return {
            "overview": await self.overview(game, tournament_id, date_from, date_to, team_id),
            "by_map": await self.by_map(game, tournament_id, date_from, date_to),
            "by_agent": await self.by_agent(game, tournament_id, date_from, date_to),
        }

    # ── trend（日次） ─────────────────────────────────────────────────────────
    async def trend(
        self, game: GameType, period: str = "30d",
        tournament_id: Optional[uuid.UUID] = None,
    ) -> list[dict]:
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period)
        date_from = None
        if days:
            date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        c = self._match_conds(game, tournament_id, date_from, None)
        occurred = func.coalesce(Match.started_at, Match.created_at)
        day = func.date(occurred)

        # 試合数 / 先攻勝率 / 平均試合時間（by day, MatchGame 基準）
        grows = (await self._db.execute(
            select(
                day.label("d"),
                func.count(func.distinct(Match.id)).label("matches"),
                func.sum(case((MatchGame.winner_id == Match.team1_id, 1), else_=0)).label("t1"),
                func.count().label("games"),
                func.avg(MatchGame.duration_seconds).label("dur"),
            )
            .select_from(MatchGame)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .where(*c).group_by(day).order_by(day)
        )).all()

        # 平均KDA（by day, PlayerMatchStats 基準）
        krows = (await self._db.execute(
            select(
                day.label("d"),
                func.avg((PlayerMatchStats.kills + PlayerMatchStats.assists) / func.nullif(PlayerMatchStats.deaths, 0)).label("kda"),
            )
            .select_from(PlayerMatchStats)
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .where(*c).group_by(day)
        )).all()
        kda_by_day = {str(r.d): float(r.kda) if r.kda is not None else 0.0 for r in krows}

        out = []
        for r in grows:
            games = int(r.games or 0)
            out.append({
                "date": str(r.d),
                "matches": int(r.matches or 0),
                "win_rate": round((r.t1 or 0) / games, 4) if games else 0.0,
                "avg_kda": round(kda_by_day.get(str(r.d), 0.0), 2),
                "avg_duration_seconds": float(r.dur) if r.dur is not None else None,
            })
        return out

    # ── players（KDA/勝率上位） ───────────────────────────────────────────────
    async def players(
        self, game: GameType, tournament_id: Optional[uuid.UUID] = None, limit: int = 20,
    ) -> list[dict]:
        c = self._match_conds(game, tournament_id, None, None)
        rows = (await self._db.execute(
            select(
                PlayerMatchStats.player_id,
                func.count().label("games"),
                func.sum(case((MatchGame.winner_id == PlayerMatchStats.team_id, 1), else_=0)).label("wins"),
                func.avg((PlayerMatchStats.kills + PlayerMatchStats.assists) / func.nullif(PlayerMatchStats.deaths, 0)).label("kda"),
                func.avg(PlayerMatchStats.kills).label("k"),
                func.avg(PlayerMatchStats.deaths).label("d"),
                func.avg(PlayerMatchStats.assists).label("a"),
            )
            .select_from(PlayerMatchStats)
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .where(*c)
            .group_by(PlayerMatchStats.player_id)
            .order_by(func.avg((PlayerMatchStats.kills + PlayerMatchStats.assists) / func.nullif(PlayerMatchStats.deaths, 0)).desc().nullslast())
            .limit(limit)
        )).all()
        if not rows:
            return []

        ids = [r.player_id for r in rows]
        pmap = {p.id: p for p in (await self._db.execute(select(Player).where(Player.id.in_(ids)))).scalars().all()}
        # 現所属チーム
        team_rows = (await self._db.execute(
            select(TeamMember.player_id, Team.name, Team.tag)
            .join(Team, Team.id == TeamMember.team_id)
            .where(TeamMember.player_id.in_(ids), TeamMember.left_at.is_(None))
        )).all()
        team_map = {pid: (name, tag) for pid, name, tag in team_rows}

        out = []
        for i, r in enumerate(rows, 1):
            p = pmap.get(r.player_id)
            games = int(r.games or 0)
            wins = int(r.wins or 0)
            t = team_map.get(r.player_id)
            out.append({
                "rank": i,
                "player_id": str(r.player_id),
                "player_name": (p.real_name or p.in_game_name) if p else "Unknown",
                "in_game_name": p.in_game_name if p else None,
                "team_name": t[0] if t else None,
                "team_tag": t[1] if t else None,
                "avatar_url": None,
                "games": games,
                "win_rate": round(wins / games, 4) if games else 0.0,
                "avg_kda": round(float(r.kda), 2) if r.kda is not None else 0.0,
                "avg_kills": round(float(r.k), 1) if r.k is not None else 0.0,
                "avg_deaths": round(float(r.d), 1) if r.d is not None else 0.0,
                "avg_assists": round(float(r.a), 1) if r.a is not None else 0.0,
                "headshot_rate": 0.0,
                "most_played_agent": None,
            })
        return out

    # ── heatmap（MAP × Agent 勝率） ───────────────────────────────────────────
    async def heatmap(
        self, game: GameType, tournament_id: Optional[uuid.UUID] = None,
    ) -> list[dict]:
        c = self._match_conds(game, tournament_id, None, None)
        rows = (await self._db.execute(
            select(
                Map.display_name, PlayerMatchStats.agent,
                func.count().label("games"),
                func.sum(case((MatchGame.winner_id == PlayerMatchStats.team_id, 1), else_=0)).label("wins"),
            )
            .select_from(PlayerMatchStats)
            .join(MatchGame, PlayerMatchStats.match_game_id == MatchGame.id)
            .join(Match, MatchGame.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .join(Map, MatchGame.map_id == Map.id)
            .where(*c, PlayerMatchStats.agent.isnot(None))
            .group_by(Map.display_name, PlayerMatchStats.agent)
            .order_by(func.count().desc())
            .limit(200)
        )).all()
        out = []
        for name, agent, games, wins in rows:
            games = int(games or 0)
            out.append({
                "map_name": name,
                "agent": agent,
                "games": games,
                "win_rate": round((wins or 0) / games, 4) if games else 0.0,
            })
        return out

    # ── マップ BAN/PICK 率（ban_picks — 大会限定データ / 外部公開の目玉） ─────────
    async def map_veto(
        self, game: GameType, tournament_id: Optional[uuid.UUID] = None,
    ) -> list[dict]:
        cache_key = f"analytics:veto:{game.value}:{tournament_id or 'all'}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        conds = [Tournament.game == game]
        if tournament_id:
            conds.append(Match.tournament_id == tournament_id)
        rows = (await self._db.execute(
            select(
                Map.display_name,
                func.sum(case((BanPick.action == BanPickAction.BAN, 1), else_=0)).label("bans"),
                func.sum(case((BanPick.action == BanPickAction.PICK, 1), else_=0)).label("picks"),
            )
            .select_from(BanPick)
            .join(Match, BanPick.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .join(Map, BanPick.map_id == Map.id)
            .where(*conds)
            .group_by(Map.display_name)
        )).all()

        total_bans = sum(int(r.bans or 0) for r in rows) or 1
        total_picks = sum(int(r.picks or 0) for r in rows) or 1
        out = []
        for r in rows:
            bans, picks = int(r.bans or 0), int(r.picks or 0)
            out.append({
                "map_name": r.display_name,
                "bans": bans,
                "picks": picks,
                "ban_rate": round(bans / total_bans, 4),
                "pick_rate": round(picks / total_picks, 4),
            })
        out.sort(key=lambda x: x["ban_rate"], reverse=True)
        await self._cache.set(cache_key, out, ttl=TTL)
        return out

    # ── 月次成長推移（大会数 / 新規チーム / 新規ユーザー — 公開ページの成長曲線） ──
    async def growth(self, months: int = 12) -> list[dict]:
        cache_key = f"analytics:growth:{months}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        month_t = func.to_char(func.date_trunc("month", Tournament.end_at), "YYYY-MM")
        t_rows = (await self._db.execute(
            select(month_t, func.count())
            .where(Tournament.status == TournamentStatus.COMPLETED, Tournament.end_at.isnot(None))
            .group_by(month_t)
        )).all()
        month_team = func.to_char(func.date_trunc("month", Team.created_at), "YYYY-MM")
        team_rows = (await self._db.execute(select(month_team, func.count()).group_by(month_team))).all()
        month_user = func.to_char(func.date_trunc("month", User.created_at), "YYYY-MM")
        user_rows = (await self._db.execute(select(month_user, func.count()).group_by(month_user))).all()

        t_map = {r[0]: int(r[1]) for r in t_rows if r[0]}
        team_map = {r[0]: int(r[1]) for r in team_rows if r[0]}
        user_map = {r[0]: int(r[1]) for r in user_rows if r[0]}

        # 直近 N ヶ月の連続した月キーを生成（データ無し月は0で埋める）
        now = datetime.now(timezone.utc)
        keys: list[str] = []
        y, m = now.year, now.month
        for _ in range(months):
            keys.append(f"{y}-{m:02d}")
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        keys.reverse()

        out = [{
            "month": k,
            "tournaments": t_map.get(k, 0),
            "new_teams": team_map.get(k, 0),
            "new_users": user_map.get(k, 0),
        } for k in keys]
        await self._cache.set(cache_key, out, ttl=TTL)
        return out
