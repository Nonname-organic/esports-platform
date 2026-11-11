"""RC4 第 2 段: 大会の方式（legacy / roster）・名簿・試合の出場登録・交代・出場の異議。

包含（設計の 2.2）: 成績 ⊆ マップの実出場 ⊆ 出場登録 ⊆ 名簿 ⊆ 承認済みの参加登録 ⊆ 正式な所属。
状態（承認・accepted・承諾）は書き込みのたびに、試合の行ロックの中で確かめる（Q06）。
"""
import uuid
from collections import defaultdict

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.redis import RedisCache
from app.events import Ev, EventEnvelope, EventService
from app.models.enums import GameType, MatchStatus, RegistrationStatus, TournamentStatus, UserRole
from app.models.match import Match, MatchGame, MatchResult, PlayerMatchStats
from app.models.player import Player
from app.models.roster import (
    AdminCorrection,
    MatchLineupEntry,
    MatchSubstitution,
    ParticipationDispute,
    TournamentRosterEntry,
)
from app.models.team import Team, TeamMember
from app.models.tournament import Tournament, TournamentRegistration
from app.models.user import User
from app.services.membership import (
    CONSENTED,
    MembershipService,
    formal_consents,
    grace_deadline,
    invalidate_player_caches,
    utcnow,
)

NOT_STARTED = (TournamentStatus.DRAFT, TournamentStatus.REGISTRATION_OPEN,
               TournamentStatus.REGISTRATION_CLOSED, TournamentStatus.CHECK_IN)
CLOSED = (TournamentStatus.COMPLETED, TournamentStatus.CANCELLED)
ROSTER_PREP_REGISTRATION = (RegistrationStatus.PENDING, RegistrationStatus.APPROVED, RegistrationStatus.WAITLISTED)
NO_PLAYER_STATS_GAMES = (GameType.APEX,)  # Q14: 2 チームの対戦でない形式は選手の成績を受け付けない
ACTIVE_ROSTER = ("invited", "accepted")


# ── 大会の方式と状態の規則 ──────────────────────────────────────────────────

def is_legacy(t: Tournament) -> bool:
    return t.roster_mode == "legacy"


def lineup_limits(t: Tournament) -> tuple[int, int] | None:
    """(出場人数, 名簿の上限)。VALORANT は既定 5・7。ほかのゲームは主催者が入れる（Q14）。"""
    if t.lineup_size:
        return t.lineup_size, max(t.roster_max or t.lineup_size, t.lineup_size)
    if t.game == GameType.VALORANT:
        return 5, 7
    return None


def require_limits(t: Tournament) -> tuple[int, int]:
    limits = lineup_limits(t)
    if limits is None:
        raise BusinessRuleError("この大会は出場人数と名簿の上限が未設定です。大会の設定で入れてください")
    return limits


def require_roster_mode(t: Tournament) -> None:
    if is_legacy(t):
        raise ConflictError("この大会は名簿の無い旧方式（legacy）です。名簿の方式に切り替えてから操作してください")


def is_organizer(t: Tournament, user: User) -> bool:
    return user.role == UserRole.ADMIN or t.organizer_id == user.id


def closed_tournament_guard(t: Tournament, user: User, reason: str | None) -> bool:
    """完了・中止の大会の変更は管理者だけ（理由つき。Q15）。管理者の訂正のときは True。"""
    if t.status not in CLOSED:
        return False
    if user.role != UserRole.ADMIN:
        raise ConflictError("完了・中止した大会は変更できません（管理者の訂正だけが行えます）")
    if not (reason or "").strip():
        raise BusinessRuleError("完了・中止した大会の訂正には理由が必要です")
    return True


async def record_correction(db: AsyncSession, *, kind: str, reason: str, actor: User, before: dict, after: dict,
                            tournament_id=None, match_id=None, membership_id=None) -> AdminCorrection:
    c = AdminCorrection(id=uuid.uuid4(), kind=kind, reason=reason.strip(), actor_user_id=actor.id,
                        tournament_id=tournament_id, match_id=match_id, membership_id=membership_id,
                        before=before, after=after)
    db.add(c)
    await db.flush()
    await EventService(db).emit(EventEnvelope.build(
        type=Ev.ADMIN_CORRECTION_APPLIED, entity_type="tournament" if tournament_id else "match",
        entity_id=tournament_id or match_id, producer="admin",
        after={"correction_id": str(c.id), "kind": kind}))
    return c


async def lock_roster(db: AsyncSession, t: Tournament) -> None:
    """名簿を固定する（Q17）。固定の前に返事の無かった名簿の招待は期限切れにする。"""
    if t.roster_mode != "roster" or t.roster_locked_at is not None:
        return
    now = utcnow()
    t.roster_locked_at = now
    await db.execute(update(TournamentRosterEntry).where(
        TournamentRosterEntry.tournament_id == t.id, TournamentRosterEntry.status == "invited",
    ).values(status="expired", responded_at=now))
    await db.flush()
    await db.refresh(t)  # updated_at などサーバー側で変わる列を読み直す（非同期で遅延読み込みしない）


