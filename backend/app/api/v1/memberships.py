"""RC4 第 1 段の API: チームの招待、移行前の所属の確認・否認、管理者による否認の取り消し。

承諾の操作（招待の承認・拒否、所属の確認・否認）は本人だけが行える。管理者も代われない。
"""
import uuid

from fastapi import APIRouter

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.schemas.common import Response
from app.schemas.team import (
    MembershipSchema,
    MyMembershipsResponse,
    MyTeamInvitationSchema,
    ReasonRequest,
    TeamInvitationCreate,
    TeamInvitationSchema,
)
from app.services.membership import MembershipService, formal_consents

router = APIRouter(tags=["チームの招待と所属の確認"])


def _membership(member, team, formal: tuple[str, ...]) -> MembershipSchema:
    return MembershipSchema(
        id=member.id, team_id=team.id, team_name=team.name, team_tag=team.tag,
        role=member.role.value, joined_at=member.joined_at, left_at=member.left_at,
        consent=member.consent, confirmed_at=member.confirmed_at, rejected_at=member.rejected_at,
        formal=member.left_at is None and member.consent in formal,
    )


@router.post("/teams/{team_id}/invitations", response_model=Response[TeamInvitationSchema], status_code=201)
async def create_invitation(team_id: uuid.UUID, data: TeamInvitationCreate, db: DBSession, cache: Cache,
                            current_user: CurrentUser):
    inv = await MembershipService(db, cache).create_invitation(team_id, data.username, data.role, current_user)
    return Response(data=TeamInvitationSchema.model_validate(inv), meta=None)


@router.get("/teams/{team_id}/invitations", response_model=Response[list[TeamInvitationSchema]])
async def list_team_invitations(team_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser):
    from sqlalchemy import select
    from app.models.user import User
    rows = await MembershipService(db, cache).list_team_invitations(team_id, current_user)
    names = dict((await db.execute(select(User.id, User.username).where(
        User.id.in_({r.invitee_user_id for r in rows} or {uuid.uuid4()})))).all())
    return Response(data=[TeamInvitationSchema.model_validate(r).model_copy(
        update={"invitee_username": names.get(r.invitee_user_id)}) for r in rows], meta=None)


@router.delete("/teams/{team_id}/invitations/{invitation_id}", status_code=204)
async def cancel_invitation(team_id: uuid.UUID, invitation_id: uuid.UUID, db: DBSession, cache: Cache,
                            current_user: CurrentUser):
    await MembershipService(db, cache).cancel_invitation(team_id, invitation_id, current_user)


@router.get("/me/team-invitations", response_model=Response[list[MyTeamInvitationSchema]])
async def my_team_invitations(db: DBSession, cache: Cache, current_user: CurrentUser):
    rows = await MembershipService(db, cache).my_invitations(current_user)
    return Response(data=[
        MyTeamInvitationSchema(**TeamInvitationSchema.model_validate(inv).model_dump(),
                               team_name=team.name, team_tag=team.tag)
        for inv, team in rows
    ], meta=None)


@router.post("/team-invitations/{invitation_id}/accept", response_model=Response[dict])
async def accept_invitation(invitation_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser):
    member = await MembershipService(db, cache).accept_invitation(invitation_id, current_user)
    return Response(data={"membership_id": str(member.id), "team_id": str(member.team_id)}, meta=None)


@router.post("/team-invitations/{invitation_id}/decline", status_code=204)
async def decline_invitation(invitation_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser):
    await MembershipService(db, cache).decline_invitation(invitation_id, current_user)


@router.get("/me/memberships", response_model=Response[MyMembershipsResponse])
async def my_memberships(db: DBSession, cache: Cache, current_user: CurrentUser):
    result = await MembershipService(db, cache).my_memberships(current_user)
    formal = formal_consents(result["deadline"])
    return Response(data=MyMembershipsResponse(
        deadline=result["deadline"], items=[_membership(m, t, formal) for m, t in result["items"]]), meta=None)


@router.post("/me/memberships/{membership_id}/confirm", response_model=Response[dict])
async def confirm_membership(membership_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser):
    member = await MembershipService(db, cache).confirm_membership(membership_id, current_user)
    return Response(data={"id": str(member.id), "consent": member.consent}, meta=None)


@router.post("/me/memberships/{membership_id}/reject", response_model=Response[dict])
async def reject_membership(membership_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser):
    member = await MembershipService(db, cache).reject_membership(membership_id, current_user)
    return Response(data={"id": str(member.id), "consent": member.consent}, meta=None)


@router.post("/admin/memberships/{membership_id}/unreject", response_model=Response[dict])
async def unreject_membership(membership_id: uuid.UUID, data: ReasonRequest, db: DBSession, cache: Cache,
                              current_user: CurrentUser):
    member = await MembershipService(db, cache).unreject_membership(membership_id, data.reason, current_user)
    return Response(data={"id": str(member.id), "consent": member.consent}, meta=None)
