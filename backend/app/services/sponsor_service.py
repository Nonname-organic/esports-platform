"""SponsorService — チームスポンサーの CRUD + 並び替え（機能⑦）。

付与権限は Team の owner/captain（TeamService の判定を再利用）。commit は呼び出し側（get_db）。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import RedisCache
from app.core.storage import resign_stored_url
from app.models.team_sponsor import TeamSponsor
from app.services.team import TeamService


def _to_dict(s: TeamSponsor) -> dict:
    return {
        "id": str(s.id),
        "team_id": str(s.team_id),
        "name": s.name,
        "logo_url": resign_stored_url(s.logo_url),
        "url": s.url,
        "sponsor_type": s.sponsor_type,
        "display_order": s.display_order,
        "contract_start": s.contract_start.isoformat() if s.contract_start else None,
        "contract_end": s.contract_end.isoformat() if s.contract_end else None,
    }


def _parse_date(v: Optional[str]) -> Optional[date]:
    return date.fromisoformat(v) if v else None


class SponsorService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache
        self._teams = TeamService(db, cache)

    async def list(self, team_id: uuid.UUID) -> list[dict]:
        rows = (await self._db.execute(
            select(TeamSponsor).where(TeamSponsor.team_id == team_id)
            .order_by(TeamSponsor.display_order, TeamSponsor.created_at)
        )).scalars().all()
        return [_to_dict(s) for s in rows]

    async def _require_manage(self, team_id: uuid.UUID, current_user) -> None:
        team = await self._teams.get_team(team_id)
        await self._teams._require_owner_or_captain(team, current_user)

    async def create(self, team_id: uuid.UUID, current_user, data: dict) -> dict:
        await self._require_manage(team_id, current_user)
        s = TeamSponsor(
            id=uuid.uuid4(), team_id=team_id,
            name=data["name"], logo_url=data.get("logo_url"), url=data.get("url"),
            sponsor_type=data.get("sponsor_type"), display_order=data.get("display_order", 0),
            contract_start=_parse_date(data.get("contract_start")),
            contract_end=_parse_date(data.get("contract_end")),
        )
        self._db.add(s)
        await self._db.flush()
        return _to_dict(s)

    async def update(self, team_id: uuid.UUID, sponsor_id: uuid.UUID, current_user, data: dict) -> dict:
        await self._require_manage(team_id, current_user)
        s = await self._db.scalar(
            select(TeamSponsor).where(TeamSponsor.id == sponsor_id, TeamSponsor.team_id == team_id)
        )
        if not s:
            raise NotFoundError("スポンサー", str(sponsor_id))
        for field in ("name", "logo_url", "url", "sponsor_type", "display_order"):
            if field in data and data[field] is not None:
                setattr(s, field, data[field])
        if "contract_start" in data:
            s.contract_start = _parse_date(data.get("contract_start"))
        if "contract_end" in data:
            s.contract_end = _parse_date(data.get("contract_end"))
        s.updated_at = datetime.now(timezone.utc)
        await self._db.flush()
        return _to_dict(s)

    async def delete(self, team_id: uuid.UUID, sponsor_id: uuid.UUID, current_user) -> None:
        await self._require_manage(team_id, current_user)
        s = await self._db.scalar(
            select(TeamSponsor).where(TeamSponsor.id == sponsor_id, TeamSponsor.team_id == team_id)
        )
        if not s:
            raise NotFoundError("スポンサー", str(sponsor_id))
        await self._db.delete(s)
        await self._db.flush()

    async def reorder(self, team_id: uuid.UUID, current_user, ordered_ids: list[uuid.UUID]) -> list[dict]:
        await self._require_manage(team_id, current_user)
        rows = (await self._db.execute(
            select(TeamSponsor).where(TeamSponsor.team_id == team_id)
        )).scalars().all()
        by_id = {s.id: s for s in rows}
        for order, sid in enumerate(ordered_ids):
            if sid in by_id:
                by_id[sid].display_order = order
        await self._db.flush()
        return await self.list(team_id)
