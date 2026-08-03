"""LFP (Looking for Players) - チーム募集 API"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.dependencies import CurrentUser, DBSession
from app.core.ranks import ranks_in_range
from app.models.team import Team, TeamMember
from app.models.team_recruitment import TeamRecruitment
from app.schemas.common import Response, ListResponse, Meta
from app.core.storage import resign_stored_url
from sqlalchemy import select, func

router = APIRouter(prefix="/lfp", tags=["LFP チーム募集"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LFPCreate(BaseModel):
    team_id: str
    title: str = Field(..., min_length=1, max_length=200)
    status: str = Field(default="open", pattern=r"^(open|paused|closed)$")
    roles: list[str] = Field(..., min_length=1)
    headcount: int = Field(..., ge=1, le=5)
    min_rank: str = Field(..., min_length=1, max_length=50)
    region: str = Field(..., min_length=1, max_length=50)
    activity_time: list[str] = Field(default=[])
    activity_level: Optional[str] = None
    tournaments: list[str] = Field(default=[])
    age_requirement: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    team_intro: Optional[str] = Field(None, max_length=1000)
    discord: Optional[str] = Field(None, max_length=100)
    deadline: Optional[str] = None
    is_public: bool = True


class LFPUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = Field(None, pattern=r"^(open|paused|closed)$")
    roles: Optional[list[str]] = None
    headcount: Optional[int] = Field(None, ge=1, le=5)
    min_rank: Optional[str] = None
    region: Optional[str] = None
    activity_time: Optional[list[str]] = None
    activity_level: Optional[str] = None
    tournaments: Optional[list[str]] = None
    age_requirement: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    team_intro: Optional[str] = Field(None, max_length=1000)
    discord: Optional[str] = Field(None, max_length=100)
    deadline: Optional[str] = None
    is_public: Optional[bool] = None


class LFPSchema(BaseModel):
    id: str
    team_id: str
    team_name: str
    team_tag: str
    team_logo_url: Optional[str]
    owner_id: str
    title: str
    status: str
    roles: list[str]
    headcount: int
    min_rank: str
    region: str
    activity_time: list[str]
    activity_level: Optional[str]
    tournaments: list[str]
    age_requirement: Optional[str]
    description: Optional[str]
    team_intro: Optional[str]
    discord: Optional[str]
    deadline: Optional[str]
    is_public: bool
    created_at: str
    updated_at: str
    # チームの大会実績（競技ランキング連携 / 一覧APIでのみ付与・読み取り専用）
    rp: Optional[int] = None
    tier_label: Optional[str] = None
    tier_color: Optional[str] = None
    championships: Optional[int] = None
    ranking: Optional[int] = None


def _to_schema(r: TeamRecruitment, team: Team) -> LFPSchema:
    return LFPSchema(
        id=str(r.id),
        team_id=str(r.team_id),
        team_name=team.name,
        team_tag=team.tag,
        team_logo_url=resign_stored_url(team.logo_url),
        owner_id=str(r.owner_id),
        title=r.title,
        status=r.status,
        roles=r.roles or [],
        headcount=r.headcount,
        min_rank=r.min_rank,
        region=r.region,
        activity_time=r.activity_time or [],
        activity_level=r.activity_level,
        tournaments=r.tournaments or [],
        age_requirement=r.age_requirement,
        description=r.description,
        team_intro=r.team_intro,
        discord=r.discord,
        deadline=str(r.deadline) if r.deadline else None,
        is_public=r.is_public,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


async def _require_team_owner_or_captain(db, team_id: uuid.UUID, user_id: uuid.UUID):
    team = (await db.execute(select(Team).where(Team.id == team_id, Team.is_active == True))).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    if team.owner_id == user_id:
        return team
    member = (await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.player_id.in_(
                select(TeamMember.player_id).join(
                    __import__("app.models.player", fromlist=["Player"]).Player,
                    __import__("app.models.player", fromlist=["Player"]).Player.id == TeamMember.player_id
                ).where(
                    __import__("app.models.player", fromlist=["Player"]).Player.user_id == user_id
                )
            ),
            TeamMember.left_at.is_(None),
        )
    )).scalar_one_or_none()
    if not member or member.role not in ("captain",):
        raise HTTPException(status_code=403, detail="オーナーまたはキャプテンのみ操作できます")
    return team


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=ListResponse[LFPSchema])
async def list_lfp(
    db: DBSession,
    status: Optional[str] = Query(default="open"),
    region: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    min_rank: Optional[str] = Query(default=None),
    max_rank: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    q = select(TeamRecruitment).where(TeamRecruitment.is_public == True)
    if status:
        q = q.where(TeamRecruitment.status == status)
    if region:
        q = q.where(TeamRecruitment.region == region)
    if min_rank or max_rank:
        # 募集に設定されたランク値が指定範囲内のものだけ返す（単純な範囲チェック）
        q = q.where(TeamRecruitment.min_rank.in_(ranks_in_range(min_rank, max_rank)))
    q = q.order_by(TeamRecruitment.created_at.desc()).limit(limit).offset(offset)

    rows = list((await db.execute(q)).scalars().all())

    if role:
        rows = [r for r in rows if role in (r.roles or [])]

    items = []
    for r in rows:
        team = (await db.execute(select(Team).where(Team.id == r.team_id))).scalar_one_or_none()
        if team:
            items.append(_to_schema(r, team))

    # チームの大会実績（RP/Tier/優勝数）を付与 — スカウトの差別化要素。
    try:
        from app.core.redis import RedisCache, get_redis
        from app.rankings.aggregator import FULL_LIMIT, RankingAggregator

        board = await RankingAggregator(db, RedisCache(await get_redis())).global_team_leaderboard(
            season="all", limit=FULL_LIMIT
        )
        by_team = {e["team_id"]: e for e in board}
        for item in items:
            e = by_team.get(item.team_id)
            if e:
                item.rp = e["rp"]
                item.tier_label = e["tier_label"]
                item.tier_color = e["tier_color"]
                item.championships = e.get("championships", 0)
                item.ranking = e.get("rank")
    except Exception:
        pass  # ランキング取得失敗時も一覧自体は返す（防御的）

    total = await db.scalar(select(func.count(TeamRecruitment.id)).where(TeamRecruitment.is_public == True))
    return ListResponse(data=items, meta=Meta(total=total, cursor=None, has_next=len(items) == limit))


@router.post("", response_model=Response[LFPSchema], status_code=201)
async def create_lfp(data: LFPCreate, db: DBSession, current_user: CurrentUser):
    team_id = uuid.UUID(data.team_id)
    team = (await db.execute(select(Team).where(Team.id == team_id, Team.is_active == True))).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="チームオーナーのみ募集を作成できます")

    now = datetime.now(timezone.utc)
    from datetime import date as date_type
    deadline = date_type.fromisoformat(data.deadline) if data.deadline else None
    r = TeamRecruitment(
        id=uuid.uuid4(),
        team_id=team_id,
        owner_id=current_user.id,
        title=data.title,
        status=data.status,
        roles=data.roles,
        headcount=data.headcount,
        min_rank=data.min_rank,
        region=data.region,
        activity_time=data.activity_time,
        activity_level=data.activity_level,
        tournaments=data.tournaments,
        age_requirement=data.age_requirement,
        description=data.description,
        team_intro=data.team_intro,
        discord=data.discord,
        deadline=deadline,
        is_public=data.is_public,
        created_at=now,
        updated_at=now,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return Response(data=_to_schema(r, team), meta=None)


@router.get("/mine", response_model=Response[list[LFPSchema]])
async def list_mine(db: DBSession, current_user: CurrentUser):
    rows = list((await db.execute(
        select(TeamRecruitment)
        .where(TeamRecruitment.owner_id == current_user.id)
        .order_by(TeamRecruitment.created_at.desc())
    )).scalars().all())
    items = []
    for r in rows:
        team = (await db.execute(select(Team).where(Team.id == r.team_id))).scalar_one_or_none()
        if team:
            items.append(_to_schema(r, team))
    return Response(data=items, meta=None)


@router.get("/{lfp_id}", response_model=Response[LFPSchema])
async def get_lfp(lfp_id: uuid.UUID, db: DBSession):
    r = (await db.execute(select(TeamRecruitment).where(TeamRecruitment.id == lfp_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="募集が見つかりません")
    team = (await db.execute(select(Team).where(Team.id == r.team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    return Response(data=_to_schema(r, team), meta=None)


@router.patch("/{lfp_id}", response_model=Response[LFPSchema])
async def update_lfp(lfp_id: uuid.UUID, data: LFPUpdate, db: DBSession, current_user: CurrentUser):
    r = (await db.execute(select(TeamRecruitment).where(TeamRecruitment.id == lfp_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="募集が見つかりません")
    if r.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="作成者のみ編集できます")

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "deadline" and value:
            from datetime import date as date_type
            value = date_type.fromisoformat(value)
        setattr(r, field, value)
    r.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(r)
    team = (await db.execute(select(Team).where(Team.id == r.team_id))).scalar_one_or_none()
    return Response(data=_to_schema(r, team), meta=None)


@router.delete("/{lfp_id}", status_code=204)
async def delete_lfp(lfp_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    r = (await db.execute(select(TeamRecruitment).where(TeamRecruitment.id == lfp_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="募集が見つかりません")
    if r.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="作成者のみ削除できます")
    await db.delete(r)
    await db.commit()
