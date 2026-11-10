"""RC4 帰属の規則（S8-2・設計の 6 章）: 個人の RP・実績・大会履歴を 1 つの関数で決める。

- 名簿の大会（roster）: そのチームとして 1 マップ以上の実出場がある選手だけ（Q11。不戦勝・バイは帰属しない）
- 既存の大会（legacy）: 所属の期間が大会の期間と重なる選手。本人否認は数えない。本人未確認は
  移行期間中だけ数える（D4・D7）
- どちらも、異議が認められた試合の選手と、大会・選手ごとに 2 回目以降は数えない（D9）
- 同じ大会で 2 チームに当たるときは、区分の良い方 → 勝ち数 → 参加登録の早い方 → チームの ID（Q12）
- 保存しない。毎回 DB の状態だけから計算する（設計の 6.6）
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TournamentStatus
from app.models.match import Match, MatchGame
from app.models.roster import MatchLineupEntry, MatchSubstitution, ParticipationDispute
from app.models.team import TeamMember
from app.models.tournament import Tournament, TournamentRegistration
from app.repositories.tournament import publicly_listed
from app.seasons.utils import season_window as _season_window
from app.services.membership import CONSENTED, grace_deadline
from app.services.roster import compute_timeline

LABEL_ORDER = {"champion": 0, "runner_up": 1, "top4": 2, "participated": 3}
_FAR = datetime.max.replace(tzinfo=timezone.utc)

ReportFn = Callable[[uuid.UUID], Awaitable[Optional[dict]]]


def placements_of(data: dict) -> dict[str, str]:
    from app.rankings.aggregator import _placements
    return _placements(data)


async def _upheld(db: AsyncSession, match_ids: list) -> set[tuple]:
    if not match_ids:
        return set()
    rows = (await db.execute(select(ParticipationDispute.match_id, ParticipationDispute.player_id).where(
        ParticipationDispute.match_id.in_(match_ids), ParticipationDispute.status == "upheld"))).all()
    return {(m, p) for m, p in rows}


async def _roster_pairs(db: AsyncSession, tournament_id) -> set[tuple]:
    """{(player_id, team_id)}: そのチームとして 1 マップ以上の実出場がある選手。"""
    match_ids = list((await db.execute(select(Match.id).where(Match.tournament_id == tournament_id))).scalars())
    if not match_ids:
        return set()
    games = defaultdict(set)
    for mid, g in (await db.execute(select(MatchGame.match_id, MatchGame.game_number).where(
            MatchGame.match_id.in_(match_ids)))).all():
        games[mid].add(g)
    entries = defaultdict(list)
    for e in (await db.execute(select(MatchLineupEntry).where(
            MatchLineupEntry.match_id.in_(match_ids), MatchLineupEntry.removed_at.is_(None)))).scalars():
        entries[e.match_id].append(e)
    subs = defaultdict(list)
    for s in (await db.execute(select(MatchSubstitution).where(
            MatchSubstitution.match_id.in_(match_ids), MatchSubstitution.status == "approved",
    ).order_by(MatchSubstitution.game_number, MatchSubstitution.approved_at, MatchSubstitution.requested_at))).scalars():
        subs[s.match_id].append(s)
    upheld = await _upheld(db, match_ids)
    pairs = set()
    for mid, played in games.items():
        if not entries.get(mid):
            continue
        timeline = compute_timeline(entries[mid], subs.get(mid, []), max(played))
        by_id = {e.id: e for e in entries[mid]}
        for (team_id, g), sets in timeline.items():
            if g not in played:
                continue
            for eid in sets["participants"]:
                e = by_id.get(eid)
                if e is not None and (mid, e.player_id) not in upheld:
                    pairs.add((e.player_id, team_id))
    return pairs


async def _legacy_pairs(db: AsyncSession, t, team_ids: list, unconfirmed_counts: bool) -> set[tuple]:
    """{(player_id, team_id)}: 所属の期間が大会の期間と重なる選手（状態は設計の 6.4）。"""
    start, end = t.start_at, t.end_at
    if start is None or end is None:
        lo, hi = (await db.execute(select(func.min(Match.started_at), func.max(Match.ended_at)).where(
            Match.tournament_id == t.id))).one()
        start, end = start or lo, end or hi
    if start is None or end is None or not team_ids:
        return set()
    consents = CONSENTED + (("unconfirmed",) if unconfirmed_counts else ())
    rows = (await db.execute(select(TeamMember.player_id, TeamMember.team_id).where(
        TeamMember.team_id.in_(team_ids), TeamMember.consent.in_(consents),
        TeamMember.joined_at <= end, or_(TeamMember.left_at.is_(None), TeamMember.left_at >= start)))).all()
    match_ids = list((await db.execute(select(Match.id).where(Match.tournament_id == t.id))).scalars())
    upheld_players = {p for _m, p in await _upheld(db, match_ids)}
    return {(p, tm) for p, tm in rows if p not in upheld_players}


async def attribution_entries(db: AsyncSession, report_data: ReportFn, *, season: str = "all",
                              player_ids: Optional[set] = None) -> list[dict]:
    """[{player_id, tournament_id, tournament_name, game, team_id, label, team_count, ended_at}]"""
    start, end = _season_window(season)
    q = select(Tournament).where(Tournament.status == TournamentStatus.COMPLETED, publicly_listed())
    if start and end:
        q = q.where(Tournament.end_at >= start, Tournament.end_at < end)
    deadline = await grace_deadline(db)
    unconfirmed_counts = deadline is None or datetime.now(timezone.utc) < deadline
    wanted = {str(p) for p in player_ids} if player_ids else None
    out: list[dict] = []
    for t in (await db.execute(q)).scalars():
        data = await report_data(t.id)
        if not data:
            continue
        placements = placements_of(data)
        if not placements:
            continue
        wins = {s.get("team_id"): s.get("wins", 0) for s in data.get("standings") or []}
        team_ids = [uuid.UUID(tid) for tid in placements]
        if t.roster_mode == "roster":
            pairs = await _roster_pairs(db, t.id)
        else:
            pairs = await _legacy_pairs(db, t, team_ids, unconfirmed_counts)
        registered = dict((await db.execute(select(TournamentRegistration.team_id, TournamentRegistration.registered_at)
                                            .where(TournamentRegistration.tournament_id == t.id))).all())
        best: dict[str, tuple] = {}
        for player_id, team_id in pairs:
            pid, tid = str(player_id), str(team_id)
            label = placements.get(tid)
            if not label or (wanted is not None and pid not in wanted):
                continue
            key = (LABEL_ORDER.get(label, 9), -int(wins.get(tid, 0) or 0), registered.get(team_id) or _FAR, tid)
            if pid not in best or key < best[pid][0]:
                best[pid] = (key, tid, label)
        game = t.game.value if hasattr(t.game, "value") else str(t.game)
        for pid, (_key, tid, label) in best.items():
            out.append({"player_id": pid, "tournament_id": str(t.id), "tournament_name": t.name, "game": game,
                        "team_id": tid, "label": label, "team_count": len(placements), "ended_at": t.end_at})
    return out
