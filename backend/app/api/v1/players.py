import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.player import GAME_ROLES, PlayerCreate, PlayerSchema, PlayerUpdate
from app.schemas.career import PlayerCareerSchema, AchievementItem, RatingPoint
from app.schemas.ranking import PlayerRankCard
from app.player_profile.dto import PlayerAnalysis, PlayerHistoryItem
from app.services.player import PlayerService
from app.services.career_service import CareerAggregationService
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/players", tags=["プレイヤー管理"])


# ── Activity Feed（公開活動 / ADR-0011） ─────────────────────────────────────
@router.get("/{player_id}/activity", response_model=Response[list[dict]])
async def get_player_activity(
    player_id: uuid.UUID, db: DBSession,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """プレイヤーに関する公開活動タイムライン（visibility=public のみ）。"""
    items = await ActivityService(db).player_activity(player_id, limit=limit, offset=offset)
    return Response(data=items, meta=None)


# ── Career / Achievements / Ratings ─────────────────────────────────────────
@router.get("/{player_id}/career", response_model=Response[PlayerCareerSchema])
async def get_player_career(player_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    career = await service.get_player_career(player_id)
    return Response(data=PlayerCareerSchema(**career), meta=None)


@router.get("/{player_id}/achievements", response_model=Response[list[AchievementItem]])
async def get_player_achievements(player_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    achievements = await service.get_player_achievements(player_id)
    return Response(data=[AchievementItem(**a) for a in achievements], meta=None)


@router.get("/{player_id}/rank-card", response_model=Response[PlayerRankCard])
async def get_player_rank_card_endpoint(player_id: uuid.UUID, db: DBSession, cache: Cache):
    """プレイヤーのランクカード（Tier/RP/Rank/Progress/Season内訳 / ADR-0016）。Achievement と横並び配置。"""
    from app.rankings.aggregator import RankingAggregator
    card = await RankingAggregator(db, cache).player_rank_card(player_id)
    return Response(data=PlayerRankCard(**card), meta=None)


# ── World-class Player Profile（ADR-0018 / Read Model・AI分析 / 追加のみ） ──────
@router.get("/{player_id}/profile", response_model=Response[dict])
async def get_player_profile(player_id: uuid.UUID, db: DBSession, cache: Cache):
    """1ページ完結のプロフィール集約（basic/career/rank/achievements/history/analysis/activity）。"""
    from app.player_profile.aggregator import PlayerProfileAggregator
    data = await PlayerProfileAggregator(db, cache).profile(player_id)
    return Response(data=data, meta=None)


@router.get("/{player_id}/analysis", response_model=Response[PlayerAnalysis])
async def get_player_analysis(player_id: uuid.UUID, db: DBSession, cache: Cache):
    """AI分析（Read Only・Provider化・現状ルールベース）。"""
    from app.player_profile.aggregator import PlayerProfileAggregator
    data = await PlayerProfileAggregator(db, cache).analysis(player_id)
    return Response(data=PlayerAnalysis(**data), meta=None)


@router.get("/{player_id}/history", response_model=Response[list[PlayerHistoryItem]])
async def get_player_history(player_id: uuid.UUID, db: DBSession, cache: Cache):
    """大会履歴（placement/team/date）。"""
    from app.player_profile.aggregator import PlayerProfileAggregator
    items = await PlayerProfileAggregator(db, cache).history(player_id)
    return Response(data=[PlayerHistoryItem(**i) for i in items], meta=None)


@router.get("/{player_id}/rating-history", response_model=Response[list[RatingPoint]])
async def get_player_rating_history(
    player_id: uuid.UUID, db: DBSession, cache: Cache,
    game: str = Query(default="VALORANT"),
):
    service = CareerAggregationService(db, cache)
    history = await service.get_player_rating_history(player_id, game)
    return Response(data=[RatingPoint(**h) for h in history], meta=None)


@router.get("/{player_id}/stats")
async def get_player_stats(player_id: uuid.UUID, db: DBSession, cache: Cache):
    """プレイヤー詳細ヘッダー用の集計スタッツ（キャリア集計から導出）。

    実績の無い新規プレイヤーでもゼロ値を返す（404にしない）。
    """
    service = CareerAggregationService(db, cache)
    c = await service.get_player_career(player_id)
    agents = c.get("agent_usage") or []
    top = agents[0] if agents else None
    data = {
        "total_matches": c.get("total_matches", 0),
        "wins": c.get("total_wins", 0),
        "losses": c.get("total_losses", 0),
        "win_rate": c.get("win_rate", 0.0),
        "total_games": c.get("total_matches", 0),
        "avg_kills": c.get("avg_kills", 0.0),
        "avg_deaths": c.get("avg_deaths", 0.0),
        "avg_assists": c.get("avg_assists", 0.0),
        "avg_kda": c.get("avg_kda", 0.0),
        "avg_score": c.get("avg_acs", 0.0),
        "headshot_rate": 0.0,
        "first_blood_rate": 0.0,
        "most_played_agent": (top or {}).get("agent"),
        "most_played_agent_games": (top or {}).get("games", 0),
    }
    return {"data": data, "meta": None}


@router.get("/roles", tags=["プレイヤー管理"])
async def get_game_roles():
    """ゲーム別ロール一覧（フロントエンドのセレクター用）"""
    return {"data": GAME_ROLES}


@router.get("", response_model=ListResponse[PlayerSchema])
async def list_players(
    db: DBSession,
    cache: Cache,
    game: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    cursor: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    service = PlayerService(db, cache)
    players, has_next = await service.list_players(
        game=game, region=region, limit=limit, cursor=cursor
    )
    next_cursor = str(players[-1].id) if has_next and players else None
    return ListResponse(
        data=players,
        meta=Meta(total=None, cursor=next_cursor, has_next=has_next),
    )


@router.get("/me", response_model=Response[Optional[PlayerSchema]])
async def get_my_player(db: DBSession, cache: Cache, current_user: CurrentUser):
    """自分のプレイヤープロフィールを取得（なければnull）"""
    service = PlayerService(db, cache)
    player = await service.get_my_player(current_user.id)
    return Response(data=player, meta=None)


@router.post("", response_model=Response[PlayerSchema], status_code=201)
async def create_player(
    data: PlayerCreate, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = PlayerService(db, cache)
    player = await service.create_player(data, current_user)
    return Response(data=player, meta=None)


@router.get("/{player_id}", response_model=Response[PlayerSchema])
async def get_player(player_id: uuid.UUID, db: DBSession, cache: Cache):
    service = PlayerService(db, cache)
    player = await service.get_player(player_id)
    return Response(data=player, meta=None)


@router.patch("/{player_id}", response_model=Response[PlayerSchema])
async def update_player(
    player_id: uuid.UUID,
    data: PlayerUpdate,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = PlayerService(db, cache)
    player = await service.update_player(player_id, data, current_user)
    return Response(data=player, meta=None)


@router.delete("/{player_id}", status_code=204)
async def delete_player(
    player_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = PlayerService(db, cache)
    await service.delete_player(player_id, current_user)