async def _emit(db, event_type: str, entity_type: str, entity_id, *, after: dict) -> None:
    await EventService(db).emit(EventEnvelope.build(
        type=event_type, entity_type=entity_type, entity_id=entity_id, producer="roster", after=after))


async def _notify(db, cache, user_id, title: str, body: str, url: str, meta: dict) -> None:
    if not user_id:
        return
    from app.services.notification_service import NotificationService
    await NotificationService(db, cache).create(user_id=user_id, ntype="tournament_roster", title=title,
                                                body=body, action_url=url, metadata=meta)


async def _user_id_of(db, player_id) -> uuid.UUID | None:
    return await db.scalar(select(Player.user_id).where(Player.id == player_id))


# ── 承認の確認（Q06）──────────────────────────────────────────────────────

async def approval_errors(db: AsyncSession, entries: list[MatchLineupEntry],
                          require_active: bool = False) -> dict[uuid.UUID, str]:
    """出場登録の行ごとに、満たしていない承認を返す（参加登録・名簿・所属）。

    require_active: 出場登録の書き込み・固定・交代のときは、所属が現役であることも求める（T25）。
    成績の保存では求めない（試合の後にチームを抜けた選手の成績は直せる）。
    """
    if not entries:
        return {}
    formal = formal_consents(await grace_deadline(db))
    rows = (await db.execute(
        select(TournamentRosterEntry.id, TournamentRosterEntry.status, TournamentRegistration.status,
               TeamMember.consent, TeamMember.left_at)
        .join(TournamentRegistration, TournamentRegistration.id == TournamentRosterEntry.registration_id)
        .join(TeamMember, TeamMember.id == TournamentRosterEntry.membership_id)
        .where(TournamentRosterEntry.id.in_({e.roster_entry_id for e in entries}))
    )).all()
    state = {r[0]: (r[1], r[2], r[3], r[4]) for r in rows}
    errors = {}
    for e in entries:
        roster_status, reg_status, consent, left_at = state.get(e.roster_entry_id, (None, None, None, None))
        if reg_status != RegistrationStatus.APPROVED:
            errors[e.id] = "参加登録が承認されていません"
        elif roster_status != "accepted":
            errors[e.id] = "本人が名簿への参加を承認していません"
        elif consent not in formal:
            errors[e.id] = "チームへの所属が正式な所属ではありません"
        elif require_active and left_at is not None:
            errors[e.id] = "チームを脱退した選手は出場登録に選べません"
    return errors


# ── マップごとの実出場（設計の 2.4・Q09）────────────────────────────────────

async def participation(db: AsyncSession, match: Match, upto_game: int | None = None,
                        exclude_sub: uuid.UUID | None = None) -> dict:
    """{(team_id, game_number): {"start": {entry_id}, "participants": {entry_id}, "end": {entry_id}}}"""
    entries = list((await db.execute(select(MatchLineupEntry).where(
        MatchLineupEntry.match_id == match.id, MatchLineupEntry.removed_at.is_(None)))).scalars())
    subs = list((await db.execute(select(MatchSubstitution).where(
        MatchSubstitution.match_id == match.id, MatchSubstitution.status == "approved",
    ).order_by(MatchSubstitution.game_number, MatchSubstitution.approved_at, MatchSubstitution.requested_at)
    )).scalars())
    subs = [s for s in subs if s.id != exclude_sub]
    games = set((await db.execute(select(MatchGame.game_number).where(MatchGame.match_id == match.id))).scalars())
    return compute_timeline(entries, subs, games | {upto_game or 1})


def compute_timeline(entries: list, subs: list, games) -> dict:
    """設計の 2.4 の計算（DB を読まない）。subs は承認済みの交代を、マップ・承認の順に並べたもの。

    games は計算するマップの番号。交代のあるマップを足して、番号の順に 1 回ずつだけ回す。
    交代の無いマップでは出場者が変わらないので、間の番号を飛ばしても結果は同じ（番号の大きさで回数が増えない）。
    """
    numbers = sorted({int(g) for g in games} | {s.game_number for s in subs})
    out: dict = {}
    for team_id in {e.team_id for e in entries}:
        playing = {e.id for e in entries if e.team_id == team_id and e.slot == "starter"}
        for g in numbers:
            for s in subs:
                if s.team_id == team_id and s.game_number == g and s.kind in ("between_maps", "fill"):
                    playing.discard(s.out_lineup_entry_id)
                    playing.add(s.in_lineup_entry_id)
            start = set(playing)
            participants = set(start)
            for s in subs:
                if s.team_id == team_id and s.game_number == g and s.kind == "mid_map":
                    playing.discard(s.out_lineup_entry_id)
                    playing.add(s.in_lineup_entry_id)
                    participants.add(s.in_lineup_entry_id)
            out[(team_id, g)] = {"start": start, "participants": participants, "end": set(playing)}
    return out


