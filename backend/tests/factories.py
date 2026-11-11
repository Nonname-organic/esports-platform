"""非同期テストファクトリ（最少必須 + override）。

factory-boy の SQLAlchemyModelFactory は同期前提のため、async セッション向けに
薄いビルダー関数で提供する。各関数は db.add + flush して実体を返す（決定論的に上書き可）。
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.enums import (
    GameType,
    MemberRole,
    RegistrationStatus,
    TournamentFormat,
    TournamentStatus,
    UserRole,
)
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.models.tournament import Tournament, TournamentRegistration
from app.models.user import User

_now = lambda: datetime.now(timezone.utc)  # noqa: E731
_D = timedelta(days=1)


async def make_user(db: AsyncSession, *, email=None, username=None, role=UserRole.PLAYER,
                    password="Passw0rd!", **kw) -> User:
    uid = uuid.uuid4()
    user = User(
        id=uid, email=email or f"u-{uid.hex[:8]}@test.com",
        username=username or f"user_{uid.hex[:6]}",
        hashed_password=hash_password(password), role=role, is_active=True, **kw,
    )
    db.add(user)
    await db.flush()
    return user


async def make_player(db: AsyncSession, *, user=None, in_game_name="Tester",
                      game=GameType.VALORANT, **kw) -> Player:
    p = Player(
        user_id=user.id if user else None, in_game_name=in_game_name, game=game, **kw,
    )
    db.add(p)
    await db.flush()
    return p


async def make_team(db: AsyncSession, *, owner: User, name=None, tag="TST",
                    game=GameType.VALORANT, **kw) -> Team:
    name = name or f"Team {uuid.uuid4().hex[:5]}"
    t = Team(name=name, tag=tag, game=game, owner_id=owner.id, is_active=True, **kw)
    db.add(t)
    await db.flush()
    return t


async def add_member(db: AsyncSession, *, team: Team, player: Player,
                     role=MemberRole.PLAYER, consent="invitation") -> TeamMember:
    """RC4: 既定は本人が招待を承認した所属。移行前の所属は consent="unconfirmed" で作る。"""
    m = TeamMember(team_id=team.id, player_id=player.id, role=role, joined_at=_now(), consent=consent)
    db.add(m)
    await db.flush()
    return m


_STATUS_DATES = {
    # status: (reg_start, reg_end, start, end) offsets in days from now
    TournamentStatus.DRAFT: (None, None, None, None),
    TournamentStatus.REGISTRATION_OPEN: (-2, 5, 7, 8),
    TournamentStatus.REGISTRATION_CLOSED: (-10, -1, 3, 4),
    TournamentStatus.ONGOING: (-10, -3, -1, 2),
    TournamentStatus.COMPLETED: (-20, -15, -10, -5),
    TournamentStatus.CANCELLED: (-8, -2, 1, 2),
}


async def make_tournament(db: AsyncSession, *, organizer: User,
                          status=TournamentStatus.REGISTRATION_OPEN, name=None,
                          game=GameType.VALORANT, format=TournamentFormat.SINGLE_ELIMINATION,
                          max_teams=16, **kw) -> Tournament:
    name = name or f"Tournament {uuid.uuid4().hex[:5]}"
    rs, re_, st, en = _STATUS_DATES.get(status, (None, None, None, None))
    now = _now()
    t = Tournament(
        name=name, slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
        game=game, format=format, status=status, organizer_id=organizer.id,
        max_teams=max_teams, min_teams=2, is_public=True,
        registration_start_at=now + rs * _D if rs is not None else None,
        registration_end_at=now + re_ * _D if re_ is not None else None,
        start_at=now + st * _D if st is not None else None,
        end_at=now + en * _D if en is not None else None,
        **kw,
    )
    db.add(t)
    await db.flush()
    return t


async def register_team(db: AsyncSession, *, tournament: Tournament, team: Team,
                        status=RegistrationStatus.APPROVED) -> TournamentRegistration:
    now = _now()
    reg = TournamentRegistration(
        tournament_id=tournament.id, team_id=team.id, status=status,
        registered_at=now, updated_at=now,
    )
    db.add(reg)
    await db.flush()
    return reg


async def make_legacy_tournament(db: AsyncSession, **kw) -> Tournament:
    """032 より前からある旧方式（legacy）の大会。DB は新しい legacy の行を断る（Q02）ので、
    このトランザクションの中だけトリガーを止めて作る（テスト専用）。"""
    from sqlalchemy import text
    await db.execute(text("ALTER TABLE tournaments DISABLE TRIGGER trg_tournaments_roster_mode_guard"))
    t = await make_tournament(db, roster_mode="legacy", **kw)
    await db.execute(text("ALTER TABLE tournaments ENABLE TRIGGER trg_tournaments_roster_mode_guard"))
    return t


async def add_roster(db: AsyncSession, *, tournament: Tournament, team: Team, player: Player,
                     status="accepted", slot="starter"):
    """名簿の行（既定は本人が承認済み）。参加登録と、承諾済みの現役の所属が要る。"""
    from sqlalchemy import select
    from app.models.roster import TournamentRosterEntry
    reg = await db.scalar(select(TournamentRegistration).where(
        TournamentRegistration.tournament_id == tournament.id, TournamentRegistration.team_id == team.id))
    member = await db.scalar(select(TeamMember).where(
        TeamMember.team_id == team.id, TeamMember.player_id == player.id, TeamMember.left_at.is_(None)))
    assert reg is not None and member is not None, "参加登録と所属を先に作る"
    e = TournamentRosterEntry(id=uuid.uuid4(), tournament_id=tournament.id, registration_id=reg.id,
                              team_id=team.id, player_id=player.id, membership_id=member.id,
                              default_slot=slot, status=status)
    db.add(e)
    await db.flush()
    return e


async def roster_player(db: AsyncSession, *, tournament: Tournament, team: Team, name=None,
                        role=MemberRole.PLAYER, slot="starter", user=None) -> Player:
    """承諾済みの所属と、承認済みの名簿の行を持つ選手を 1 人作る。"""
    player = await make_player(db, user=user or await make_user(db), in_game_name=name or f"P-{uuid.uuid4().hex[:5]}")
    await add_member(db, team=team, player=player, role=role)
    await add_roster(db, tournament=tournament, team=team, player=player, slot=slot)
    return player


async def lock_lineup(db: AsyncSession, *, match, tournament: Tournament, team: Team, players: list,
                      slot="starter") -> list:
    """試合の出場登録を直接作り、固定済みにする（試合を ONGOING で直接作るテスト用）。

    選手には承認済みの名簿の行が要る（roster_player / add_roster）。
    """
    from sqlalchemy import select
    from app.models.roster import MatchLineupEntry, TournamentRosterEntry
    out = []
    for p in players:
        roster = await db.scalar(select(TournamentRosterEntry).where(
            TournamentRosterEntry.tournament_id == tournament.id, TournamentRosterEntry.player_id == p.id))
        e = MatchLineupEntry(id=uuid.uuid4(), match_id=match.id, tournament_id=tournament.id, team_id=team.id,
                             player_id=p.id, roster_entry_id=roster.id, slot=slot, source="default")
        db.add(e)
        out.append(e)
    match.lineup_locked_at = match.lineup_locked_at or _now()
    await db.flush()
    return out
