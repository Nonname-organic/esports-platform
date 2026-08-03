"""LFT (Looking for Team) - 選手募集 API"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from app.core.dependencies import CurrentUser, DBSession
from app.core.ranks import ranks_in_range
from app.models.player import Player
from app.models.player_lft import PlayerLFT
from app.models.user import User
from app.schemas.common import Response, ListResponse, Meta
from app.core.storage import resign_stored_url

router = APIRouter(prefix="/lft", tags=["LFT 選手募集"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LFTCreate(BaseModel):
    status: str = Field(default="open", pattern=r"^(open|negotiating|closed)$")
    roles: list[str] = Field(..., min_length=1)
    current_rank: str = Field(..., min_length=1, max_length=50)
    peak_rank: str = Field(..., min_length=1, max_length=50)
    region: str = Field(..., min_length=1, max_length=50)
    activity_time: list[str] = Field(default=[])
    experience: Optional[str] = None
    premier: Optional[str] = None
    agents: list[str] = Field(default=[])
    description: Optional[str] = Field(None, max_length=1000)
    conditions: Optional[str] = Field(None, max_length=500)
    discord: Optional[str] = Field(None, max_length=100)
    twitter: Optional[str] = Field(None, max_length=100)
    deadline: Optional[str] = None
    is_public: bool = True


class LFTUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern=r"^(open|negotiating|closed)$")
    roles: Optional[list[str]] = None
    current_rank: Optional[str] = None
    peak_rank: Optional[str] = None
    region: Optional[str] = None
    activity_time: Optional[list[str]] = None
    experience: Optional[str] = None
    premier: Optional[str] = None
    agents: Optional[list[str]] = None
    description: Optional[str] = Field(None, max_length=1000)
    conditions: Optional[str] = Field(None, max_length=500)
    discord: Optional[str] = Field(None, max_length=100)
    twitter: Optional[str] = Field(None, max_length=100)
    deadline: Optional[str] = None
    is_public: Optional[bool] = None


class LFTSchema(BaseModel):
    id: str
    player_id: str
    user_id: str
    in_game_name: str
    avatar_url: Optional[str]
    status: str
    roles: list[str]
    current_rank: str
    peak_rank: str
    region: str
    activity_time: list[str]
    experience: Optional[str]
    premier: Optional[str]
    agents: list[str]
    description: Optional[str]
    conditions: Optional[str]
    discord: Optional[str]
    twitter: Optional[str]
    deadline: Optional[str]
    is_public: bool
    created_at: str
    updated_at: str
    # 大会実績（競技ランキング連携 / 一覧APIでのみ付与・読み取り専用）
    rp: Optional[int] = None
    tier_label: Optional[str] = None
    tier_color: Optional[str] = None
    mvps: Optional[int] = None
    ranking: Optional[int] = None


def _to_schema(r: PlayerLFT, player: Player, user: Optional[User] = None) -> LFTSchema:
    return LFTSchema(
        id=str(r.id),
        player_id=str(r.player_id),
        user_id=str(r.user_id),
        in_game_name=player.in_game_name,
        avatar_url=resign_stored_url(user.avatar_url) if user else None,
        status=r.status,
        roles=r.roles or [],
        current_rank=r.current_rank,
        peak_rank=r.peak_rank,
        region=r.region,
        activity_time=r.activity_time or [],
        experience=r.experience,
        premier=r.premier,
        agents=r.agents or [],
        description=r.description,
        conditions=r.conditions,
        discord=r.discord,
        twitter=r.twitter,
        deadline=str(r.deadline) if r.deadline else None,
        is_public=r.is_public,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=ListResponse[LFTSchema])
async def list_lft(
    db: DBSession,
    status: Optional[str] = Query(default="open"),
    region: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    rank: Optional[str] = Query(default=None),
    min_rank: Optional[str] = Query(default=None),
    max_rank: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    q = select(PlayerLFT).where(PlayerLFT.is_public == True)
    if status:
        q = q.where(PlayerLFT.status == status)
    if region:
        q = q.where(PlayerLFT.region == region)
    if rank:  # 旧: 完全一致（後方互換）
        q = q.where(PlayerLFT.current_rank == rank)
    if min_rank or max_rank:  # 新: 現在ランクの範囲絞り込み
        q = q.where(PlayerLFT.current_rank.in_(ranks_in_range(min_rank, max_rank)))
    q = q.order_by(PlayerLFT.updated_at.desc()).limit(limit).offset(offset)

    rows = list((await db.execute(q)).scalars().all())

    if role:
        rows = [r for r in rows if role in (r.roles or [])]

    items = []
    for r in rows:
        player = (await db.execute(select(Player).where(Player.id == r.player_id))).scalar_one_or_none()
        if not player:
            continue
        user = (await db.execute(select(User).where(User.id == r.user_id))).scalar_one_or_none()
        items.append(_to_schema(r, player, user))

    # 大会実績（RP/Tier/MVP）を付与 — スカウトの差別化要素。leaderboardはRedisキャッシュ済みで軽量。
    try:
        from app.core.redis import RedisCache, get_redis
        from app.rankings.aggregator import FULL_LIMIT, RankingAggregator

        board = await RankingAggregator(db, RedisCache(await get_redis())).global_player_leaderboard(
            season="all", limit=FULL_LIMIT
        )
        by_player = {e["player_id"]: e for e in board}
        for item in items:
            e = by_player.get(item.player_id)
            if e:
                item.rp = e["rp"]
                item.tier_label = e["tier_label"]
                item.tier_color = e["tier_color"]
                item.mvps = e.get("mvps", 0)
                item.ranking = e.get("rank")
    except Exception:
        pass  # ランキング取得失敗時も一覧自体は返す（防御的）

    total = await db.scalar(select(func.count(PlayerLFT.id)).where(PlayerLFT.is_public == True))
    return ListResponse(data=items, meta=Meta(total=total, cursor=None, has_next=len(rows) == limit))


@router.get("/me", response_model=Response[Optional[LFTSchema]])
async def get_my_lft(db: DBSession, current_user: CurrentUser):
    player = (await db.execute(select(Player).where(Player.user_id == current_user.id))).scalar_one_or_none()
    if not player:
        return Response(data=None, meta=None)
    r = (await db.execute(select(PlayerLFT).where(PlayerLFT.player_id == player.id))).scalar_one_or_none()
    if not r:
        return Response(data=None, meta=None)
    return Response(data=_to_schema(r, player, current_user), meta=None)


@router.get("/{lft_id}", response_model=Response[LFTSchema])
async def get_lft(lft_id: uuid.UUID, db: DBSession):
    r = (await db.execute(select(PlayerLFT).where(PlayerLFT.id == lft_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="LFTが見つかりません")
    player = (await db.execute(select(Player).where(Player.id == r.player_id))).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="プレイヤーが見つかりません")
    user = (await db.execute(select(User).where(User.id == r.user_id))).scalar_one_or_none()
    return Response(data=_to_schema(r, player, user), meta=None)


@router.post("", response_model=Response[LFTSchema], status_code=201)
async def create_lft(data: LFTCreate, db: DBSession, current_user: CurrentUser):
    player = (await db.execute(select(Player).where(Player.user_id == current_user.id))).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=400, detail="プレイヤー登録が必要です")

    existing = (await db.execute(select(PlayerLFT).where(PlayerLFT.player_id == player.id))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="既にLFTが登録されています。編集してください。")

    now = datetime.now(timezone.utc)
    from datetime import date as date_type
    deadline = date_type.fromisoformat(data.deadline) if data.deadline else None

    r = PlayerLFT(
        id=uuid.uuid4(),
        player_id=player.id,
        user_id=current_user.id,
        status=data.status,
        roles=data.roles,
        current_rank=data.current_rank,
        peak_rank=data.peak_rank,
        region=data.region,
        activity_time=data.activity_time,
        experience=data.experience,
        premier=data.premier,
        agents=data.agents,
        description=data.description,
        conditions=data.conditions,
        discord=data.discord,
        twitter=data.twitter,
        deadline=deadline,
        is_public=data.is_public,
        created_at=now,
        updated_at=now,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return Response(data=_to_schema(r, player, current_user), meta=None)


@router.patch("/me", response_model=Response[LFTSchema])
async def update_my_lft(data: LFTUpdate, db: DBSession, current_user: CurrentUser):
    player = (await db.execute(select(Player).where(Player.user_id == current_user.id))).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=400, detail="プレイヤー登録が必要です")
    r = (await db.execute(select(PlayerLFT).where(PlayerLFT.player_id == player.id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="LFTが見つかりません")

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "deadline" and value:
            from datetime import date as date_type
            value = date_type.fromisoformat(value)
        setattr(r, field, value)
    r.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(r)
    return Response(data=_to_schema(r, player, current_user), meta=None)


@router.delete("/me", status_code=204)
async def delete_my_lft(db: DBSession, current_user: CurrentUser):
    player = (await db.execute(select(Player).where(Player.user_id == current_user.id))).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=400, detail="プレイヤー登録が必要です")
    r = (await db.execute(select(PlayerLFT).where(PlayerLFT.player_id == player.id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="LFTが見つかりません")
    await db.delete(r)
    await db.commit()