async def participants_by_player(db: AsyncSession, match: Match, game_number: int) -> dict:
    """{(team_id, player_id): lineup_entry_id}: そのマップで成績を登録できる選手。"""
    timeline = await participation(db, match, upto_game=game_number)
    ids = set()
    for (_team_id, g), sets in timeline.items():
        if g == game_number:
            ids |= sets["participants"]
    if not ids:
        return {}
    rows = (await db.execute(select(MatchLineupEntry).where(MatchLineupEntry.id.in_(ids)))).scalars()
    return {(e.team_id, e.player_id): e.id for e in rows}


# ── 名簿 ─────────────────────────────────────────────────────────────────

class RosterService:
    def __init__(self, db: AsyncSession, cache: RedisCache | None):
        self._db = db
        self._cache = cache

    async def _context(self, tournament_id: uuid.UUID, registration_id: uuid.UUID):
        t = await self._db.get(Tournament, tournament_id)
        if t is None:
            raise NotFoundError("大会", str(tournament_id))
        reg = (await self._db.execute(select(TournamentRegistration).where(
            TournamentRegistration.id == registration_id, TournamentRegistration.tournament_id == tournament_id,
        ).with_for_update())).scalar_one_or_none()
        if reg is None:
            raise NotFoundError("参加登録", str(registration_id))
        team = await self._db.get(Team, reg.team_id)
        return t, reg, team

    async def _scope(self, t: Tournament, team: Team, user: User, reason: str | None) -> str:
        """変更できる立場: team（固定の前）・organizer（固定の後は理由が必須）・admin（完了の後の訂正）。"""
        if closed_tournament_guard(t, user, reason):
            return "admin"
        if t.roster_locked_at is None:
            if is_organizer(t, user):
                return "organizer"
            await MembershipService(self._db, self._cache).require_team_manager(team, user)
            return "team"
        if not is_organizer(t, user):
            raise ConflictError("名簿は固定されています。変更は大会の主催者に依頼してください")
        if not (reason or "").strip():
            raise BusinessRuleError("固定の後の名簿の変更には理由が必要です")
        return "organizer"

    async def can_view(self, t: Tournament, team: Team, user: User) -> bool:
        """D18: 名簿は参加チームの正式な所属者・オーナー・主催者・管理者だけ。"""
        if is_organizer(t, user) or team.owner_id == user.id:
            return True
        return bool(await self._db.scalar(
            select(TeamMember.id).join(Player, Player.id == TeamMember.player_id).where(
                TeamMember.team_id == team.id, Player.user_id == user.id, TeamMember.left_at.is_(None),
                TeamMember.consent.in_(formal_consents(await grace_deadline(self._db)))).limit(1)))

    async def get_roster(self, tournament_id, registration_id, user: User) -> list[TournamentRosterEntry]:
        t, _reg, team = await self._context(tournament_id, registration_id)
        if not await self.can_view(t, team, user):
            raise ForbiddenError("この名簿を見る権限がありません")
        return list((await self._db.execute(select(TournamentRosterEntry).where(
            TournamentRosterEntry.registration_id == registration_id,
        ).order_by(TournamentRosterEntry.invited_at))).scalars())

    async def add_entry(self, tournament_id, registration_id, player_id, default_slot: str,
                        reason: str | None, user: User) -> TournamentRosterEntry:
        t, reg, team = await self._context(tournament_id, registration_id)
        require_roster_mode(t)
        scope = await self._scope(t, team, user, reason)
        if reg.status not in ROSTER_PREP_REGISTRATION:
            raise ConflictError("辞退・却下した参加登録の名簿は作れません")
        _lineup, roster_max = require_limits(t)
        member = await self._db.scalar(select(TeamMember).where(
            TeamMember.team_id == team.id, TeamMember.player_id == player_id, TeamMember.left_at.is_(None)))
        if member is None or member.consent not in CONSENTED:
            raise BusinessRuleError("名簿に載せられるのは、本人が承諾したチームの現役の所属の選手だけです")
        active = await self._db.scalar(select(func.count()).select_from(TournamentRosterEntry).where(
            TournamentRosterEntry.registration_id == reg.id, TournamentRosterEntry.status.in_(ACTIVE_ROSTER)))
        if active >= roster_max:
            raise ConflictError(f"名簿は {roster_max} 人までです")
        entry = TournamentRosterEntry(
            id=uuid.uuid4(), tournament_id=t.id, registration_id=reg.id, team_id=team.id, player_id=player_id,
            membership_id=member.id, default_slot=default_slot, status="invited", invited_by_user_id=user.id,
            reason=(reason or None) if scope != "team" else None,
        )
        try:
            async with self._db.begin_nested():  # 違反のときは、この行だけを戻す
                self._db.add(entry)
        except IntegrityError:
            raise ConflictError("この選手は、この大会のどこかのチームの名簿に既に載っています（D10）") from None
        await _emit(self._db, Ev.TOURNAMENT_ROSTER_CHANGED, "tournament", t.id,
                    after={"entry_id": str(entry.id), "action": "invited", "scope": scope})
        if scope == "admin":
            await record_correction(self._db, kind="roster_change", reason=reason, actor=user, tournament_id=t.id,
                                    before={}, after={"entry_id": str(entry.id), "status": "invited"})
        await _notify(self._db, self._cache, await _user_id_of(self._db, player_id), "大会の名簿への参加の依頼",
                      f"{team.name} が {t.name} の名簿にあなたを載せました。参加を承認してください",
                      "/tournaments/roster-invitations", {"entry_id": str(entry.id), "tournament_id": str(t.id)})
        return entry

    async def update_entry(self, tournament_id, registration_id, entry_id, *, default_slot: str | None,
                           remove: bool, reason: str | None, user: User) -> TournamentRosterEntry:
        t, reg, team = await self._context(tournament_id, registration_id)
        require_roster_mode(t)
        scope = await self._scope(t, team, user, reason)
        entry = (await self._db.execute(select(TournamentRosterEntry).where(
            TournamentRosterEntry.id == entry_id, TournamentRosterEntry.registration_id == reg.id,
        ).with_for_update())).scalar_one_or_none()
        if entry is None:
            raise NotFoundError("名簿の行", str(entry_id))
        before = {"status": entry.status, "default_slot": entry.default_slot}
        if remove:
            if entry.status not in ACTIVE_ROSTER:
                raise ConflictError("既に名簿から外れています")
            entry.status, entry.removed_at, entry.removed_by_user_id = "removed", utcnow(), user.id
            entry.reason = (reason or None)
        elif default_slot:
            entry.default_slot = default_slot
        await self._db.flush()
        after = {"status": entry.status, "default_slot": entry.default_slot}
        await _emit(self._db, Ev.TOURNAMENT_ROSTER_CHANGED, "tournament", t.id,
                    after={"entry_id": str(entry.id), "before": before, "after": after, "scope": scope})
        if scope == "admin":
            await record_correction(self._db, kind="roster_change", reason=reason, actor=user, tournament_id=t.id,
                                    before=before, after=after)
        if remove:
            await _notify(self._db, self._cache, await _user_id_of(self._db, entry.player_id), "大会の名簿から外れました",
                          f"{t.name} の {team.name} の名簿から外されました", "/tournaments/roster-invitations",
                          {"entry_id": str(entry.id), "reason": reason})
        return entry

    async def my_invitations(self, user: User) -> list:
        player = await self._db.scalar(select(Player).where(Player.user_id == user.id))
        if player is None:
            return []
        return list((await self._db.execute(
            select(TournamentRosterEntry, Tournament, Team)
            .join(Tournament, Tournament.id == TournamentRosterEntry.tournament_id)
            .join(Team, Team.id == TournamentRosterEntry.team_id)
            .where(TournamentRosterEntry.player_id == player.id,
                   TournamentRosterEntry.status.in_(ACTIVE_ROSTER))
            .order_by(TournamentRosterEntry.invited_at.desc()))).all())

    async def respond(self, entry_id: uuid.UUID, action: str, user: User) -> TournamentRosterEntry:
        """本人だけ: accept・decline・withdraw（取り下げは固定の前だけ）。"""
        entry = (await self._db.execute(select(TournamentRosterEntry).where(
            TournamentRosterEntry.id == entry_id).with_for_update())).scalar_one_or_none()
        player = await self._db.scalar(select(Player).where(Player.user_id == user.id))
        if entry is None:
            raise NotFoundError("名簿の行", str(entry_id))
        if player is None or entry.player_id != player.id:
            raise ForbiddenError("名簿への参加に返事ができるのは本人だけです")
        t = await self._db.get(Tournament, entry.tournament_id)
        if t.status in CLOSED:
            raise ConflictError("完了・中止した大会の名簿には返事ができません")
        if action in ("accept", "decline"):
            if entry.status != "invited":
                raise ConflictError("返事待ちの名簿の行だけに返事ができます")
            if action == "accept":
                reg = await self._db.get(TournamentRegistration, entry.registration_id)
                member = await self._db.get(TeamMember, entry.membership_id)
                if reg is None or reg.status not in ROSTER_PREP_REGISTRATION:
                    raise ConflictError("この参加登録は辞退・却下されています")
                if member is None or member.left_at is not None or member.consent not in CONSENTED:
                    raise ConflictError("チームへの所属を承諾してから名簿への参加を承認してください")
            entry.status = "accepted" if action == "accept" else "declined"
        elif action == "withdraw":
            if entry.status != "accepted":
                raise ConflictError("承認した名簿の行だけを取り下げられます")
            if t.roster_locked_at is not None:
                raise ConflictError("名簿の固定の後は取り下げられません。主催者に連絡してください")
            entry.status = "withdrawn"
        else:
            raise BusinessRuleError("不明な操作です")
        entry.responded_at = utcnow()
        await self._db.flush()
        await _emit(self._db, Ev.TOURNAMENT_ROSTER_CHANGED, "tournament", t.id,
                    after={"entry_id": str(entry.id), "action": entry.status, "scope": "self"})
        await invalidate_player_caches(self._cache, [entry.player_id])
        return entry


