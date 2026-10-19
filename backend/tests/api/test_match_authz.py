"""MATCH-AUTHZ — 試合操作の認可テスト。

P0-2（Ban/Pick）と P0-1（試合進行・結果登録の主催者間認可）の両方を扱う。

P0-1 の方針:
  試合を変える4操作と、処理の重いスコアボード取り込みは、ADMIN か
  その試合が属する大会の主催者だけが通る。ロールが organizer でも、
  他人の大会の試合には触れない。

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
from app.models.domain_event import DomainEvent
from app.models.match import (
    BanPick,
    Map,
    Match,
    MatchGame,
    MatchResult,
    PlayerMatchStats,
)
from app.services.match import MatchService
from app.services.scoreboard_import import ScoreboardImportService
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


# ══ P0-1: 試合進行・結果登録の主催者間認可 ══════════════════════════════════

P_START = "/api/v1/matches/{id}/start"
P_SCORE = "/api/v1/matches/{id}/games/1/score"
P_STATS = "/api/v1/matches/{id}/games/1/player-stats"
P_RESULT = "/api/v1/matches/{id}/result"
P_OCR = "/api/v1/matches/{id}/scoreboard-ocr"
P_STREAM = "/api/v1/matches/{id}/stream"

# 操作名 → その操作が許される試合ステータス
_OPS = {
    "start": MatchStatus.SCHEDULED,
    "score": MatchStatus.ONGOING,
    "stats": MatchStatus.ONGOING,
    "result": MatchStatus.ONGOING,
}


def _stats_body(w, *, player=None, team=None, kills=20) -> dict:
    rows = []
    if player is not None:
        rows = [{
            "player_id": str(player.id),
            "team_id": str((team or w["team1"]).id),
            "kills": kills, "deaths": 10, "assists": 5, "score": 300, "first_bloods": 3,
        }]
    return {
        "map_id": str(w["map"].id), "team1_score": 13, "team2_score": 7,
        "player_stats": rows,
    }


async def _call(client, op, match_id, headers, w):
    """4操作のいずれかを HTTP で叩く。"""
    url = {"start": P_START, "score": P_SCORE, "stats": P_STATS, "result": P_RESULT}[op]
    url = url.format(id=match_id)
    if op == "start":
        return await client.patch(url, headers=headers)
    body = {
        "score": {"team1_score": 13, "team2_score": 7},
        "stats": _stats_body(w),
        "result": {"winner_id": str(w["team1"].id)},
    }[op]
    return await client.post(url, json=body, headers=headers)


async def _counts(db) -> dict:
    """結果登録が触りうるテーブルの件数。副作用の有無を測る。"""
    async def n(model):
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()

    return {
        "results": await n(MatchResult),
        "games": await n(MatchGame),
        "player_stats": await n(PlayerMatchStats),
        "events": await n(DomainEvent),
    }


async def _stat_kills(db, match) -> list[int]:
    return list((await db.execute(
        select(PlayerMatchStats.kills)
        .join(MatchGame, MatchGame.id == PlayerMatchStats.match_game_id)
        .where(MatchGame.match_id == match.id)
        .order_by(PlayerMatchStats.kills)
    )).scalars().all())


# ── 許可されるケース ─────────────────────────────────────────────────────────


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("op", list(_OPS))
async def test_p01_001_organizer_allowed_on_own_match(client: AsyncClient, db, op):
    w = await _world(db, status=_OPS[op])
    r = await _call(client, op, w["match"].id, _headers(w["organizer"]), w)
    assert r.status_code == 204, r.text


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("op", list(_OPS))
async def test_p01_002_admin_allowed_on_other_match(client: AsyncClient, db, admin_user, op):
    w = await _world(db, status=_OPS[op])
    r = await _call(client, op, w["match"].id, _headers(admin_user), w)
    assert r.status_code == 204, r.text


# ── 拒否されるケース ─────────────────────────────────────────────────────────


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("op", list(_OPS))
async def test_p01_003_other_organizer_denied(client: AsyncClient, db, op):
    """P0-1 の本体。別の大会の主催者は他人の試合に触れない。"""
    w = await _world(db, status=_OPS[op])
    other = await f.make_user(db, role=UserRole.ORGANIZER)
    r = await _call(client, op, w["match"].id, _headers(other), w)
    assert r.status_code == 403, r.text


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("op", list(_OPS))
@pytest.mark.parametrize("role", [UserRole.PLAYER, UserRole.TEAM_MANAGER])
async def test_p01_004_non_organizer_roles_denied(client: AsyncClient, db, op, role):
    w = await _world(db, status=_OPS[op])
    user = await f.make_user(db, role=role)
    r = await _call(client, op, w["match"].id, _headers(user), w)
    assert r.status_code == 403, r.text


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("op", list(_OPS))
async def test_p01_005_anonymous_denied(client: AsyncClient, db, op):
    w = await _world(db, status=_OPS[op])
    r = await _call(client, op, w["match"].id, {}, w)
    assert r.status_code == 401, r.text


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("op", list(_OPS))
async def test_p01_006_unknown_match_is_404(client: AsyncClient, db, op):
    """権限のある主催者でも、存在しない試合は 404。"""
    w = await _world(db, status=_OPS[op])
    r = await _call(client, op, uuid.uuid4(), _headers(w["organizer"]), w)
    assert r.status_code == 404, r.text


# ── 副作用が出ないことの確認 ─────────────────────────────────────────────────


@pytest.mark.security
@pytest.mark.asyncio
async def test_p01_007_denied_result_has_no_side_effects(client: AsyncClient, db):
    w = await _world(db, status=MatchStatus.ONGOING)
    nxt = Match(
        tournament_id=w["tour"].id, format=BOFormat.BO1,
        status=MatchStatus.SCHEDULED, round_number=2, match_number=1,
    )
    db.add(nxt)
    await db.flush()
    w["match"].next_match_id = nxt.id
    await db.flush()

    before = await _counts(db)
    other = await f.make_user(db, role=UserRole.ORGANIZER)
    r = await client.post(
        P_RESULT.format(id=w["match"].id),
        json={"winner_id": str(w["team1"].id)}, headers=_headers(other),
    )
    assert r.status_code == 403, r.text

    assert await _counts(db) == before
    await db.refresh(w["match"])
    await db.refresh(nxt)
    assert w["match"].status == MatchStatus.ONGOING
    assert w["match"].winner_id is None
    assert (nxt.team1_id, nxt.team2_id) == (None, None)


@pytest.mark.security
@pytest.mark.asyncio
async def test_p01_008_denied_result_never_enters_service(
    client: AsyncClient, db, monkeypatch
):
    """認可はサービス層より前に落ちる。ロックも結果処理も始まらない。"""
    w = await _world(db, status=MatchStatus.ONGOING)
    reached = []

    async def _boom(self, *args, **kwargs):
        reached.append(1)

    monkeypatch.setattr(MatchService, "register_result", _boom)

    other = await f.make_user(db, role=UserRole.ORGANIZER)
    r = await client.post(
        P_RESULT.format(id=w["match"].id),
        json={"winner_id": str(w["team1"].id)}, headers=_headers(other),
    )
    assert r.status_code == 403, r.text
    assert reached == []


@pytest.mark.security
@pytest.mark.asyncio
async def test_p01_009_denied_stats_keeps_existing_rows(client: AsyncClient, db):
    """成績は毎回置き換える実装なので、拒否で既存が消えないことを確かめる。"""
    w = await _world(db, status=MatchStatus.ONGOING)
    user = await f.make_user(db, role=UserRole.PLAYER)
    player = await f.make_player(db, user=user)
    await f.add_member(db, team=w["team1"], player=player)

    ok = await client.post(
        P_STATS.format(id=w["match"].id),
        json=_stats_body(w, player=player, kills=20), headers=_headers(w["organizer"]),
    )
    assert ok.status_code == 204, ok.text
    assert await _stat_kills(db, w["match"]) == [20]

    other = await f.make_user(db, role=UserRole.ORGANIZER)
    bad = await client.post(
        P_STATS.format(id=w["match"].id),
        json=_stats_body(w), headers=_headers(other),
    )
    assert bad.status_code == 403, bad.text
    assert await _stat_kills(db, w["match"]) == [20]


# ── スコアボード取り込み（処理が重い経路） ───────────────────────────────────


@pytest.mark.security
@pytest.mark.asyncio
async def test_p01_010_denied_ocr_never_reaches_parser(
    client: AsyncClient, db, monkeypatch
):
    w = await _world(db, status=MatchStatus.ONGOING)
    reached = []

    async def _spy(self, *args, **kwargs):
        reached.append(1)
        return []

    monkeypatch.setattr(ScoreboardImportService, "parse", _spy)

    other = await f.make_user(db, role=UserRole.ORGANIZER)
    r = await client.post(
        P_OCR.format(id=w["match"].id),
        files={"file": ("shot.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        headers=_headers(other),
    )
    assert r.status_code == 403, r.text
    assert reached == []


# ── 既存の配信URL認可が壊れていないこと ──────────────────────────────────────


@pytest.mark.security
@pytest.mark.asyncio
async def test_p01_011_stream_url_authz_unchanged(client: AsyncClient, db):
    """set_stream_url は今回触っていない。従来どおり本人のみ通る。"""
    w = await _world(db)
    body = {"stream_url": "https://twitch.tv/axelia"}

    ok = await client.patch(
        P_STREAM.format(id=w["match"].id), json=body, headers=_headers(w["organizer"]),
    )
    assert ok.status_code == 200, ok.text

    other = await f.make_user(db, role=UserRole.ORGANIZER)
    ng = await client.patch(
        P_STREAM.format(id=w["match"].id), json=body, headers=_headers(other),
    )
    assert ng.status_code == 403, ng.text


# ── route の付け忘れ検査 ─────────────────────────────────────────────────────

# matches.py の非GET route は原則 _require_match_organizer を通す。
# 例外は2つだけで、どちらもサービス層に専用の認可を持っている。
_AUTHZ_EXEMPT = {
    # Ban/Pick は運営だけでなくチーム側（オーナー・現役キャプテン）も登録するため、
    # MatchService._require_ban_pick_authority が判定する（P0-2）。
    "register_ban_pick",
    # 配信URLは MatchService.set_stream_url が自前で主催者本人を確認する。
    "set_stream_url",
}


def _dependency_calls(dependant) -> set:
    found = set()
    for sub in dependant.dependencies:
        found.add(sub.call)
        found |= _dependency_calls(sub)
    return found


@pytest.mark.security
def test_p01_012_mutation_routes_require_match_organizer():
    """新しい mutation route が認可なしで足されたら、ここで落ちる。

    限界: この検査は matches.py の route だけを見る。将来、別の router から
    MatchService の mutation メソッドを直接呼ぶ実装までは防げない。この残余
    リスクは Design E として受容している。
    """
    from fastapi.routing import APIRoute

    from app.api.v1.matches import _require_match_organizer, router

    unguarded = []
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not (route.methods - {"GET", "HEAD", "OPTIONS"}):
            continue
        if route.name in _AUTHZ_EXEMPT:
            continue
        if _require_match_organizer not in _dependency_calls(route.dependant):
            unguarded.append(route.name)

    assert unguarded == [], f"認可 Dependency のない mutation route: {unguarded}"
