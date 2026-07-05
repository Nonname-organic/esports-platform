"""Home Widget Providers（ADR-0019 / read-only・実データのみ）。

各 Provider は独立し WidgetProvider を実装。Recommendation/Prediction は RuleBased 実装で、
将来 OpenAI/Claude/Gemini 実装へ registry の差し替えのみで交換可能（HomeAggregatorは不変）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.core.storage import resign_stored_url
from app.home.base import HomeContext
from app.models.enums import RegistrationStatus, TournamentStatus
from app.models.tag import Tag, Taggable
from app.models.team import Team
from app.models.tournament import Tournament, TournamentRegistration
from app.rankings.aggregator import RankingAggregator
from app.services.activity_service import ActivityService
from app.services.stats_service import StatsService

FULL = 100000


async def _approved_counts(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(TournamentRegistration.tournament_id, func.count())
        .where(TournamentRegistration.status == RegistrationStatus.APPROVED)
        .group_by(TournamentRegistration.tournament_id)
    )).all()
    return {tid: int(c) for tid, c in rows}


# ── Recommendation（AI差し替え点 / 初期RuleBased） ──────────────────────────
def _reason(hours, prize, fill, ctx_game, t_game) -> str:
    parts = []
    if ctx_game and t_game == ctx_game:
        parts.append("あなたのメインゲーム")
    if hours is not None and hours <= 48:
        parts.append("締切間近")
    if prize and prize >= 50000:
        parts.append("高額賞金")
    if 0.4 <= fill <= 0.85:
        parts.append("参加が集まっている")
    if not parts:
        parts.append("今おすすめ")
    return " · ".join(parts)


class RuleBasedRecommendationProvider:
    key = "recommendations"

    async def build(self, db: AsyncSession, cache: RedisCache, ctx: HomeContext) -> list[dict]:
        rows = list((await db.execute(
            select(Tournament).where(Tournament.status == TournamentStatus.REGISTRATION_OPEN)
        )).scalars().all())
        if not rows:
            return []
        counts = await _approved_counts(db)
        now = datetime.now(timezone.utc)

        scored: list[tuple] = []
        for t in rows:
            reg = counts.get(t.id, 0)
            fill = reg / max(t.max_teams, 1)
            hours = None
            if t.registration_end_at:
                dt = (t.registration_end_at - now).total_seconds() / 3600
                if dt <= 0:
                    continue
                hours = dt
            deadline_score = 0.0 if hours is None else max(0.0, 100 - min(hours, 168) / 168 * 100)
            prize = float(t.prize_pool or 0)
            prize_score = min(prize / 100000, 1) * 100
            fill_score = (1 - abs(fill - 0.6)) * 50
            game_boost = 30 if (ctx.game and t.game.value == ctx.game) else 0
            score = deadline_score * 0.4 + prize_score * 0.3 + fill_score * 0.2 + game_boost
            scored.append((score, t, reg, fill, hours, _reason(hours, prize, fill, ctx.game, t.game.value)))

        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[dict] = []
        for _score, t, reg, fill, _hours, reason in scored[:6]:
            out.append({
                "id": str(t.id),
                "name": t.name,
                "game": t.game.value if hasattr(t.game, "value") else str(t.game),
                "banner_url": resign_stored_url(t.banner_url),
                "prize_pool": float(t.prize_pool) if t.prize_pool is not None else None,
                "prize_currency": t.prize_currency,
                "registration_end_at": t.registration_end_at.isoformat() if t.registration_end_at else None,
                "start_at": t.start_at.isoformat() if t.start_at else None,
                "registered": reg,
                "max_teams": t.max_teams,
                "fill": round(fill, 4),
                "reason": reason,
            })
        return out


# ── Prediction（AI差し替え点 / 初期RuleBased） ──────────────────────────────
class RuleBasedPredictionProvider:
    key = "predictions"

    async def build(self, db: AsyncSession, cache: RedisCache, ctx: HomeContext):
        t = await db.scalar(
            select(Tournament).where(Tournament.status == TournamentStatus.ONGOING).order_by(Tournament.prize_pool.desc()).limit(1)
        )
        if not t:
            t = await db.scalar(
                select(Tournament).where(Tournament.status == TournamentStatus.REGISTRATION_OPEN).order_by(Tournament.prize_pool.desc()).limit(1)
            )
        if not t:
            return None

        parts = (await db.execute(
            select(Team.id, Team.name, Team.tag, Team.logo_url)
            .join(TournamentRegistration, TournamentRegistration.team_id == Team.id)
            .where(TournamentRegistration.tournament_id == t.id, TournamentRegistration.status == RegistrationStatus.APPROVED)
        )).all()
        if len(parts) < 2:
            return None

        board = await RankingAggregator(db, cache).global_team_leaderboard(game=None, season="all", limit=FULL)
        rp = {e["team_id"]: e["rp"] for e in board}
        base = 200
        scored = [
            {"team_id": str(tid), "team_name": name, "team_tag": tag, "logo_url": resign_stored_url(logo),
             "weight": rp.get(str(tid), 0) + base}
            for tid, name, tag, logo in parts
        ]
        total = sum(s["weight"] for s in scored) or 1
        scored.sort(key=lambda s: s["weight"], reverse=True)
        contenders = [{
            "team_id": s["team_id"], "team_name": s["team_name"], "team_tag": s["team_tag"], "logo_url": s["logo_url"],
            "win_prob": round(s["weight"] / total * 100, 1),
        } for s in scored[:5]]

        return {
            "method": "rule_based",
            "tournament": {"id": str(t.id), "name": t.name, "game": t.game.value if hasattr(t.game, "value") else str(t.game)},
            "favorite": contenders[0] if contenders else None,
            "contenders": contenders,
            "dark_horse": contenders[2] if len(contenders) >= 3 else None,
        }


# ── Trending（実データ集計） ────────────────────────────────────────────────
class TrendingProvider:
    key = "trending"

    async def build(self, db: AsyncSession, cache: RedisCache, ctx: HomeContext) -> dict:
        counts = await _approved_counts(db)
        active = list((await db.execute(
            select(Tournament).where(Tournament.status.in_([TournamentStatus.REGISTRATION_OPEN, TournamentStatus.ONGOING]))
        )).scalars().all())
        active.sort(key=lambda t: counts.get(t.id, 0), reverse=True)
        tournaments = [{
            "id": str(t.id), "name": t.name,
            "game": t.game.value if hasattr(t.game, "value") else str(t.game),
            "registered": counts.get(t.id, 0), "max_teams": t.max_teams,
        } for t in active[:5]]

        agg = RankingAggregator(db, cache)
        team_board = await agg.global_team_leaderboard(game=ctx.game, season="all", limit=5)
        teams = [{"team_id": e["team_id"], "team_name": e["team_name"], "rp": e["rp"], "tier_label": e["tier_label"], "tier_color": e["tier_color"]} for e in team_board]
        player_board = await agg.global_player_leaderboard(game=ctx.game, season="all", limit=5)
        players = [{"player_id": e["player_id"], "in_game_name": e["in_game_name"], "rp": e["rp"], "tier_label": e["tier_label"], "tier_color": e["tier_color"]} for e in player_board]

        tag_rows = (await db.execute(
            select(Tag.slug, Tag.label, func.count(Taggable.tag_id))
            .join(Taggable, Taggable.tag_id == Tag.id)
            .group_by(Tag.id).order_by(func.count(Taggable.tag_id).desc()).limit(8)
        )).all()
        tags = [{"slug": slug, "label": label, "count": int(c)} for slug, label, c in tag_rows]

        return {"tournaments": tournaments, "teams": teams, "players": players, "tags": tags}


# ── Live（既存 StatsService を read-only 再利用） ──────────────────────────────
class LiveSummaryProvider:
    key = "live"

    async def build(self, db: AsyncSession, cache: RedisCache, ctx: HomeContext) -> dict:
        return await StatsService(db, cache).overview()


# ── Activity（既存 ActivityService を read-only 再利用 / 公開のみ） ────────────
class ActivityHomeProvider:
    key = "activity"

    async def build(self, db: AsyncSession, cache: RedisCache, ctx: HomeContext) -> list[dict]:
        return await ActivityService(db).global_activity(limit=8)


# ── Insights（実数から規則ベースで生成 / 文言はAI説明文） ──────────────────────
class InsightsProvider:
    key = "insights"

    async def build(self, db: AsyncSession, cache: RedisCache, ctx: HomeContext) -> list[dict]:
        ov = await StatsService(db, cache).overview()
        live = ov.get("live", {})
        totals = ov.get("totals", {})
        prize = int(totals.get("total_prize", 0) or 0)
        return [
            {"icon": "door", "text": f"現在 {live.get('registration_open_tournaments', 0)} 件の大会が受付中"},
            {"icon": "zap", "text": f"{live.get('ongoing_tournaments', 0)} 件の大会が進行中"},
            {"icon": "coins", "text": f"累計 ¥{prize:,} の賞金が懸かっています"},
            {"icon": "users", "text": f"{totals.get('teams', 0)} チーム・{totals.get('players', 0)} 選手が登録済み"},
        ]