# ── 出場登録 ─────────────────────────────────────────────────────────────

class LineupService:
    def __init__(self, db: AsyncSession, cache: RedisCache | None):
        self._db = db
        self._cache = cache

    async def active_entries(self, match_id, team_id=None) -> list[MatchLineupEntry]:
        q = select(MatchLineupEntry).where(MatchLineupEntry.match_id == match_id, MatchLineupEntry.removed_at.is_(None))
        if team_id:
            q = q.where(MatchLineupEntry.team_id == team_id)
        return list((await self._db.execute(q.order_by(MatchLineupEntry.added_at))).scalars())

    async def get_lineups(self, match: Match) -> dict:
        entries = await self.active_entries(match.id)
        timeline = await participation(self._db, match)
        names = dict((await self._db.execute(select(Player.id, Player.in_game_name).where(
            Player.id.in_({e.player_id for e in entries} or {uuid.uuid4()})))).all())
        by_game = defaultdict(dict)
        for (team_id, g), sets in timeline.items():
            by_game[g][str(team_id)] = sorted(str(eid) for eid in sets["participants"])
        return {
            "locked_at": match.lineup_locked_at,
            "entries": [{"id": e.id, "team_id": e.team_id, "player_id": e.player_id,
                         "in_game_name": names.get(e.player_id), "slot": e.slot, "source": e.source}
                        for e in entries],
            "participants_by_game": dict(by_game),
        }

    async def _accepted_roster(self, t: Tournament, team_id) -> list[TournamentRosterEntry]:
        return list((await self._db.execute(select(TournamentRosterEntry).where(
            TournamentRosterEntry.tournament_id == t.id, TournamentRosterEntry.team_id == team_id,
            TournamentRosterEntry.status == "accepted").order_by(TournamentRosterEntry.invited_at))).scalars())

    async def ensure_default(self, match: Match, t: Tournament, team_id) -> None:
        """出場登録の無いチームは、名簿の既定の役目から作る（設計の 4 章）。"""
        if await self.active_entries(match.id, team_id):
            return
        lineup_size, roster_max = require_limits(t)
        roster = await self._accepted_roster(t, team_id)
        starters = [r for r in roster if r.default_slot == "starter"][:lineup_size]
        bench = [r for r in roster if r not in starters][:max(roster_max - lineup_size, 0)]
        for r, slot in [(r, "starter") for r in starters] + [(r, "bench") for r in bench]:
            self._db.add(MatchLineupEntry(id=uuid.uuid4(), match_id=match.id, tournament_id=t.id, team_id=team_id,
                                          player_id=r.player_id, roster_entry_id=r.id, slot=slot, source="default"))
        await self._db.flush()

    async def put_lineup(self, match: Match, team_id, starters: list, bench: list, reason: str | None,
                         user: User) -> list[MatchLineupEntry]:
        """出場登録を置き換える。開始の前はチーム、固定の後は主催者（理由つき）、完了の後は管理者。"""
        t = await self._db.get(Tournament, match.tournament_id)
        require_roster_mode(t)
        if team_id not in (match.team1_id, match.team2_id):
            raise BusinessRuleError("この試合のチームではありません")
        admin_fix = closed_tournament_guard(t, user, reason)
        if admin_fix and match.lineup_locked_at is None:
            raise ConflictError("開始を経ずに決着した試合には、出場登録を作れません")
        if not admin_fix:
            if match.lineup_locked_at is None and match.status == MatchStatus.SCHEDULED:
                if not is_organizer(t, user):
                    await MembershipService(self._db, self._cache).require_team_manager(
                        await self._db.get(Team, team_id), user)
            elif match.lineup_locked_at is None:
                raise ConflictError("開始を経ずに決着した試合には、出場登録を作れません")
            else:
                if not is_organizer(t, user):
                    raise ConflictError("出場登録は固定されています。変更は大会の主催者に依頼してください")
                if not (reason or "").strip():
                    raise BusinessRuleError("固定の後の出場登録の変更には理由が必要です")
        lineup_size, roster_max = require_limits(t)
        if len(set(starters) | set(bench)) != len(starters) + len(bench):
            raise BusinessRuleError("同じ選手が重複しています")
        if len(starters) > lineup_size:
            raise BusinessRuleError(f"スターターは {lineup_size} 人までです")
        if len(bench) > max(roster_max - lineup_size, 0):
            raise BusinessRuleError(f"控えは {max(roster_max - lineup_size, 0)} 人までです")
        roster = {r.player_id: r for r in await self._accepted_roster(t, team_id)}
        wanted = {pid: "starter" for pid in starters} | {pid: "bench" for pid in bench}
        missing = [pid for pid in wanted if pid not in roster]
        if missing:
            raise BusinessRuleError("出場登録できるのは、本人が名簿への参加を承認した選手だけです")
        current = await self.active_entries(match.id, team_id)
        now = utcnow()
        source = "admin" if admin_fix else ("team" if match.lineup_locked_at is None and not is_organizer(t, user)
                                            else "organizer")
        removed = [e for e in current if wanted.get(e.player_id) != e.slot]
        if match.lineup_locked_at is not None and removed:
            with_stats = set((await self._db.execute(
                select(PlayerMatchStats.lineup_entry_id).join(MatchGame, MatchGame.id == PlayerMatchStats.match_game_id)
                .where(MatchGame.match_id == match.id,
                       PlayerMatchStats.lineup_entry_id.in_([e.id for e in removed])))).scalars())
            if with_stats:
                raise ConflictError("この試合の成績が残っている選手は出場登録から外せません。先に成績を直してください")
        for e in removed:
            e.removed_at, e.removed_by_user_id, e.reason = now, user.id, (reason or None)
        await self._db.flush()
        kept = {e.player_id for e in current if e not in removed}
        added = []
        for pid, slot in wanted.items():
            if pid in kept:
                continue
            e = MatchLineupEntry(id=uuid.uuid4(), match_id=match.id, tournament_id=t.id, team_id=team_id,
                                 player_id=pid, roster_entry_id=roster[pid].id, slot=slot, source=source,
                                 added_by_user_id=user.id, reason=(reason or None))
            self._db.add(e)
            added.append(e)
        await self._db.flush()
        errors = await approval_errors(self._db, added, require_active=True)
        if errors:
            raise ConflictError(next(iter(errors.values())))
        await _emit(self._db, Ev.MATCH_LINEUP_CHANGED, "match", match.id,
                    after={"team_id": str(team_id), "starters": len(starters), "bench": len(bench), "source": source})
        if admin_fix:
            await record_correction(self._db, kind="lineup_change", reason=reason, actor=user, tournament_id=t.id,
                                    match_id=match.id, before={"removed": [str(e.player_id) for e in removed]},
                                    after={"added": [str(e.player_id) for e in added]})
        await invalidate_player_caches(self._cache, [e.player_id for e in removed + added])
        return await self.active_entries(match.id, team_id)

    async def lock_for_start(self, match: Match, t: Tournament, reason: str | None, user: User) -> dict:
        """試合の開始で出場登録を固定する（Q04・Q06・Q17）。人数・承認を確かめる。"""
        lineup_size, _ = require_limits(t)
        await lock_roster(self._db, t)
        counts = {}
        for team_id in (match.team1_id, match.team2_id):
            await self.ensure_default(match, t, team_id)
            entries = await self.active_entries(match.id, team_id)
            errors = await approval_errors(self._db, entries, require_active=True)
            if errors:
                raise ConflictError(f"出場登録に承認の足りない選手がいます: {next(iter(errors.values()))}")
            counts[team_id] = sum(1 for e in entries if e.slot == "starter")
        if 0 in counts.values():
            raise ConflictError("スターターのいないチームがあります。開始せずに不戦勝として登録してください")
        short = {str(k): v for k, v in counts.items() if v < lineup_size}
        if short and not (reason or "").strip():
            raise BusinessRuleError(f"スターターが {lineup_size} 人に満たないチームがあります。開始するには理由を入力してください")
        match.lineup_locked_at = utcnow()
        await self._db.flush()
        await _emit(self._db, Ev.MATCH_LINEUP_CHANGED, "match", match.id,
                    after={"action": "locked", "starters": {str(k): v for k, v in counts.items()},
                           "short_reason": (reason or None) if short else None})
        # D22: 本人への通知は試合ごとに 1 件（出場登録の固定の時）
        for e in await self.active_entries(match.id):
            await _notify(self._db, self._cache, await _user_id_of(self._db, e.player_id), "試合の出場登録",
                          f"{t.name} の試合の出場登録に載りました。出場していない場合は試合のページから異議を出せます",
                          f"/matches/{match.id}", {"match_id": str(match.id), "lineup_entry_id": str(e.id)})
        return counts


