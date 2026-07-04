"""タグ API（機能⑤ / ADR-0014）。

- カタログ取得・タグ検索は公開。
- エンティティへの付与/差し替えは **対象エンティティの権限**に従う（各 Service で検証）。
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.schemas.common import Response
from app.services.tag_service import TagService, VALID_ENTITY_TYPES

router = APIRouter(prefix="/tags", tags=["タグ"])


class SetTagsRequest(BaseModel):
    tags: list[str] = Field(default_factory=list, description="slug またはラベル（正規化される）")


@router.get("", response_model=Response[list[dict]])
async def list_tags(
    db: DBSession,
    category: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
):
    """タグカタログ（autocomplete 用）。"""
    return Response(data=await TagService(db).list_catalog(category=category, q=q), meta=None)


@router.get("/{slug}/entities", response_model=Response[list[dict]])
async def entities_with_tag(
    slug: str, db: DBSession,
    entity_type: Optional[str] = Query(default=None),
):
    """指定タグが付いたエンティティ一覧（タグ検索）。"""
    return Response(data=await TagService(db).entities_with_tag(slug, entity_type), meta=None)


@router.get("/of/{entity_type}/{entity_id}", response_model=Response[list[dict]])
async def get_entity_tags(entity_type: str, entity_id: uuid.UUID, db: DBSession):
    """エンティティに付与済みのタグ（公開）。"""
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(400, "invalid entity_type")
    return Response(data=await TagService(db).tags_for(entity_type, entity_id), meta=None)


@router.put("/of/{entity_type}/{entity_id}", response_model=Response[list[dict]])
async def set_entity_tags(
    entity_type: str, entity_id: uuid.UUID, data: SetTagsRequest,
    db: DBSession, cache: Cache, current_user: CurrentUser,
):
    """エンティティのタグを差し替え（対象エンティティの権限を検証）。"""
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(400, "invalid entity_type")
    await _authorize(entity_type, entity_id, db, cache, current_user)
    tags = await TagService(db).set_tags(entity_type, entity_id, data.tags)
    return Response(data=tags, meta=None)


async def _authorize(entity_type: str, entity_id: uuid.UUID, db, cache, current_user) -> None:
    """対象エンティティの編集権限を検証（無ければ 403/404 を送出）。"""
    from app.core.exceptions import ForbiddenError, NotFoundError
    if entity_type == "team":
        from app.services.team import TeamService
        svc = TeamService(db, cache)
        team = await svc.get_team(entity_id)
        await svc._require_owner_or_captain(team, current_user)
    elif entity_type == "tournament":
        from app.services.tournament import TournamentService
        from app.models.enums import UserRole
        t = await TournamentService(db, cache)._repo.get_by_id(entity_id)
        if not t:
            raise NotFoundError("大会", str(entity_id))
        if current_user.role != UserRole.ADMIN and t.organizer_id != current_user.id:
            raise ForbiddenError("この大会のタグを編集する権限がありません")
    elif entity_type in ("lfp", "lft"):
        # 作成者のみ。owner_id/user_id を持つ募集モデルを参照。
        from sqlalchemy import select
        from app.models.enums import UserRole
        if entity_type == "lfp":
            from app.models.team_recruitment import TeamRecruitment as M
            owner_col = M.owner_id
        else:
            from app.models.player_lft import PlayerLFT as M
            owner_col = M.user_id
        row = await db.scalar(select(M).where(M.id == entity_id))
        if not row:
            raise NotFoundError("募集", str(entity_id))
        if current_user.role != UserRole.ADMIN and getattr(row, owner_col.key) != current_user.id:
            raise ForbiddenError("この募集のタグを編集する権限がありません")
