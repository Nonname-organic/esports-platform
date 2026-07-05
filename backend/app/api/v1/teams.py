import uuid
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.models.enums import GameType
from app.schemas.common import ListResponse, Meta, Response
from app.services.sponsor_service import SponsorService
from app.schemas.team import (
    AddMemberRequest,
    TeamCreate,
    TeamDetailSchema,
    TeamMemberSchema,
    TeamSummarySchema,
    TeamUpdate,
)
from app.schemas.career import TeamCareerSchema, AchievementItem, RivalItem
from app.schemas.achievement import AchievementCardDTO
from app.schemas.ranking import RankCard
from app.services.team import TeamService
from app.services.career_service import CareerAggregationService
from app.achievements.aggregator import AchievementAggregator
from app.core.storage import resign_stored_url

router = APIRouter(prefix="/teams", tags=["チーム管理"])


# ── Career / Achievements / Rivals ──────────────────────────────────────────
@router.get("/{team_id}/career", response_model=Response[TeamCareerSchema])
async def get_team_career(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    career = await service.get_team_career(team_id)
    return Response(data=TeamCareerSchema(**career), meta=None)


@router.get("/{team_id}/achievements", response_model=Response[list[AchievementItem]])
async def get_team_achievements(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    achievements = await service.get_team_achievements(team_id)
    return Response(data=[AchievementItem(**a) for a in achievements], meta=None)


@router.get("/{team_id}/rivals", response_model=Response[list[RivalItem]])
async def get_team_rivals(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = CareerAggregationService(db, cache)
    career = await service.get_team_career(team_id)
    return Response(data=[RivalItem(**r) for r in career["rivals"]], meta=None)


# ── Achievement Card（読み取り専用の集約DTO・公開） ─────────────────────────
# 注: 既存 GET /{id}/achievements は team_achievements 由来の一覧を返す別契約のため、
#     破壊的変更を避けて additive な /achievement-card を新設（設計差分に記載）。
@router.get("/{team_id}/achievement-card", response_model=Response[AchievementCardDTO])
async def get_team_achievement_card(team_id: uuid.UUID, db: DBSession, cache: Cache):
    """公開チームページ用の実績カード。既存データから集約（保存しない）。"""
    aggregator = AchievementAggregator(db, cache)
    card = await aggregator.get_team_card(team_id)
    return Response(data=AchievementCardDTO(**card), meta=None)


@router.get("/{team_id}/rank-card", response_model=Response[RankCard])
async def get_team_rank_card_endpoint(team_id: uuid.UUID, db: DBSession, cache: Cache):
    """チームのランクカード（Tier/RP/Rank/Progress/Season内訳 / ADR-0016）。Achievement Card と横並び配置。"""
    from app.rankings.aggregator import RankingAggregator
    card = await RankingAggregator(db, cache).team_rank_card(team_id)
    return Response(data=RankCard(**card), meta=None)


def _team_detail(team) -> TeamDetailSchema:
    return TeamDetailSchema(
        id=team.id,
        name=team.name,
        tag=team.tag,
        game=team.game.value,
        logo_url=resign_stored_url(team.logo_url),
        owner_id=team.owner_id,
        is_active=team.is_active,
        created_at=team.created_at,
        description=team.description,
        country=team.country,
        banner_url=resign_stored_url(team.banner_url),
        twitter_handle=team.twitter_handle,
        updated_at=team.updated_at,
    )


def _team_summary(team) -> TeamSummarySchema:
    return TeamSummarySchema(
        id=team.id,
        name=team.name,
        tag=team.tag,
        game=team.game.value,
        logo_url=resign_stored_url(team.logo_url),
        owner_id=team.owner_id,
        is_active=team.is_active,
        created_at=team.created_at,
    )


# ── GET /teams ────────────────────────────────────────────────────────────────
@router.get("/mine", response_model=Response[list[TeamSummarySchema]])
async def list_my_teams(db: DBSession, cache: Cache, current_user: CurrentUser):
    """ログインユーザーが所有またはメンバーとして参加しているチーム一覧"""
    service = TeamService(db, cache)
    teams = await service.get_my_teams(current_user.id)
    return Response(data=[_team_summary(t) for t in teams], meta=None)


# ── スポンサー（機能⑦） ──────────────────────────────────────────────────────
class SponsorInput(BaseModel):
    name: str = Field(..., max_length=100)
    logo_url: Optional[str] = None
    url: Optional[str] = None
    sponsor_type: Optional[str] = Field(None, max_length=30)
    display_order: int = 0
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None


class SponsorUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = None
    url: Optional[str] = None
    sponsor_type: Optional[str] = Field(None, max_length=30)
    display_order: Optional[int] = None
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None


class ReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID]


@router.get("/{team_id}/sponsors", response_model=Response[list[dict]])
async def list_sponsors(team_id: uuid.UUID, db: DBSession, cache: Cache):
    """スポンサー一覧（公開）。"""
    return Response(data=await SponsorService(db, cache).list(team_id), meta=None)


@router.post("/{team_id}/sponsors", response_model=Response[dict], status_code=201)
async def create_sponsor(team_id: uuid.UUID, data: SponsorInput, db: DBSession, cache: Cache, current_user: CurrentUser):
    item = await SponsorService(db, cache).create(team_id, current_user, data.model_dump())
    return Response(data=item, meta=None)


@router.patch("/{team_id}/sponsors/reorder", response_model=Response[list[dict]])
async def reorder_sponsors(team_id: uuid.UUID, data: ReorderRequest, db: DBSession, cache: Cache, current_user: CurrentUser):
    items = await SponsorService(db, cache).reorder(team_id, current_user, data.ordered_ids)
    return Response(data=items, meta=None)


@router.patch("/{team_id}/sponsors/{sponsor_id}", response_model=Response[dict])
async def update_sponsor(team_id: uuid.UUID, sponsor_id: uuid.UUID, data: SponsorUpdate, db: DBSession, cache: Cache, current_user: CurrentUser):
    item = await SponsorService(db, cache).update(team_id, sponsor_id, current_user, data.model_dump(exclude_unset=True))
    return Response(data=item, meta=None)


@router.delete("/{team_id}/sponsors/{sponsor_id}", status_code=204)
async def delete_sponsor(team_id: uuid.UUID, sponsor_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser):
    await SponsorService(db, cache).delete(team_id, sponsor_id, current_user)


@router.get("/{team_id}/audit", response_model=Response[list[dict]])
async def get_team_audit(
    team_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """チーム監査ログ（owner/captain/Admin のみ / ADR-0012）。"""
    service = TeamService(db, cache)
    items = await service.get_audit(team_id, current_user, limit=limit, offset=offset)
    return Response(data=items, meta=None)


@router.get("/{team_id}/stats", response_model=Response[dict])
async def get_team_stats(team_id: uuid.UUID, db: DBSession, cache: Cache):
    """チーム統計（暫定: ゼロ値を返す）"""
    service = TeamService(db, cache)
    await service.get_team(team_id)
    return Response(data={
        "wins": 0, "losses": 0, "win_rate": 0.0, "rating": 1000,
        "peak_rating": 1000, "game_win_rate": 0.0,
        "tournaments_played": 0, "tournaments_won": 0,
        "win_rate_history": [],
    }, meta=None)


@router.get("", response_model=ListResponse[TeamSummarySchema])
async def list_teams(
    db: DBSession,
    cache: Cache,
    game: Optional[GameType] = Query(default=None),
    cursor: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    service = TeamService(db, cache)
    teams, has_next = await service.list_teams(game=game, limit=limit, cursor=cursor)
    items = [_team_summary(t) for t in teams]
    next_cursor = str(items[-1].id) if has_next and items else None
    return ListResponse(
        data=items,
        meta=Meta(total=None, cursor=next_cursor, has_next=has_next),
    )


# ── POST /teams ───────────────────────────────────────────────────────────────
@router.post("", response_model=Response[TeamDetailSchema], status_code=201)
async def create_team(
    data: TeamCreate,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    team = await service.create_team(data, current_user)
    return Response(data=_team_detail(team), meta=None)


# ── GET /teams/{id} ───────────────────────────────────────────────────────────
@router.get("/{team_id}", response_model=Response[TeamDetailSchema])
async def get_team(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = TeamService(db, cache)
    team = await service.get_team(team_id)
    return Response(data=_team_detail(team), meta=None)


# ── PATCH /teams/{id} ────────────────────────────────────────────────────────
@router.patch("/{team_id}", response_model=Response[TeamDetailSchema])
async def update_team(
    team_id: uuid.UUID,
    data: TeamUpdate,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    team = await service.update_team(team_id, data, current_user)
    return Response(data=_team_detail(team), meta=None)


# ── DELETE /teams/{id} ───────────────────────────────────────────────────────
@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    await service.delete_team(team_id, current_user)


# ── GET /teams/{id}/members ───────────────────────────────────────────────────
@router.get("/{team_id}/members", response_model=Response[list[TeamMemberSchema]])
async def list_members(team_id: uuid.UUID, db: DBSession, cache: Cache):
    service = TeamService(db, cache)
    members = await service.get_members(team_id)
    return Response(data=[TeamMemberSchema(**m) for m in members], meta=None)


# ── POST /teams/{id}/members ──────────────────────────────────────────────────
@router.post("/{team_id}/members", response_model=Response[TeamMemberSchema], status_code=201)
async def add_member(
    team_id: uuid.UUID,
    data: AddMemberRequest,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    member = await service.add_member(team_id, data, current_user)
    return Response(data=TeamMemberSchema(**member), meta=None)


# ── DELETE /teams/{id}/members/{player_id} ────────────────────────────────────
@router.delete("/{team_id}/members/{player_id}", status_code=204)
async def remove_member(
    team_id: uuid.UUID,
    player_id: uuid.UUID,
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
):
    service = TeamService(db, cache)
    await service.remove_member(team_id, player_id, current_user)