# ── 交代（Q09・Q10）────────────────────────────────────────────────────────

class SubstitutionService:
    def __init__(self, db: AsyncSession, cache: RedisCache | None):
        self._db = db
        self._cache = cache

    async def _entry(self, match: Match, team_id, player_id) -> MatchLineupEntry:
        e = await self._db.scalar(select(MatchLineupEntry).where(
            MatchLineupEntry.match_id == match.id, MatchLineupEntry.team_id == team_id,
            MatchLineupEntry.player_id == player_id, MatchLineupEntry.removed_at.is_(None)))
        if e is None:
            raise BusinessRuleError("交代できるのは、この試合の出場登録の選手だけです")
        return e

    async def _validate(self, match: Match, t: Tournament, sub: MatchSubstitution) -> None:
        lineup_size, _ = require_limits(t)
        timeline = await participation(self._db, match, upto_game=sub.game_number, exclude_sub=sub.id)
        cur = timeline.get((sub.team_id, sub.game_number), {"start": set(), "participants": set(), "end": set()})
        if sub.kind == "mid_map":
            playing = cur["end"]
            if sub.out_lineup_entry_id not in playing:
                raise BusinessRuleError("抜ける選手が、そのマップで出場中ではありません")
            if sub.in_lineup_entry_id in cur["participants"]:
                raise BusinessRuleError("入る選手は、そのマップに既に出場しています")
        else:
            start = cur["start"]
            if sub.in_lineup_entry_id in start:
                raise BusinessRuleError("入る選手は、そのマップの開始で既に出場中です")
            if sub.kind == "between_maps" and sub.out_lineup_entry_id not in start:
                raise BusinessRuleError("抜ける選手が、そのマップの開始で出場中ではありません")
            if sub.kind == "fill" and len(start) >= lineup_size:
                raise BusinessRuleError("補充は、出場中の人数が出場人数に満たないときだけです")
        if sub.kind != "mid_map" and await self._db.scalar(select(MatchGame.id).join(
                PlayerMatchStats, PlayerMatchStats.match_game_id == MatchGame.id).where(
                MatchGame.match_id == match.id, MatchGame.game_number == sub.game_number).limit(1)):
            raise ConflictError("成績を登録したマップには、マップの間の交代・補充を足せません")
        errors = await approval_errors(self._db, [await self._db.get(MatchLineupEntry, sub.in_lineup_entry_id)],
                                       require_active=True)
        if errors:
            raise ConflictError(next(iter(errors.values())))

    async def submit(self, match: Match, *, game_number: int, team_id, kind: str, out_player_id,
                     in_player_id, at_round: int | None, reason: str | None, user: User) -> MatchSubstitution:
        t = await self._db.get(Tournament, match.tournament_id)
        require_roster_mode(t)
        if match.lineup_locked_at is None or match.status not in (MatchStatus.ONGOING, MatchStatus.COMPLETED):
            raise ConflictError("交代を記録できるのは、開始した試合だけです")
        if kind not in ("between_maps", "mid_map", "fill"):
            raise BusinessRuleError("交代の種類が不正です")
        if (kind == "fill") != (out_player_id is None):
            raise BusinessRuleError("補充は抜ける選手を指定せず、交代は抜ける選手を指定してください")
        if kind == "mid_map" and not (reason or "").strip():
            raise BusinessRuleError("マップの途中の交代には理由が必要です")
        admin_fix = closed_tournament_guard(t, user, reason)
        direct = admin_fix or is_organizer(t, user)
        if not direct:
            if match.status != MatchStatus.ONGOING:
                raise ConflictError("完了した試合の交代は、主催者が記録してください")
            await MembershipService(self._db, self._cache).require_team_manager(await self._db.get(Team, team_id), user)
        elif not (reason or "").strip():
            raise BusinessRuleError("主催者・管理者が交代を記録するときは理由が必要です")
        sub = MatchSubstitution(
            id=uuid.uuid4(), match_id=match.id, game_number=game_number, team_id=team_id, kind=kind,
            out_lineup_entry_id=(await self._entry(match, team_id, out_player_id)).id if out_player_id else None,
            in_lineup_entry_id=(await self._entry(match, team_id, in_player_id)).id,
            at_round=at_round, reason=(reason or None), status="requested", requested_by_user_id=user.id,
        )
        if direct:
            await self._validate(match, t, sub)
            sub.status, sub.approved_by_user_id, sub.approved_at = "approved", user.id, utcnow()
        self._db.add(sub)
        await self._db.flush()
        await _emit(self._db, Ev.MATCH_SUBSTITUTION_REQUESTED if not direct else Ev.MATCH_SUBSTITUTION_DECIDED,
                    "match", match.id, after={"substitution_id": str(sub.id), "kind": kind, "status": sub.status})
        if admin_fix:
            await record_correction(self._db, kind="substitution_change", reason=reason, actor=user,
                                    tournament_id=t.id, match_id=match.id, before={},
                                    after={"substitution_id": str(sub.id), "status": sub.status})
        return sub

    async def decide(self, match: Match, sub_id, approve: bool, user: User) -> MatchSubstitution:
        t = await self._db.get(Tournament, match.tournament_id)
        if not is_organizer(t, user):
            raise ForbiddenError("交代を承認・却下できるのは大会の主催者と管理者だけです")
        if t.status in CLOSED:
            raise ConflictError("完了・中止した大会の交代は、管理者の記録で行ってください")
        sub = (await self._db.execute(select(MatchSubstitution).where(
            MatchSubstitution.id == sub_id, MatchSubstitution.match_id == match.id).with_for_update())).scalar_one_or_none()
        if sub is None:
            raise NotFoundError("交代", str(sub_id))
        if sub.status != "requested":
            raise ConflictError("申請中の交代だけを承認・却下できます")
        if approve:
            await self._validate(match, t, sub)
        sub.status = "approved" if approve else "rejected"
        sub.approved_by_user_id, sub.approved_at = user.id, utcnow()
        await self._db.flush()
        await _emit(self._db, Ev.MATCH_SUBSTITUTION_DECIDED, "match", match.id,
                    after={"substitution_id": str(sub.id), "status": sub.status})
        return sub


