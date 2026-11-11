"""RC4 第 2 段の API: 大会の名簿、名簿への参加の承認、大会の方式の切り替え、出場の異議。"""
import uuid
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.schemas.common import Response
from app.services.roster import DisputeService, RosterService
from app.services.tournament import TournamentService

router = APIRouter(tags=["大会の名簿と出場の異議"])


def _entry(e) -> dict[str, Any]:
    return {"id": str(e.id), "tournament_id": str(e.tournament_id), "registration_id": str(e.registration_id),
            "team_id": str(e.team_id), "player_id": str(e.player_id), "default_slot": e.default_slot,
            "status": e.status, "invited_at": e.invited_at, "responded_at": e.responded_at,
            "removed_at": e.removed_at, "reason": e.reason}


class RosterAddBody(BaseModel):
    player_id: uuid.UUID
    default_slot: str = Field(default="starter", pattern="^(starter|bench)$")
    reason: str | None = Field(default=None, max_length=1000)


class RosterPatchBody(BaseModel):
    default_slot: str | None = Field(default=None, pattern="^(starter|bench)$")
    remove: bool = False
    reason: str | None = Field(default=None, max_length=1000)


@router.get("/tournaments/{tournament_id}/registrations/{registration_id}/roster",
            response_model=Response[list[dict[str, Any]]])
async def get_roster(tournament_id: uuid.UUID, registration_id: uuid.UUID, db: DBSession, cache: Cache,
                     current_user: CurrentUser):
    rows = await RosterService(db, cache).get_roster(tournament_id, registration_id, current_user)
    return Response(data=[_entry(e) for e in rows])


@router.post("/tournaments/{tournament_id}/registrations/{registration_id}/roster",
             response_model=Response[dict[str, Any]], status_code=201)
async def add_roster_entry(tournament_id: uuid.UUID, registration_id: uuid.UUID, data: RosterAddBody,
                           db: DBSession, cache: Cache, current_user: CurrentUser):
    entry = await RosterService(db, cache).add_entry(tournament_id, registration_id, data.player_id,
                                                     data.default_slot, data.reason, current_user)
    return Response(data=_entry(entry))


@router.patch("/tournaments/{tournament_id}/registrations/{registration_id}/roster/{entry_id}",
              response_model=Response[dict[str, Any]])
async def patch_roster_entry(tournament_id: uuid.UUID, registration_id: uuid.UUID, entry_id: uuid.UUID,
                             data: RosterPatchBody, db: DBSession, cache: Cache, current_user: CurrentUser):
    entry = await RosterService(db, cache).update_entry(
        tournament_id, registration_id, entry_id, default_slot=data.default_slot, remove=data.remove,
        reason=data.reason, user=current_user)
    return Response(data=_entry(entry))


@router.get("/me/roster-invitations", response_model=Response[list[dict[str, Any]]])
async def my_roster_invitations(db: DBSession, cache: Cache, current_user: CurrentUser):
    rows = await RosterService(db, cache).my_invitations(current_user)
    return Response(data=[{**_entry(e), "tournament_name": t.name, "team_name": team.name,
                           "roster_locked_at": t.roster_locked_at} for e, t, team in rows])


@router.post("/roster-entries/{entry_id}/{action}", response_model=Response[dict[str, Any]])
async def respond_roster_entry(entry_id: uuid.UUID, action: str, db: DBSession, cache: Cache,
                               current_user: CurrentUser):
    """本人だけ: accept（参加を承認）・decline（辞退）・withdraw（固定の前の取り下げ）。"""
    from app.core.exceptions import ValidationError
    if action not in ("accept", "decline", "withdraw"):
        raise ValidationError("accept・decline・withdraw のどれかを指定してください")
    entry = await RosterService(db, cache).respond(entry_id, action, current_user)
    return Response(data=_entry(entry))


@router.post("/tournaments/{tournament_id}/roster-mode", response_model=Response[dict[str, Any]])
async def switch_to_roster(tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser):
    """旧方式（legacy）の未開始の大会を名簿の方式に切り替える（一方向。Q01）。"""
    t = await TournamentService(db, cache).switch_to_roster(tournament_id, current_user)
    return Response(data={"id": str(t.id), "roster_mode": t.roster_mode})


class DisputeBody(BaseModel):
    match_id: uuid.UUID
    reason: str = Field(..., min_length=1, max_length=2000)


class DisputeResolveBody(BaseModel):
    status: str = Field(..., pattern="^(upheld|dismissed)$")
    note: str | None = Field(default=None, max_length=2000)


def _dispute(d) -> dict[str, Any]:
    return {"id": str(d.id), "match_id": str(d.match_id), "player_id": str(d.player_id), "reason": d.reason,
            "status": d.status, "created_at": d.created_at, "resolved_at": d.resolved_at,
            "resolution_note": d.resolution_note}


@router.post("/me/participation-disputes", response_model=Response[dict[str, Any]], status_code=201)
async def create_dispute(data: DisputeBody, db: DBSession, cache: Cache, current_user: CurrentUser):
    """出場登録・実出場・成績に載った本人の「出場していない」の異議（C5）。"""
    d = await DisputeService(db, cache).create(data.match_id, data.reason, current_user)
    return Response(data=_dispute(d))


@router.get("/admin/participation-disputes", response_model=Response[list[dict[str, Any]]])
async def list_disputes(db: DBSession, cache: Cache, current_user: CurrentUser,
                        status: str | None = Query(default=None, pattern="^(open|upheld|dismissed)$")):
    rows = await DisputeService(db, cache).list(status, current_user)
    return Response(data=[_dispute(d) for d in rows])


@router.patch("/admin/participation-disputes/{dispute_id}", response_model=Response[dict[str, Any]])
async def resolve_dispute(dispute_id: uuid.UUID, data: DisputeResolveBody, db: DBSession, cache: Cache,
                          current_user: CurrentUser):
    d = await DisputeService(db, cache).resolve(dispute_id, data.status, data.note, current_user)
    return Response(data=_dispute(d))
