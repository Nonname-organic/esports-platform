"""公開の確認（scripts/rc4_release_check.py）: 旧方式の大会が始まっていれば失敗にする。"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import MatchStatus, TournamentStatus, UserRole
from app.models.match import Match
from scripts.rc4_release_check import parse_since, run_checks
from tests import factories as f


@pytest.mark.asyncio
async def test_旧方式の大会の試合が始まっていると失敗し_名簿の大会は数えない(db):
    since = datetime.now(timezone.utc) - timedelta(minutes=5)
    org = await f.make_user(db, role=UserRole.ORGANIZER)
    roster = await f.make_tournament(db, organizer=org, status=TournamentStatus.ONGOING)
    legacy = await f.make_legacy_tournament(db, organizer=org, status=TournamentStatus.REGISTRATION_CLOSED)
    legacy.created_at = since - timedelta(days=30)  # マイグレーションより前からある大会
    db.add(Match(tournament_id=roster.id, status=MatchStatus.ONGOING, started_at=datetime.now(timezone.utc)))
    await db.flush()

    values, problems = await run_checks(db, since)
    assert values["db_revision"] == "032" and problems == []
    assert values["legacy_tournaments_not_started"] == 1

    db.add(Match(tournament_id=legacy.id, status=MatchStatus.ONGOING, started_at=datetime.now(timezone.utc)))
    legacy.status = TournamentStatus.ONGOING
    await db.flush()
    _values, problems = await run_checks(db, since)
    assert problems == ["legacy_matches_started_since=1", "legacy_matches_ongoing=1", "legacy_tournaments_ongoing=1"]


def test_時刻はZつきでも受け取る():
    assert parse_since("2026-11-11T10:00:00Z") == datetime(2026, 11, 11, 10, tzinfo=timezone.utc)
    assert parse_since("2026-11-11T10:00:00").tzinfo == timezone.utc
