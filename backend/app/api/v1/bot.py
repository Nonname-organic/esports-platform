"""Discord Bot service API (/api/v1/bot).

全エンドポイントは `X-Bot-Secret`（Bot↔Backend共有秘密）で認証する。
書き込み・操作系は `X-Discord-User-Id` から DiscordLink→User を解決し、
**その実ユーザーの権限**で権威判定する（多層防御）。Botのロールは詐称可能なため、
最終的なRBACは常にここで行う。

設計詳細: docs/architecture/DISCORD_OS_DESIGN.md §5
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.dependencies import BotActor, BotAuth, Cache, DBSession
from app.core.exceptions import (
    BusinessRuleError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.models.bot_ops import BotErrorLog, CommandMetric, MatchDispute
from app.models.enums import (
    MatchStatus,
    MemberRole,
    RegistrationStatus,
    TournamentStatus,
    UserRole,
)
from app.models.match import Match
from app.models.player import Player
from app.models.scout import ScoutProfile
from app.models.team import Team, TeamMember
from app.models.tournament import Notification, Tournament, TournamentRegistration
from app.models.user import User
from app.services.match import MatchService
from app.services.tournament import TournamentService

router = APIRouter(prefix="/bot", tags=["bot"])


# ── helpers ───────────────────────────────────────────────────────────────────
async def _require_actor(actor: Optional[User]) -> User:
    if actor is None:
        raise UnauthorizedError("Discordアカウントが未連携です。/link で連携してください")
    return actor


async def _actor_context(db, user: User) -> dict:
    """解決ユーザーの player / 所属チーム / キャプテンチームを返す。"""
    player = (
        await db.execute(select(Player).where(Player.user_id == user.id))
    ).scalar_one_or_none()
    teams: list[dict] = []
    captain_team_ids: list[uuid.UUID] = []
    if player:
        rows = (
            await db.execute(
                select(TeamMember, Team)
                .join(Team, Team.id == TeamMember.team_id)
                .where(TeamMember.player_id == player.id, TeamMember.left_at.is_(None))
            )
        ).all()
        for tm, team in rows:
            teams.append(
                {"id": str(team.id), "name": team.name, "tag": team.tag, "role": tm.role.value}
            )
            if tm.role == MemberRole.CAPTAIN:
                captain_team_ids.append(team.id)
    return {
        "player_id": str(player.id) if player else None,
        "in_game_name": player.in_game_name if player else None,
        "team_ids": [uuid.UUID(t["id"]) for t in teams],
        "captain_team_ids": captain_team_ids,
        "teams": teams,
    }


def _is_organizer(user: User) -> bool:
    return user.role in (UserRole.ADMIN, UserRole.ORGANIZER, UserRole.TEAM_MANAGER)


# ── resolve ─────────────────────────────────────────────────────────────────
@router.get("/resolve")
async def resolve(db: DBSession, _: BotAuth, actor: BotActor):
    """Discordユーザーのプラットフォーム要約（ロール/プレイヤー/所属チーム）。"""
    if actor is None:
        return {"data": {"linked": False}}
    ctx = await _actor_context(db, actor)
    return {
        "data": {
            "linked": True,
            "user_id": str(actor.id),
            "role": actor.role.value,
            "is_organizer": _is_organizer(actor),
            "player_id": ctx["player_id"],
            "in_game_name": ctx["in_game_name"],
            "teams": ctx["teams"],
            "captain_team_ids": [str(t) for t in ctx["captain_team_ids"]],
        }
    }


# ── tournament status ───────────────────────────────────────────────────────
class StatusBody(BaseModel):
    status: str  # start→ongoing, end→completed, cancel→cancelled, or raw status value


_STATUS_ALIAS = {
    "start": TournamentStatus.ONGOING,
    "end": TournamentStatus.COMPLETED,
    "cancel": TournamentStatus.CANCELLED,
}


@router.post("/tournaments/{tournament_id}/status")
async def change_tournament_status(
    tournament_id: uuid.UUID, body: StatusBody, db: DBSession, cache: Cache,
    _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    try:
        new_status = _STATUS_ALIAS.get(body.status) or TournamentStatus(body.status)
    except ValueError:
        raise BusinessRuleError(f"不明なステータス: {body.status}")
    # change_status 内部で organizer/owner のRBACが効く（権威判定）
    service = TournamentService(db, cache)
    t = await service.change_status(tournament_id, new_status, user)
    return {"data": {"id": str(t.id), "status": t.status.value, "name": t.name}}


@router.post("/tournaments/{tournament_id}/bracket")
async def generate_bracket(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, _: BotAuth, actor: BotActor,
):
    """ブラケット生成/再生成。generate_bracket 内部で運営RBACが効く。"""
    user = await _require_actor(actor)
    service = TournamentService(db, cache)
    await service.generate_bracket(tournament_id, user)
    return {"data": {"ok": True}}


# ── check-in ────────────────────────────────────────────────────────────────
async def _reg_for_user_team(db, tournament_id: uuid.UUID, team_ids: list[uuid.UUID]):
    if not team_ids:
        return None
    return (
        await db.execute(
            select(TournamentRegistration).where(
                TournamentRegistration.tournament_id == tournament_id,
                TournamentRegistration.team_id.in_(team_ids),
            )
        )
    ).scalar_one_or_none()


@router.post("/tournaments/{tournament_id}/check-in")
async def self_check_in(
    tournament_id: uuid.UUID, db: DBSession, _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    ctx = await _actor_context(db, user)
    reg = await _reg_for_user_team(db, tournament_id, ctx["team_ids"])
    if reg is None:
        raise NotFoundError("登録", "あなたのチームはこの大会に登録されていません")
    if reg.status != RegistrationStatus.APPROVED:
        raise BusinessRuleError("承認済みの登録のみチェックインできます")
    reg.checked_in_at = datetime.now(timezone.utc)
    reg.checked_in_via = "discord"
    await db.flush()
    return {"data": {"checked_in": True, "team_id": str(reg.team_id), "at": reg.checked_in_at.isoformat()}}


@router.post("/tournaments/{tournament_id}/check-in-all")
async def check_in_all(
    tournament_id: uuid.UUID, db: DBSession, _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    tournament = (
        await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    ).scalar_one_or_none()
    if not tournament:
        raise NotFoundError("大会", str(tournament_id))
    if user.role != UserRole.ADMIN and tournament.organizer_id != user.id:
        raise ForbiddenError("一括チェックインの権限がありません")
    regs = (
        await db.execute(
            select(TournamentRegistration).where(
                TournamentRegistration.tournament_id == tournament_id,
                TournamentRegistration.status == RegistrationStatus.APPROVED,
            )
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    count = 0
    for reg in regs:
        if reg.checked_in_at is None:
            reg.checked_in_at = now
            reg.checked_in_via = "admin"
            count += 1
    await db.flush()
    return {"data": {"checked_in": count, "total": len(regs)}}


@router.get("/tournaments/{tournament_id}/check-in-status")
async def check_in_status(tournament_id: uuid.UUID, db: DBSession, _: BotAuth):
    regs = (
        await db.execute(
            select(TournamentRegistration, Team)
            .join(Team, Team.id == TournamentRegistration.team_id)
            .where(
                TournamentRegistration.tournament_id == tournament_id,
                TournamentRegistration.status == RegistrationStatus.APPROVED,
            )
        )
    ).all()
    checked, missed = [], []
    for reg, team in regs:
        entry = {"team_id": str(team.id), "name": team.name, "tag": team.tag}
        (checked if reg.checked_in_at else missed).append(entry)
    return {
        "data": {
            "total": len(regs),
            "checked_in_count": len(checked),
            "missed_count": len(missed),
            "checked_in": checked,
            "missed": missed,
        }
    }


# ── match result flow (report → confirm) ─────────────────────────────────────
class ReportBody(BaseModel):
    winner_id: str


def _redis_report_key(match_id: uuid.UUID) -> str:
    return f"bot:reported:{match_id}"


async def _finalize_result(db, cache, match: Match, winner_id: uuid.UUID, user: User) -> None:
    """既存サービスで結果を確定（必要なら自動でstart）。"""
    service = MatchService(db, cache)
    if match.status == MatchStatus.SCHEDULED:
        await service.start_match(match.id, user)
    from app.schemas.match import MatchResultCreate
    await service.register_result(match.id, MatchResultCreate(winner_id=str(winner_id)), user)


@router.post("/matches/{match_id}/report")
async def report_result(
    match_id: uuid.UUID, body: ReportBody, db: DBSession, cache: Cache,
    _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    if not match:
        raise NotFoundError("試合", str(match_id))
    winner_id = uuid.UUID(body.winner_id)
    if winner_id not in (match.team1_id, match.team2_id):
        raise BusinessRuleError("勝者はこの試合の参加チームである必要があります")

    tournament = (
        await db.execute(select(Tournament).where(Tournament.id == match.tournament_id))
    ).scalar_one_or_none()
    ctx = await _actor_context(db, user)
    is_owner = tournament and (user.role == UserRole.ADMIN or tournament.organizer_id == user.id)
    is_captain = any(tid in (match.team1_id, match.team2_id) for tid in ctx["captain_team_ids"])
    if not (is_owner or is_captain):
        raise ForbiddenError("結果を報告できるのは運営または対戦チームのキャプテンのみです")

    # 運営は即確定。キャプテンは相手の確認待ち（Redisに保留）。
    if is_owner:
        await _finalize_result(db, cache, match, winner_id, user)
        return {"data": {"status": "confirmed", "winner_id": str(winner_id)}}

    reporter_team = next(
        tid for tid in ctx["captain_team_ids"] if tid in (match.team1_id, match.team2_id)
    )
    await cache.set(
        _redis_report_key(match_id),
        {"winner_id": str(winner_id), "by_team": str(reporter_team), "by_user": str(user.id)},
        ttl=86400,
    )
    return {"data": {"status": "pending_confirmation", "winner_id": str(winner_id)}}


@router.post("/matches/{match_id}/confirm")
async def confirm_result(
    match_id: uuid.UUID, db: DBSession, cache: Cache, _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    pending = await cache.get(_redis_report_key(match_id))
    if not pending:
        raise BusinessRuleError("確認待ちの報告がありません")
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    if not match:
        raise NotFoundError("試合", str(match_id))
    ctx = await _actor_context(db, user)
    reporter_team = uuid.UUID(pending["by_team"])
    other_team = match.team1_id if reporter_team == match.team2_id else match.team2_id
    # 確認は「報告した側ではない方のキャプテン」または運営
    tournament = (
        await db.execute(select(Tournament).where(Tournament.id == match.tournament_id))
    ).scalar_one_or_none()
    is_owner = tournament and (user.role == UserRole.ADMIN or tournament.organizer_id == user.id)
    if not (is_owner or other_team in ctx["captain_team_ids"]):
        raise ForbiddenError("確認できるのは相手チームのキャプテンまたは運営のみです")

    await _finalize_result(db, cache, match, uuid.UUID(pending["winner_id"]), user)
    await cache.delete(_redis_report_key(match_id))
    return {"data": {"status": "confirmed", "winner_id": pending["winner_id"]}}


class DisputeBody(BaseModel):
    reason: str


@router.post("/matches/{match_id}/dispute")
async def dispute_result(
    match_id: uuid.UUID, body: DisputeBody, db: DBSession, _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    if not match:
        raise NotFoundError("試合", str(match_id))
    ctx = await _actor_context(db, user)
    is_participant = any(tid in (match.team1_id, match.team2_id) for tid in ctx["team_ids"])
    if not (is_participant or _is_organizer(user)):
        raise ForbiddenError("異議を申し立てられるのは参加者または運営のみです")
    dispute = MatchDispute(
        match_id=match_id, raised_by=user.id, reason=body.reason, status="open",
    )
    db.add(dispute)
    await db.flush()
    return {"data": {"id": str(dispute.id), "status": "open"}}


class ForfeitBody(BaseModel):
    winner_id: str


@router.post("/matches/{match_id}/forfeit")
async def forfeit_match(
    match_id: uuid.UUID, body: ForfeitBody, db: DBSession, cache: Cache,
    _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    if not match:
        raise NotFoundError("試合", str(match_id))
    tournament = (
        await db.execute(select(Tournament).where(Tournament.id == match.tournament_id))
    ).scalar_one_or_none()
    if not (user.role == UserRole.ADMIN or (tournament and tournament.organizer_id == user.id)):
        raise ForbiddenError("不戦敗を設定できるのは運営のみです")
    winner_id = uuid.UUID(body.winner_id)
    if winner_id not in (match.team1_id, match.team2_id):
        raise BusinessRuleError("勝者はこの試合の参加チームである必要があります")
    match.status = MatchStatus.FORFEIT
    match.winner_id = winner_id
    match.ended_at = datetime.now(timezone.utc)
    await db.flush()
    return {"data": {"status": "forfeit", "winner_id": str(winner_id)}}


@router.post("/matches/{match_id}/reopen")
async def reopen_match(
    match_id: uuid.UUID, db: DBSession, _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    if not match:
        raise NotFoundError("試合", str(match_id))
    tournament = (
        await db.execute(select(Tournament).where(Tournament.id == match.tournament_id))
    ).scalar_one_or_none()
    if not (user.role == UserRole.ADMIN or (tournament and tournament.organizer_id == user.id)):
        raise ForbiddenError("試合を再オープンできるのは運営のみです")
    match.status = MatchStatus.ONGOING
    match.winner_id = None
    match.ended_at = None
    await db.flush()
    return {"data": {"status": "ongoing"}}


# ── user-scoped reads ────────────────────────────────────────────────────────
@router.get("/users/{discord_user_id}/matches")
async def my_matches(
    discord_user_id: str, db: DBSession, _: BotAuth, actor: BotActor,
    limit: int = Query(10, ge=1, le=50),
):
    user = await _require_actor(actor)
    ctx = await _actor_context(db, user)
    if not ctx["team_ids"]:
        return {"data": []}
    rows = (
        await db.execute(
            select(Match)
            .where(
                (Match.team1_id.in_(ctx["team_ids"])) | (Match.team2_id.in_(ctx["team_ids"]))
            )
            .order_by(Match.round_number.asc(), Match.match_number.asc())
            .limit(limit)
        )
    ).scalars().all()
    out = [
        {
            "id": str(m.id),
            "tournament_id": str(m.tournament_id),
            "round_number": m.round_number,
            "match_number": m.match_number,
            "status": m.status.value,
            "team1_id": str(m.team1_id) if m.team1_id else None,
            "team2_id": str(m.team2_id) if m.team2_id else None,
            "winner_id": str(m.winner_id) if m.winner_id else None,
        }
        for m in rows
    ]
    return {"data": out}


@router.get("/users/{discord_user_id}/notifications")
async def my_notifications(
    discord_user_id: str, db: DBSession, _: BotAuth, actor: BotActor,
    unread: bool = False, limit: int = Query(10, ge=1, le=30),
):
    user = await _require_actor(actor)
    q = select(Notification).where(Notification.user_id == user.id)
    if unread:
        q = q.where(Notification.is_read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    unread_count = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id, Notification.is_read == False  # noqa: E712
            )
        )
    ).scalar_one()
    out = [
        {
            "id": str(n.id),
            "type": n.type.value if hasattr(n.type, "value") else str(n.type),
            "title": n.title,
            "body": n.body,
            "is_read": n.is_read,
            "action_url": n.action_url,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]
    return {"data": {"items": out, "unread_count": unread_count}}


# ── scout: open/close to work ────────────────────────────────────────────────
class LookingBody(BaseModel):
    looking: bool


@router.post("/players/{player_id}/looking")
async def set_looking(
    player_id: uuid.UUID, body: LookingBody, db: DBSession, _: BotAuth, actor: BotActor,
):
    user = await _require_actor(actor)
    player = (await db.execute(select(Player).where(Player.id == player_id))).scalar_one_or_none()
    if not player:
        raise NotFoundError("プレイヤー", str(player_id))
    if player.user_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("自分のプロフィールのみ変更できます")
    profile = (
        await db.execute(select(ScoutProfile).where(ScoutProfile.player_id == player_id))
    ).scalar_one_or_none()
    if profile is None:
        now = datetime.now(timezone.utc)
        profile = ScoutProfile(
            player_id=player_id, type="player", is_looking=body.looking,
            created_at=now, updated_at=now,
        )
        db.add(profile)
    else:
        profile.is_looking = body.looking
        profile.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"data": {"player_id": str(player_id), "is_looking": body.looking}}


# ── monitoring ingest ────────────────────────────────────────────────────────
class MetricItem(BaseModel):
    guild_id: Optional[str] = None
    discord_user_id: Optional[str] = None
    command: str
    success: bool = True
    latency_ms: Optional[int] = None
    error_type: Optional[str] = None


class MetricsBody(BaseModel):
    items: list[MetricItem]


@router.post("/metrics")
async def ingest_metrics(body: MetricsBody, db: DBSession, _: BotAuth):
    for it in body.items[:200]:  # 上限ガード
        db.add(CommandMetric(
            guild_id=it.guild_id, discord_user_id=it.discord_user_id, command=it.command,
            success=it.success, latency_ms=it.latency_ms, error_type=it.error_type,
        ))
    await db.flush()
    return {"data": {"ingested": min(len(body.items), 200)}}


class ErrorBody(BaseModel):
    guild_id: Optional[str] = None
    discord_user_id: Optional[str] = None
    command: Optional[str] = None
    error_type: str
    message: str
    traceback: Optional[str] = None


@router.post("/errors")
async def ingest_error(body: ErrorBody, db: DBSession, _: BotAuth):
    db.add(BotErrorLog(
        guild_id=body.guild_id, discord_user_id=body.discord_user_id, command=body.command,
        error_type=body.error_type, message=body.message[:8000],
        traceback=(body.traceback or "")[:16000] or None,
    ))
    await db.flush()
    return {"data": {"logged": True}}