# ── 出場の異議（C5）────────────────────────────────────────────────────────

class DisputeService:
    def __init__(self, db: AsyncSession, cache: RedisCache | None):
        self._db = db
        self._cache = cache

    async def create(self, match_id: uuid.UUID, reason: str, user: User) -> ParticipationDispute:
        player = await self._db.scalar(select(Player).where(Player.user_id == user.id))
        if player is None:
            raise ForbiddenError("異議を出せるのは、出場登録・成績に載った本人だけです")
        on_record = await self._db.scalar(select(MatchLineupEntry.id).where(
            MatchLineupEntry.match_id == match_id, MatchLineupEntry.player_id == player.id,
            MatchLineupEntry.removed_at.is_(None)).limit(1))
        if on_record is None:
            on_record = await self._db.scalar(select(PlayerMatchStats.id).join(
                MatchGame, MatchGame.id == PlayerMatchStats.match_game_id).where(
                MatchGame.match_id == match_id, PlayerMatchStats.player_id == player.id).limit(1))
        if on_record is None:
            raise ForbiddenError("異議を出せるのは、出場登録・成績に載った本人だけです")
        d = ParticipationDispute(id=uuid.uuid4(), match_id=match_id, player_id=player.id, reason=reason.strip())
        try:
            async with self._db.begin_nested():  # 違反のときは、この行だけを戻す
                self._db.add(d)
        except IntegrityError:
            raise ConflictError("この試合には、裁定待ちの異議が既にあります") from None
        await _emit(self._db, Ev.MATCH_PARTICIPATION_DISPUTED, "match", match_id, after={"dispute_id": str(d.id)})
        return d

    async def list(self, status: str | None, user: User) -> list[ParticipationDispute]:
        if user.role != UserRole.ADMIN:
            raise ForbiddenError("異議の一覧は管理者だけが見られます")
        q = select(ParticipationDispute).order_by(ParticipationDispute.created_at.desc()).limit(200)
        if status:
            q = q.where(ParticipationDispute.status == status)
        return list((await self._db.execute(q)).scalars())

    async def resolve(self, dispute_id: uuid.UUID, status: str, note: str | None, user: User) -> ParticipationDispute:
        if user.role != UserRole.ADMIN:
            raise ForbiddenError("異議を裁定できるのは管理者だけです")
        if status not in ("upheld", "dismissed"):
            raise BusinessRuleError("裁定は upheld か dismissed です")
        d = (await self._db.execute(select(ParticipationDispute).where(
            ParticipationDispute.id == dispute_id).with_for_update())).scalar_one_or_none()
        if d is None:
            raise NotFoundError("異議", str(dispute_id))
        if d.status != "open":
            raise ConflictError("裁定待ちの異議だけを裁定できます")
        d.status, d.resolved_at, d.resolved_by_user_id, d.resolution_note = status, utcnow(), user.id, note
        await self._db.flush()
        await _emit(self._db, Ev.MATCH_DISPUTE_RESOLVED, "match", d.match_id,
                    after={"dispute_id": str(d.id), "status": status})
        await invalidate_player_caches(self._cache, [d.player_id])
        await _notify(self._db, self._cache, await _user_id_of(self._db, d.player_id), "出場の異議の裁定",
                      "異議を認めました" if status == "upheld" else "異議を退けました",
                      f"/matches/{d.match_id}", {"dispute_id": str(d.id), "status": status})
        return d


async def is_bye(db: AsyncSession, match: Match) -> bool:
    """バイ: 完了・結果の行が無い・相手のいない試合（Q18）。"""
    if match.status != MatchStatus.COMPLETED or (match.team1_id and match.team2_id):
        return False
    return not await db.scalar(select(MatchResult.id).where(MatchResult.match_id == match.id))
