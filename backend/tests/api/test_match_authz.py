"""MATCH-AUTHZ — 試合操作の認可テスト。

今回の対象は P0-2（Ban/Pick）だけ。試合結果の登録・進行（P0-1）はまだ
ロールだけで通るため、ここでは検証しない。

Ban/Pick の方針:
  運営（ADMIN・大会の主催者）は両チームぶんを登録できる。
  チーム側はオーナーか現役キャプテンだけで、自分のチームぶんに限る。
  出場していないチームのIDは、権限の話より前に弾く（400）。
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models.enums import (
    BanPickAction,
    BOFormat,
    GameType,
    MatchStatus,
    MemberRole,
    TournamentStatus,
    UserRole,
)
from app.models.match import BanPick, Map, Match
from tests import factories as f

PATH = "/api/v1/matches/{match_id}/banpick"


def _headers(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id), {'role': user.role.value})}"}


async def _make_map(db) -> Map:
    m = Map(
        game=GameType.VALORANT,
        internal_name=f"map_{uuid.uuid4().hex[:8]}",
        display_name="Test Map",
        is_active=True,
    )
    db.add(m)
    await db.flush()
    return m


async def _make_match(db, *, tournament, team1, team2, status=MatchStatus.SCHEDULED) -> Match:
    m = Match(
        tournament_id=tournament.id,
        team1_id=team1.id,
        team2_id=team2.id,
        format=BOFormat.BO1,
        status=status,
        round_number=1,
        match_number=1,
    )
    db.add(m)
    await db.flush()
    return m


async def _member(db, *, team, role, left_at=None):
    """チームに所属するユーザーを1人作って返す。"""
    user = await f.make_user(db, role=UserRole.PLAYER)
    player = await f.make_player(db, user=user)
    member = await f.add_member(db, team=team, player=player, role=role)
    if left_at is not None:
        member.left_at = left_at
        await db.flush()
    return user


async def _world(db, *, status=MatchStatus.SCHEDULED):
    """主催者・両チーム・試合・マップを用意する。"""
    organizer = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=organizer, status=TournamentStatus.ONGOING)
    owner1 = await f.make_user(db, role=UserRole.PLAYER)
    owner2 = await f.make_user(db, role=UserRole.PLAYER)
    team1 = await f.make_team(db, owner=owner1, tag="T1")
    team2 = await f.make_team(db, owner=owner2, tag="T2")
    await f.register_team(db, tournament=tour, team=team1)
    await f.register_team(db, tournament=tour, team=team2)
    match = await _make_match(db, tournament=tour, team1=team1, team2=team2, status=status)
    map_ = await _make_map(db)
    return {
        "organizer": organizer, "tour": tour, "team1": team1, "team2": team2,
        "owner1": owner1, "owner2": owner2, "match": match, "map": map_,
    }


def _body(w, *, team, order=1) -> dict:
    return {
        "team_id": str(team.id),
        "action": BanPickAction.BAN.value,
        "map_id": str(w["map"].id),
        "order": order,
    }


async def _ban_pick_count(db, match) -> int:
    return (
        await db.execute(select(func.count(BanPick.id)).where(BanPick.match_id == match.id))
    ).scalar_one()


# ── 許可されるケース ─────────────────────────────────────────────────────────


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_001_admin_allowed(client: AsyncClient, db, admin_user):
    w = await _world(db)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(admin_user),
    )
    assert r.status_code == 204
    assert await _ban_pick_count(db, w["match"]) == 1


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_002_organizer_allowed_for_both_teams(client: AsyncClient, db):
    w = await _world(db)
    for i, team in enumerate((w["team1"], w["team2"]), start=1):
        r = await client.post(
            PATH.format(match_id=w["match"].id), json=_body(w, team=team, order=i),
            headers=_headers(w["organizer"]),
        )
        assert r.status_code == 204, team.tag
    assert await _ban_pick_count(db, w["match"]) == 2


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_003_team_owner_allowed_for_own_team(client: AsyncClient, db):
    w = await _world(db)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(w["owner1"]),
    )
    assert r.status_code == 204
    assert await _ban_pick_count(db, w["match"]) == 1


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_004_active_captain_allowed_for_own_team(client: AsyncClient, db):
    w = await _world(db)
    captain = await _member(db, team=w["team1"], role=MemberRole.CAPTAIN)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(captain),
    )
    assert r.status_code == 204
    assert await _ban_pick_count(db, w["match"]) == 1


# ── 拒否されるケース（403） ──────────────────────────────────────────────────


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_005_owner_cannot_touch_opponent_team(client: AsyncClient, db):
    """自分のチームではない側のBan/Pickは入れられない。"""
    w = await _world(db)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team2"]),
        headers=_headers(w["owner1"]),
    )
    assert r.status_code == 403
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_006_captain_cannot_touch_opponent_team(client: AsyncClient, db):
    w = await _world(db)
    captain = await _member(db, team=w["team1"], role=MemberRole.CAPTAIN)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team2"]),
        headers=_headers(captain),
    )
    assert r.status_code == 403
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [MemberRole.PLAYER, MemberRole.SUBSTITUTE, MemberRole.COACH, MemberRole.ANALYST],
)
async def test_p02_007_non_captain_members_denied(client: AsyncClient, db, role):
    """一般プレイヤー・控え・コーチ・アナリストは入れられない。"""
    w = await _world(db)
    member = await _member(db, team=w["team1"], role=role)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(member),
    )
    assert r.status_code == 403, role
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_008_retired_captain_denied(client: AsyncClient, db):
    """退任済み（left_at あり）のキャプテンは入れられない。"""
    from datetime import datetime, timezone

    w = await _world(db)
    retired = await _member(
        db, team=w["team1"], role=MemberRole.CAPTAIN,
        left_at=datetime.now(timezone.utc),
    )
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(retired),
    )
    assert r.status_code == 403
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_009_viewer_denied(client: AsyncClient, db):
    """ログインしているだけのユーザーは入れられない。

    チームにも大会にも紐づいていないアカウントを使う。ロールは
    TEAM_MANAGER にした。名前はチームを扱えそうに見えるが、この試合の
    どちらのチームとも関係が無いので通ってはいけない、という確認になる。

    UserRole.VIEWER は使えない。Python の enum には後方互換で残っているが、
    DB の user_role は 001 で admin / organizer / team_manager / player の
    4つとして作られており、viewer を INSERT すると PostgreSQL が弾く。
    """
    w = await _world(db)
    viewer = await f.make_user(db, role=UserRole.TEAM_MANAGER)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(viewer),
    )
    assert r.status_code == 403
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_010_unrelated_organizer_denied(client: AsyncClient, db):
    """別の大会の主催者は、この試合のBan/Pickを入れられない。

    大会単位のスタッフ（P0-1 で追加予定）も Ban/Pick の権限範囲外なので、
    認可ヘルパーがスタッフを参照しない現在の実装では同じく 403 になる。
    """
    w = await _world(db)
    other = await f.make_user(db, role=UserRole.ORGANIZER)
    await f.make_tournament(db, organizer=other, status=TournamentStatus.ONGOING)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(other),
    )
    assert r.status_code == 403
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_011_unrelated_team_owner_denied(client: AsyncClient, db):
    """この試合に出ていないチームのオーナーは、出場チームぶんも入れられない。"""
    w = await _world(db)
    outsider = await f.make_user(db, role=UserRole.PLAYER)
    await f.make_team(db, owner=outsider, tag="OUT")
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(outsider),
    )
    assert r.status_code == 403
    assert await _ban_pick_count(db, w["match"]) == 0


# ── 業務ルール違反（400）・存在しない（404）・未認証（401） ──────────────────


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_012_team_not_in_match_is_400(client: AsyncClient, db):
    """出場していないチームのIDは、権限判定より前に 400 で弾く。"""
    w = await _world(db)
    outsider = await f.make_user(db, role=UserRole.PLAYER)
    outside_team = await f.make_team(db, owner=outsider, tag="OUT")
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=outside_team),
        headers=_headers(w["organizer"]),
    )
    assert r.status_code == 400
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_013_outside_team_owner_gets_400_not_403(client: AsyncClient, db):
    """自分のチームが出場していない場合、順序どおり 400 が先に出る。"""
    w = await _world(db)
    outsider = await f.make_user(db, role=UserRole.PLAYER)
    outside_team = await f.make_team(db, owner=outsider, tag="OUT")
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=outside_team),
        headers=_headers(outsider),
    )
    assert r.status_code == 400
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_014_match_not_found_is_404(client: AsyncClient, db):
    w = await _world(db)
    r = await client.post(
        PATH.format(match_id=uuid.uuid4()), json=_body(w, team=w["team1"]),
        headers=_headers(w["organizer"]),
    )
    assert r.status_code == 404


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_015_completed_match_is_400(client: AsyncClient, db):
    """既存のステータス制約は維持する。"""
    w = await _world(db, status=MatchStatus.COMPLETED)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(w["organizer"]),
    )
    assert r.status_code == 400
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_016_unauthenticated_is_401(client: AsyncClient, db):
    w = await _world(db)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
    )
    assert r.status_code == 401
    assert await _ban_pick_count(db, w["match"]) == 0


@pytest.mark.security
@pytest.mark.asyncio
async def test_p02_017_ongoing_match_allowed(client: AsyncClient, db):
    """ONGOING でも登録できる（既存仕様）。"""
    w = await _world(db, status=MatchStatus.ONGOING)
    r = await client.post(
        PATH.format(match_id=w["match"].id), json=_body(w, team=w["team1"]),
        headers=_headers(w["organizer"]),
    )
    assert r.status_code == 204
    assert await _ban_pick_count(db, w["match"]) == 1
