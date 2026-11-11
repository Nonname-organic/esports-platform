"""RC4 第 1 段: チームの所属を本人の承諾制にする。

- 所属は、本人が招待を承認したとき（invitation）か、本人の操作（self）でだけできる
- 移行前の所属は本人未確認（unconfirmed）。本人が確認（confirmed）か否認（rejected）する
- 期限（移行期間の開始 + 60 日）の後の本人未確認は、正式な所属として扱わない（D7）
- 否認を戻せるのは管理者だけで、戻す先は本人未確認だけ（Q21）
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.redis import RedisCache
from app.events import Ev, EventEnvelope, EventService
from app.models.enums import MemberRole, UserRole
from app.models.player import Player
from app.models.roster import AdminCorrection, MembershipMigrationState, TeamInvitation
from app.models.team import Team, TeamMember
from app.models.user import User

CONSENTED = ("self", "invitation", "confirmed")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def grace_deadline(db: AsyncSession) -> datetime | None:
    """本人未確認の所属を正式な所属として扱う期限。移行前の DB（行が無い）では None。"""
    state = await db.get(MembershipMigrationState, 1)
    if state is None:
        return None
    return state.started_at + timedelta(days=state.grace_days)


def formal_consents(deadline: datetime | None, now: datetime | None = None) -> tuple[str, ...]:
    """正式な所属として扱う承諾の状態。期限の前だけ本人未確認を含める（D7）。"""
    now = now or utcnow()
    if deadline is None or now < deadline:
        return CONSENTED + ("unconfirmed",)
    return CONSENTED


async def formal_clause(db: AsyncSession):
    """TeamMember を正式な所属に絞る条件（キャプテンの権限・成績の照合で使う）。"""
    return TeamMember.consent.in_(formal_consents(await grace_deadline(db)))


async def invalidate_player_caches(cache: RedisCache | None, player_ids) -> None:
    """帰属・成績が変わった選手のキャッシュを消す（設計の 6.6）。"""
    if cache is None:
        return
    for pid in {str(p) for p in player_ids if p}:
        for key in (f"career:player:{pid}", f"player_rank_card:{pid}", f"player_profile:{pid}",
                    f"player_analysis:{pid}"):
            await cache.delete(key)
        await cache.delete_pattern(f"cache:player:{pid}:stats:*")
    await cache.delete_pattern("ranking:players:*")


class MembershipService:
    def __init__(self, db: AsyncSession, cache: RedisCache | None):
        self._db = db
        self._cache = cache

    async def _emit(self, event_type: str, entity_type: str, entity_id, *, before=None, after=None) -> None:
        await EventService(self._db).emit(EventEnvelope.build(
            type=event_type, entity_type=entity_type, entity_id=entity_id,
            producer="membership", before=before, after=after,
        ))

    async def _notify(self, user_id, title: str, body: str, action_url: str, metadata: dict) -> None:
        from app.services.notification_service import NotificationService
        await NotificationService(self._db, self._cache).create(
            user_id=user_id, ntype="team_membership", title=title, body=body,
            action_url=action_url, metadata=metadata,
        )

    async def _player_of(self, user: User) -> Player | None:
        return await self._db.scalar(select(Player).where(Player.user_id == user.id))

    async def _team(self, team_id: uuid.UUID) -> Team:
        team = await self._db.get(Team, team_id)
        if team is None or not team.is_active:
            raise NotFoundError("チーム", str(team_id))
        return team

    async def require_team_manager(self, team: Team, user: User) -> None:
        """オーナー・管理者・正式な所属のキャプテンだけ（期限の後の本人未確認は持たない）。"""
        if team.owner_id == user.id or user.role == UserRole.ADMIN:
            return
        captain = await self._db.scalar(
            select(TeamMember.id).join(Player, Player.id == TeamMember.player_id).where(
                TeamMember.team_id == team.id, Player.user_id == user.id, TeamMember.left_at.is_(None),
                TeamMember.role == MemberRole.CAPTAIN, await formal_clause(self._db),
            ).limit(1))
        if captain is None:
            raise ForbiddenError("この操作はチームのオーナーかキャプテンだけが行えます")

    async def _expire_stale(self, **where) -> None:
        conds = [TeamInvitation.status == "pending", TeamInvitation.expires_at <= utcnow()]
        conds += [getattr(TeamInvitation, k) == v for k, v in where.items()]
        await self._db.execute(update(TeamInvitation).where(and_(*conds))
                               .values(status="expired", decided_at=utcnow()))

    # ── 招待 ─────────────────────────────────────────────────────────────

    async def create_invitation(self, team_id: uuid.UUID, username: str, role: MemberRole,
                                current_user: User) -> TeamInvitation:
        team = await self._team(team_id)
        await self.require_team_manager(team, current_user)
        target = await self._db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
        if target is None:
            raise NotFoundError("ユーザー", username)
        player = await self._db.scalar(select(Player).where(Player.user_id == target.id))
        if player is None:
            raise BusinessRuleError("このユーザーはプレイヤープロフィールを持っていません")
        if await self._db.scalar(select(TeamMember.id).where(
                TeamMember.team_id == team_id, TeamMember.player_id == player.id, TeamMember.left_at.is_(None))):
            raise ConflictError("このユーザーは既にチームのメンバーです")

        await self._expire_stale(team_id=team_id)
        now = utcnow()
        declined_recently = await self._db.scalar(select(TeamInvitation.id).where(
            TeamInvitation.team_id == team_id, TeamInvitation.invitee_user_id == target.id,
            TeamInvitation.status == "declined",
            TeamInvitation.decided_at > now - timedelta(days=settings.TEAM_INVITATION_REINVITE_DAYS),
        ).limit(1))
        if declined_recently:
            raise ConflictError(
                f"このユーザーは招待を断ってから {settings.TEAM_INVITATION_REINVITE_DAYS} 日たっていません")
        pending = await self._db.scalar(select(TeamInvitation.id).where(
            TeamInvitation.team_id == team_id, TeamInvitation.status == "pending").limit(
            settings.TEAM_INVITATION_MAX_PENDING).offset(settings.TEAM_INVITATION_MAX_PENDING - 1))
        if pending:
            raise ConflictError(f"返事待ちの招待は {settings.TEAM_INVITATION_MAX_PENDING} 件までです")

        inv = TeamInvitation(
            id=uuid.uuid4(), team_id=team_id, invitee_user_id=target.id, invited_by_user_id=current_user.id,
            role=role, status="pending", created_at=now,
            expires_at=now + timedelta(days=settings.TEAM_INVITATION_EXPIRY_DAYS),
        )
        try:
            async with self._db.begin_nested():  # 違反のときは、この行だけを戻す
                self._db.add(inv)
        except IntegrityError:
            raise ConflictError("このユーザーには返事待ちの招待があります") from None
        await self._emit(Ev.TEAM_MEMBER_INVITED, "team", team_id,
                         after={"invitation_id": str(inv.id), "player_id": str(player.id), "role": role.value})
        await self._notify(target.id, "チームへの招待", f"{team.name} から招待が届きました",
                           "/teams/invitations", {"invitation_id": str(inv.id), "team_id": str(team_id)})
        return inv

    async def list_team_invitations(self, team_id: uuid.UUID, current_user: User) -> list[TeamInvitation]:
        team = await self._team(team_id)
        await self.require_team_manager(team, current_user)
        await self._expire_stale(team_id=team_id)
        return list((await self._db.execute(select(TeamInvitation).where(TeamInvitation.team_id == team_id)
                                            .order_by(TeamInvitation.created_at.desc()).limit(200))).scalars())

    async def cancel_invitation(self, team_id: uuid.UUID, invitation_id: uuid.UUID, current_user: User) -> None:
        inv = await self._locked(invitation_id)
        if inv.team_id != team_id:
            raise NotFoundError("招待", str(invitation_id))
        # 送った人でも、オーナー・キャプテンでなくなっていれば取り消せない
        await self.require_team_manager(await self._team(team_id), current_user)
        if inv.status != "pending":
            raise ConflictError("返事待ちの招待だけを取り消せます")
        inv.status, inv.decided_at, inv.decided_by_user_id = "cancelled", utcnow(), current_user.id
        await self._db.flush()
        await self._emit(Ev.TEAM_MEMBER_INVITATION_CANCELLED, "team", team_id,
                         after={"invitation_id": str(inv.id)})

    async def my_invitations(self, current_user: User) -> list[tuple[TeamInvitation, Team]]:
        await self._expire_stale(invitee_user_id=current_user.id)
        return list((await self._db.execute(
            select(TeamInvitation, Team).join(Team, Team.id == TeamInvitation.team_id)
            .where(TeamInvitation.invitee_user_id == current_user.id, TeamInvitation.status == "pending")
            .order_by(TeamInvitation.created_at.desc()))).all())

    async def _locked(self, invitation_id: uuid.UUID) -> TeamInvitation:
        inv = (await self._db.execute(select(TeamInvitation).where(TeamInvitation.id == invitation_id)
                                      .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if inv is None:
            raise NotFoundError("招待", str(invitation_id))
        return inv

    async def _decide(self, invitation_id: uuid.UUID, current_user: User) -> TeamInvitation:
        inv = await self._locked(invitation_id)
        if inv.invitee_user_id != current_user.id:
            raise ForbiddenError("招待に返事ができるのは、招待された本人だけです")
        if inv.status == "pending" and inv.expires_at <= utcnow():
            inv.status, inv.decided_at = "expired", utcnow()
            await self._db.flush()
        if inv.status != "pending":
            raise ConflictError("この招待には返事ができません（期限切れか、既に返事済みです）")
        return inv

    async def accept_invitation(self, invitation_id: uuid.UUID, current_user: User) -> TeamMember:
        inv = await self._decide(invitation_id, current_user)
        team = await self._team(inv.team_id)
        player = await self._player_of(current_user)
        if player is None:
            raise BusinessRuleError("プレイヤープロフィールを作ってから招待を承認してください")
        now = utcnow()
        member = TeamMember(id=uuid.uuid4(), team_id=team.id, player_id=player.id, role=inv.role,
                            joined_at=now, consent="invitation", invitation_id=inv.id)
        try:
            async with self._db.begin_nested():  # 違反のときは、この行だけを戻す
                self._db.add(member)
        except IntegrityError:
            raise ConflictError("既にこのチームのメンバーです") from None
        inv.status, inv.decided_at, inv.decided_by_user_id, inv.membership_id = "accepted", now, current_user.id, member.id
        await self._db.flush()
        await self._emit(Ev.TEAM_MEMBER_INVITATION_ACCEPTED, "team", team.id,
                         after={"invitation_id": str(inv.id), "membership_id": str(member.id)})
        await self._emit(Ev.TEAM_MEMBER_ADDED, "team", team.id,
                         after={"player_id": str(player.id), "role": inv.role.value, "via": "invitation"})
        # 公開活動: プレイヤー視点の「チーム加入」（Activity Feed / ADR-0011）
        await EventService(self._db).emit(EventEnvelope.build(
            type=Ev.PLAYER_TEAM_JOINED, entity_type="player", entity_id=player.id,
            producer="team", metadata={"team_id": str(team.id), "team_name": team.name},
        ))
        await invalidate_player_caches(self._cache, [player.id])
        return member

    async def decline_invitation(self, invitation_id: uuid.UUID, current_user: User) -> None:
        inv = await self._decide(invitation_id, current_user)
        inv.status, inv.decided_at, inv.decided_by_user_id = "declined", utcnow(), current_user.id
        await self._db.flush()
        await self._emit(Ev.TEAM_MEMBER_INVITATION_DECLINED, "team", inv.team_id,
                         after={"invitation_id": str(inv.id)})

    # ── 移行前の所属の確認・否認 ────────────────────────────────────────

    async def my_memberships(self, current_user: User) -> dict:
        player = await self._player_of(current_user)
        rows = []
        if player is not None:
            rows = (await self._db.execute(
                select(TeamMember, Team).join(Team, Team.id == TeamMember.team_id)
                .where(TeamMember.player_id == player.id)
                .order_by(TeamMember.joined_at.desc()))).all()
        deadline = await grace_deadline(self._db)
        return {"deadline": deadline, "items": rows}

    async def _own_membership(self, membership_id: uuid.UUID, current_user: User) -> TeamMember:
        member = (await self._db.execute(select(TeamMember).where(TeamMember.id == membership_id)
                                         .with_for_update().execution_options(populate_existing=True))
                  ).scalar_one_or_none()
        player = await self._player_of(current_user)
        if member is None:
            raise NotFoundError("所属", str(membership_id))
        if player is None or member.player_id != player.id:
            raise ForbiddenError("所属の確認・否認ができるのは本人だけです")
        if member.consent != "unconfirmed":
            raise ConflictError("本人未確認の所属だけを確認・否認できます")
        return member

    async def confirm_membership(self, membership_id: uuid.UUID, current_user: User) -> TeamMember:
        member = await self._own_membership(membership_id, current_user)
        member.consent, member.confirmed_at = "confirmed", utcnow()
        await self._db.flush()
        await self._emit(Ev.TEAM_MEMBER_CONFIRMED, "team", member.team_id,
                         after={"membership_id": str(member.id), "player_id": str(member.player_id)})
        await invalidate_player_caches(self._cache, [member.player_id])
        return member

    async def reject_membership(self, membership_id: uuid.UUID, current_user: User) -> TeamMember:
        member = await self._own_membership(membership_id, current_user)
        now = utcnow()
        member.consent, member.rejected_at = "rejected", now
        if member.left_at is None:
            member.left_at = max(now, member.joined_at)
        await self._db.flush()
        await self._emit(Ev.TEAM_MEMBER_REJECTED, "team", member.team_id,
                         after={"membership_id": str(member.id), "player_id": str(member.player_id)})
        await invalidate_player_caches(self._cache, [member.player_id])
        return member

    async def unreject_membership(self, membership_id: uuid.UUID, reason: str, current_user: User) -> TeamMember:
        """管理者だけ。戻す先は本人未確認に固定（承諾済みにできるのは本人だけ）。現役には戻さない。"""
        if current_user.role != UserRole.ADMIN:
            raise ForbiddenError("否認を取り消せるのは管理者だけです")
        if not (reason or "").strip():
            raise BusinessRuleError("理由を入力してください")
        member = (await self._db.execute(select(TeamMember).where(TeamMember.id == membership_id)
                                         .with_for_update())).scalar_one_or_none()
        if member is None:
            raise NotFoundError("所属", str(membership_id))
        if member.consent != "rejected":
            raise ConflictError("本人否認の所属だけを戻せます")
        before = {"consent": member.consent, "rejected_at": member.rejected_at.isoformat() if member.rejected_at else None}
        member.consent, member.rejected_at = "unconfirmed", None
        correction = AdminCorrection(id=uuid.uuid4(), kind="membership_unreject", membership_id=member.id,
                                     reason=reason.strip(), actor_user_id=current_user.id,
                                     before=before, after={"consent": "unconfirmed", "rejected_at": None})
        self._db.add(correction)
        await self._db.flush()
        await self._emit(Ev.ADMIN_CORRECTION_APPLIED, "team", member.team_id,
                         after={"correction_id": str(correction.id), "kind": "membership_unreject"})
        player = await self._db.get(Player, member.player_id)
        if player is not None and player.user_id:
            await self._notify(player.user_id, "所属の否認が取り消されました",
                               "管理者が否認を取り消しました。所属を確認するか、改めて否認してください。",
                               "/settings/memberships", {"correction_id": str(correction.id)})
        await invalidate_player_caches(self._cache, [member.player_id])
        return member
