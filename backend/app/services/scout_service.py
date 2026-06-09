"""
Scout Service
- Player/Team Discovery（検索）
- Recruitment Board（募集・応募・招待）
- Recommendation Engine（双方向マッチング）
- Scout Rating算出（Glicko-2 + WinRate + Tournament + Championship + MVP + Activity）

既存の player_careers / team_careers / player_ratings / rankings を利用。
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, ForbiddenError, NotFoundError
from app.core.redis import RedisCache
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.models.scout import ScoutProfile, RecruitmentPost, RecruitmentApplication
from app.repositories.scout import (
    ScoutProfileRepository, RecruitmentRepository, ApplicationRepository,
)
from app.services.career_service import CareerAggregationService


# ══════════════════════════════════════════════════════════════════════════════
# Scout Rating 算出
# ══════════════════════════════════════════════════════════════════════════════
class ScoutRatingCalculator:
    """
    Scout Rating = 各要素の重み付き合成（0-100スケール）
      - Glicko-2 rating（正規化）   35%
      - Win Rate                    25%
      - Tournament Score            15%
      - Championship                10%
      - MVP                         10%
      - Activity（直近活動）         5%
    """
    WEIGHTS = {
        "glicko": 0.35, "win_rate": 0.25, "tournament": 0.15,
        "championship": 0.10, "mvp": 0.10, "activity": 0.05,
    }

    @classmethod
    def calculate(
        cls,
        rating: Optional[float],
        win_rate: float,
        tournaments_played: int,
        championships: int,
        mvp_count: int,
        last_active_days: Optional[int],
    ) -> float:
        # Glicko正規化（1000-2500 → 0-1）
        glicko_norm = min(max(((rating or 1500) - 1000) / 1500, 0), 1)
        wr_norm = min(max(win_rate, 0), 1)
        tour_norm = min(tournaments_played / 20, 1)
        champ_norm = min(championships / 5, 1)
        mvp_norm = min(mvp_count / 10, 1)
        # 活動度: 7日以内=1.0, 30日=0.5, 90日以上=0.1
        if last_active_days is None:
            activity = 0.3
        elif last_active_days <= 7:
            activity = 1.0
        elif last_active_days <= 30:
            activity = 0.6
        elif last_active_days <= 90:
            activity = 0.3
        else:
            activity = 0.1

        score = (
            cls.WEIGHTS["glicko"] * glicko_norm +
            cls.WEIGHTS["win_rate"] * wr_norm +
            cls.WEIGHTS["tournament"] * tour_norm +
            cls.WEIGHTS["championship"] * champ_norm +
            cls.WEIGHTS["mvp"] * mvp_norm +
            cls.WEIGHTS["activity"] * activity
        ) * 100
        return round(score, 1)


# ══════════════════════════════════════════════════════════════════════════════
# Recommendation Engine
# ══════════════════════════════════════════════════════════════════════════════
class RecommendationEngine:
    """
    双方向マッチングスコア算出
    Player→Team / Team→Player の適合度を 0-100 で算出
    """
    DEFAULT_WEIGHTS = {
        "role_match": 0.25, "language_match": 0.10, "region_match": 0.15,
        "rating_diff": 0.20, "activity": 0.10, "tournament_exp": 0.10, "win_rate": 0.10,
    }

    @classmethod
    def score(
        cls,
        *,
        role_match: bool,
        common_languages: int,
        region_match: bool,
        rating_a: float,
        rating_b: float,
        activity_level: float,
        tournaments: int,
        win_rate: float,
        weights: Optional[dict] = None,
    ) -> tuple[float, dict]:
        w = weights or cls.DEFAULT_WEIGHTS

        role_score = 1.0 if role_match else 0.3
        lang_score = min(common_languages / 2, 1.0)
        region_score = 1.0 if region_match else 0.4
        # レート差が小さいほど高スコア（差500で0）
        rating_score = max(0, 1 - abs(rating_a - rating_b) / 500)
        activity_score = min(max(activity_level, 0), 1)
        tour_score = min(tournaments / 15, 1)
        wr_score = min(max(win_rate, 0), 1)

        total = (
            w["role_match"] * role_score +
            w["language_match"] * lang_score +
            w["region_match"] * region_score +
            w["rating_diff"] * rating_score +
            w["activity"] * activity_score +
            w["tournament_exp"] * tour_score +
            w["win_rate"] * wr_score
        ) * 100

        breakdown = {
            "role_match": round(role_score * 100),
            "language_match": round(lang_score * 100),
            "region_match": round(region_score * 100),
            "rating": round(rating_score * 100),
            "activity": round(activity_score * 100),
            "tournament": round(tour_score * 100),
            "win_rate": round(wr_score * 100),
        }
        return round(total, 1), breakdown


# ══════════════════════════════════════════════════════════════════════════════
# Scout Service
# ══════════════════════════════════════════════════════════════════════════════
class ScoutService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache
        self._profiles = ScoutProfileRepository(db)
        self._recruitment = RecruitmentRepository(db)
        self._applications = ApplicationRepository(db)
        self._career = CareerAggregationService(db, cache)

    # ── Player Discovery ──────────────────────────────────────────────────────
    async def search_players(
        self,
        game: Optional[str] = None,
        role: Optional[str] = None,
        rank: Optional[str] = None,
        region: Optional[str] = None,
        min_win_rate: Optional[float] = None,
        min_rating: Optional[float] = None,
        min_tournaments: Optional[int] = None,
        looking_only: bool = False,
        sort_by: str = "scout_rating",
        limit: int = 30,
        offset: int = 0,
    ) -> list[dict]:
        q = select(Player)
        if game:
            q = q.where(Player.game == game)
        if role:
            q = q.where(Player.main_role == role)
        if rank:
            q = q.where(Player.rank == rank)
        if region:
            q = q.where(Player.region == region)
        q = q.limit(limit * 3).offset(offset)  # フィルタ後絞り込むため多めに取得

        players = list((await self._db.execute(q)).scalars().all())

        cards = []
        for p in players:
            stats = await self._player_stats_quick(p.id, p.game.value)
            if min_win_rate is not None and stats["win_rate"] < min_win_rate:
                continue
            if min_rating is not None and (stats["rating"] or 0) < min_rating:
                continue
            if min_tournaments is not None and stats["tournaments_played"] < min_tournaments:
                continue

            profile = await self._profiles.get_by_player(p.id)
            if looking_only and not (profile and profile.is_looking):
                continue

            team_info = await self._current_team(p.id)
            cards.append({
                "player_id": str(p.id),
                "in_game_name": p.in_game_name,
                "game": p.game.value,
                "main_role": p.main_role,
                "rank": p.rank,
                "region": p.region,
                "current_team_id": team_info[0],
                "current_team_name": team_info[1],
                "rating": stats["rating"],
                "scout_rating": stats["scout_rating"],
                "win_rate": stats["win_rate"],
                "total_matches": stats["total_matches"],
                "championships": stats["championships"],
                "mvp_count": stats["mvp_count"],
                "tournaments_played": stats["tournaments_played"],
                "is_looking": profile.is_looking if profile else False,
                "availability": profile.availability if profile else None,
                "languages": (profile.languages if profile else None),
            })

        # ソート
        sort_key = {
            "scout_rating": lambda c: c["scout_rating"] or 0,
            "rating": lambda c: c["rating"] or 0,
            "win_rate": lambda c: c["win_rate"],
            "tournament_count": lambda c: c["tournaments_played"],
        }.get(sort_by, lambda c: c["scout_rating"] or 0)
        cards.sort(key=sort_key, reverse=True)
        return cards[:limit]

    async def _player_stats_quick(self, player_id: uuid.UUID, game: str) -> dict:
        """軽量集計（careerキャッシュを利用）"""
        try:
            career = await self._career.get_player_career(player_id)
            rating = career.get("current_rating")
            scout_rating = ScoutRatingCalculator.calculate(
                rating=rating,
                win_rate=career["win_rate"],
                tournaments_played=career["tournaments_played"],
                championships=career["championships"],
                mvp_count=career["mvp_count"],
                last_active_days=None,
            )
            return {
                "rating": rating,
                "scout_rating": scout_rating,
                "win_rate": career["win_rate"],
                "total_matches": career["total_matches"],
                "championships": career["championships"],
                "mvp_count": career["mvp_count"],
                "tournaments_played": career["tournaments_played"],
            }
        except Exception:
            return {"rating": None, "scout_rating": None, "win_rate": 0.0,
                    "total_matches": 0, "championships": 0, "mvp_count": 0, "tournaments_played": 0}

    async def _current_team(self, player_id: uuid.UUID) -> tuple[Optional[str], Optional[str]]:
        row = (await self._db.execute(
            select(Team.id, Team.name)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.player_id == player_id, TeamMember.left_at.is_(None))
            .limit(1)
        )).first()
        if row:
            return str(row[0]), row[1]
        return None, None

    # ── Team Discovery ──────────────────────────────────────────────────────────
    async def search_teams(
        self,
        game: Optional[str] = None,
        region: Optional[str] = None,
        recruiting_only: bool = False,
        min_avg_rating: Optional[float] = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[dict]:
        q = select(Team).where(Team.is_active == True)
        if game:
            q = q.where(Team.game == game)
        if region:
            q = q.where(Team.region == region)
        q = q.limit(limit * 2).offset(offset)

        teams = list((await self._db.execute(q)).scalars().all())
        cards = []
        for t in teams:
            try:
                career = await self._career.get_team_career(t.id)
            except Exception:
                career = {"win_rate": 0.0, "total_matches": 0, "championships": 0, "current_rating": None}

            roster_count = await self._db.scalar(
                select(func.count(TeamMember.id)).where(
                    TeamMember.team_id == t.id, TeamMember.left_at.is_(None)
                )
            ) or 0

            profile = await self._profiles.get_by_team(t.id)
            is_recruiting = profile.is_looking if profile else False
            if recruiting_only and not is_recruiting:
                continue
            if min_avg_rating is not None and (career.get("current_rating") or 0) < min_avg_rating:
                continue

            cards.append({
                "team_id": str(t.id),
                "name": t.name,
                "tag": t.tag,
                "game": t.game.value,
                "logo_url": t.logo_url,
                "region": t.region,
                "avg_rating": career.get("current_rating"),
                "win_rate": career["win_rate"],
                "total_matches": career["total_matches"],
                "championships": career["championships"],
                "roster_count": roster_count,
                "is_recruiting": is_recruiting,
            })

        cards.sort(key=lambda c: c["avg_rating"] or 0, reverse=True)
        return cards[:limit]

    # ── Recruitment Board ─────────────────────────────────────────────────────
    async def create_post(self, author_id: uuid.UUID, data) -> RecruitmentPost:
        post = await self._recruitment.create(
            author_id=author_id,
            post_type=data.post_type,
            team_id=uuid.UUID(data.team_id) if data.team_id else None,
            player_id=uuid.UUID(data.player_id) if data.player_id else None,
            game=data.game,
            title=data.title,
            description=data.description,
            required_roles=data.required_roles,
            min_rank=data.min_rank,
            regions=data.regions,
            is_open=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return post

    async def list_posts(self, post_type=None, game=None, limit=30, offset=0) -> list[dict]:
        posts = await self._recruitment.list_posts(
            post_type=post_type, game=game, limit=limit, offset=offset
        )
        result = []
        for p in posts:
            count = await self._recruitment.count_applications(p.id)
            result.append({
                "id": str(p.id),
                "author_id": str(p.author_id),
                "post_type": p.post_type,
                "team_id": str(p.team_id) if p.team_id else None,
                "player_id": str(p.player_id) if p.player_id else None,
                "game": p.game,
                "title": p.title,
                "description": p.description,
                "required_roles": p.required_roles,
                "min_rank": p.min_rank,
                "regions": p.regions,
                "is_open": p.is_open,
                "application_count": count,
                "created_at": p.created_at,
            })
        return result

    async def update_post(self, post_id: uuid.UUID, author_id: uuid.UUID, data) -> RecruitmentPost:
        post = await self._recruitment.get_by_id(post_id)
        if not post:
            raise NotFoundError("募集", str(post_id))
        if post.author_id != author_id:
            raise ForbiddenError("この募集を編集する権限がありません")
        updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
        updates["updated_at"] = datetime.now(timezone.utc)
        return await self._recruitment.update(post, **updates)

    async def delete_post(self, post_id: uuid.UUID, author_id: uuid.UUID) -> None:
        post = await self._recruitment.get_by_id(post_id)
        if not post:
            raise NotFoundError("募集", str(post_id))
        if post.author_id != author_id:
            raise ForbiddenError("この募集を削除する権限がありません")
        await self._recruitment.delete(post)

    async def apply(self, applicant_id: uuid.UUID, data) -> RecruitmentApplication:
        post = await self._recruitment.get_by_id(uuid.UUID(data.post_id))
        if not post or not post.is_open:
            raise NotFoundError("募集", data.post_id)
        existing = await self._applications.get_existing(post.id, applicant_id)
        if existing:
            raise AlreadyExistsError("既に応募済みです")
        app = await self._applications.create(
            post_id=post.id,
            applicant_id=applicant_id,
            applicant_player_id=uuid.UUID(data.player_id) if data.player_id else None,
            applicant_team_id=uuid.UUID(data.team_id) if data.team_id else None,
            kind=data.kind,
            message=data.message,
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # 募集者へ通知
        try:
            from app.services.notification_service import NotificationService
            notif = NotificationService(self._db, self._cache)
            await notif.create(
                user_id=post.author_id,
                ntype="team_invite" if data.kind == "invite" else "tournament_invite",
                title="新しい応募が届きました",
                body=f"「{post.title}」に応募がありました",
                action_url=f"/scout/recruitment",
            )
        except Exception:
            pass
        return app

    # ── Recommendation Engine ─────────────────────────────────────────────────
    async def recommend_teams_for_player(self, player_id: uuid.UUID, limit: int = 10) -> list[dict]:
        """選手におすすめのチーム"""
        player = await self._db.scalar(select(Player).where(Player.id == player_id))
        if not player:
            raise NotFoundError("プレイヤー", str(player_id))

        p_profile = await self._profiles.get_by_player(player_id)
        p_stats = await self._player_stats_quick(player_id, player.game.value)
        p_languages = set(p_profile.languages or []) if p_profile else set()

        # 募集中のチームを取得
        teams = await self.search_teams(game=player.game.value, recruiting_only=True, limit=50)

        recs = []
        for t in teams:
            t_profile = await self._profiles.get_by_team(uuid.UUID(t["team_id"]))
            t_roles = set(t_profile.preferred_roles or []) if t_profile else set()
            t_languages = set(t_profile.languages or []) if t_profile else set()

            role_match = player.main_role in t_roles if player.main_role else False
            common_lang = len(p_languages & t_languages)
            region_match = player.region == t["region"] if player.region and t["region"] else False

            score, breakdown = RecommendationEngine.score(
                role_match=role_match,
                common_languages=common_lang,
                region_match=region_match,
                rating_a=p_stats["rating"] or 1500,
                rating_b=t["avg_rating"] or 1500,
                activity_level=0.6,
                tournaments=t["championships"] * 3 + t["total_matches"] // 5,
                win_rate=t["win_rate"],
            )
            recs.append({
                "target_id": t["team_id"],
                "target_type": "team",
                "name": t["name"],
                "score": score,
                "breakdown": breakdown,
                "summary": f"ロール{'一致' if role_match else '要確認'} / 地域{'一致' if region_match else '異なる'} / 勝率{int(t['win_rate']*100)}%",
            })

        recs.sort(key=lambda r: r["score"], reverse=True)
        return recs[:limit]

    async def recommend_players_for_team(self, team_id: uuid.UUID, limit: int = 10) -> list[dict]:
        """チームにおすすめの選手"""
        team = await self._db.scalar(select(Team).where(Team.id == team_id))
        if not team:
            raise NotFoundError("チーム", str(team_id))

        t_profile = await self._profiles.get_by_team(team_id)
        t_roles = set(t_profile.preferred_roles or []) if t_profile else set()
        t_languages = set(t_profile.languages or []) if t_profile else set()
        try:
            t_career = await self._career.get_team_career(team_id)
            t_rating = t_career.get("current_rating") or 1500
        except Exception:
            t_rating = 1500

        # 募集中の選手を取得
        players = await self.search_players(game=team.game.value, looking_only=True, limit=50)

        recs = []
        for p in players:
            p_profile = await self._profiles.get_by_player(uuid.UUID(p["player_id"]))
            p_languages = set(p_profile.languages or []) if p_profile else set()

            role_match = p["main_role"] in t_roles if p["main_role"] else False
            common_lang = len(p_languages & t_languages)
            region_match = p["region"] == team.region if p["region"] and team.region else False

            score, breakdown = RecommendationEngine.score(
                role_match=role_match,
                common_languages=common_lang,
                region_match=region_match,
                rating_a=t_rating,
                rating_b=p["rating"] or 1500,
                activity_level=1.0 if p["is_looking"] else 0.5,
                tournaments=p["tournaments_played"],
                win_rate=p["win_rate"],
            )
            recs.append({
                "target_id": p["player_id"],
                "target_type": "player",
                "name": p["in_game_name"],
                "score": score,
                "breakdown": breakdown,
                "summary": f"{p['main_role'] or '不明'} / 勝率{int(p['win_rate']*100)}% / Scout {p['scout_rating'] or '-'}",
            })

        recs.sort(key=lambda r: r["score"], reverse=True)
        return recs[:limit]
