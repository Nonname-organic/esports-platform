"""DISCORD-SETUP-AUTHZ — 大会Discord紐付け（POST /discord/setup/{id}）の認可テスト。

P0-5 の方針:
  紐付けできるのは ADMIN か、その大会の主催者だけ。主催者ロールは本人が
  切り替えられるため、ロールが organizer でも他人の大会は紐付けられない。
  存在しない大会は 404。権限の確認は重複確認より前に行い、他人には
  紐付け済みかどうかも見せない（400 ではなく 403）。
  拒否したときは discord_servers に行を作らず、Bot への依頼も出さない。
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.discord import DiscordServer
from app.models.enums import UserRole
from app.services.discord_service import DiscordEventPublisher
from tests import factories as f

PATH = "/api/v1/discord/setup/{tournament_id}"
GUILD_ID = "123456789012345678"
FORBIDDEN_DETAIL = "この大会のDiscordを設定する権限がありません"


def _headers(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id), {'role': user.role.value})}"}


@pytest.fixture
def published(monkeypatch) -> list:
    """Bot への依頼を記録するだけにする（SQS・Redis へは送らない）。"""
    calls: list = []

    async def _record(self, event_type: str, payload: dict) -> None:
        calls.append((event_type, payload))

    monkeypatch.setattr(DiscordEventPublisher, "publish", _record)
    return calls


async def _post(client: AsyncClient, tournament_id, user, *, guild_id: str = GUILD_ID):
    return await client.post(
        PATH.format(tournament_id=tournament_id),
        json={"guild_id": guild_id},
        headers=_headers(user),
    )


async def _servers(db, tournament_id=None) -> list[DiscordServer]:
    q = select(DiscordServer)
    if tournament_id is not None:
        q = q.where(DiscordServer.tournament_id == tournament_id)
    return list((await db.execute(q)).scalars().all())


async def _bind(db, tournament, *, guild_id: str) -> DiscordServer:
    """紐付け済みの状態を直接作る（Bot への依頼は通さない）。"""
    server = DiscordServer(
        tournament_id=tournament.id, guild_id=guild_id, status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(server)
    await db.flush()
    return server


# ── 許可されるケース ─────────────────────────────────────────────────────────

@pytest.mark.security
@pytest.mark.asyncio
async def test_p05_001_owner_allowed(client: AsyncClient, db, published):
    """大会の主催者本人は紐付けでき、保存と Bot への依頼が1回ずつ行われる。"""
    owner = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=owner)

    r = await _post(client, tour.id, owner)

    assert r.status_code == 201
    data = r.json()["data"]
    assert data["tournament_id"] == str(tour.id)
    assert data["guild_id"] == GUILD_ID
    assert data["status"] == "pending"
    servers = await _servers(db, tour.id)
    assert len(servers) == 1
    assert str(servers[0].id) == data["id"]
    assert servers[0].guild_id == GUILD_ID
    assert servers[0].status == "pending"
    assert published == [("setup_tournament", {
        "tournament_id": str(tour.id),
        "guild_id": GUILD_ID,
        "discord_server_id": data["id"],
    })]


@pytest.mark.security
@pytest.mark.asyncio
async def test_p05_002_admin_allowed_for_others_tournament(client: AsyncClient, db, published):
    """ADMIN は他人の大会でも紐付けできる。"""
    owner = await f.make_user(db, role=UserRole.ORGANIZER)
    admin = await f.make_user(db, role=UserRole.ADMIN)
    tour = await f.make_tournament(db, organizer=owner)

    r = await _post(client, tour.id, admin)

    assert r.status_code == 201
    servers = await _servers(db, tour.id)
    assert len(servers) == 1
    assert servers[0].guild_id == GUILD_ID
    assert len(published) == 1
    assert published[0][0] == "setup_tournament"


# ── 拒否されるケース（保存も Bot への依頼も起きない） ──────────────────────────

@pytest.mark.security
@pytest.mark.asyncio
async def test_p05_003_other_organizer_forbidden(client: AsyncClient, db, published):
    """ロールが organizer でも、他人の大会は 403。"""
    owner = await f.make_user(db, role=UserRole.ORGANIZER)
    other = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=owner)

    r = await _post(client, tour.id, other)

    assert r.status_code == 403
    assert r.json()["detail"] == FORBIDDEN_DETAIL
    assert await _servers(db, tour.id) == []
    assert published == []


@pytest.mark.security
@pytest.mark.asyncio
async def test_p05_004_player_forbidden(client: AsyncClient, db, published):
    """player は入口のロール確認で 403。"""
    owner = await f.make_user(db, role=UserRole.ORGANIZER)
    player = await f.make_user(db, role=UserRole.PLAYER)
    tour = await f.make_tournament(db, organizer=owner)

    r = await _post(client, tour.id, player)

    assert r.status_code == 403
    assert r.json()["type"] == "forbidden"
    assert await _servers(db, tour.id) == []
    assert published == []


@pytest.mark.security
@pytest.mark.asyncio
async def test_p05_005_unknown_tournament_not_found(client: AsyncClient, db, published):
    """存在しない大会IDは 404（修正前は外部キー違反で 500 だった）。"""
    organizer = await f.make_user(db, role=UserRole.ORGANIZER)

    r = await _post(client, uuid.uuid4(), organizer)

    assert r.status_code == 404
    assert r.json()["type"] == "not_found"
    assert await _servers(db) == []
    assert published == []


@pytest.mark.security
@pytest.mark.asyncio
async def test_p05_006_already_bound_rejected(client: AsyncClient, db, published):
    """主催者本人でも、紐付け済みの大会は従来どおり 400 で、既存の紐付けは変わらない。"""
    owner = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=owner)
    await _bind(db, tour, guild_id="111")

    r = await _post(client, tour.id, owner, guild_id="222")

    assert r.status_code == 400
    assert r.json()["type"] == "business_rule_error"
    assert [s.guild_id for s in await _servers(db, tour.id)] == ["111"]
    assert published == []


@pytest.mark.security
@pytest.mark.asyncio
async def test_p05_007_other_organizer_forbidden_on_bound(client: AsyncClient, db, published):
    """紐付け済みの大会でも、他人には 400 ではなく 403（紐付けの有無を見せない）。"""
    owner = await f.make_user(db, role=UserRole.ORGANIZER)
    other = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=owner)
    await _bind(db, tour, guild_id="111")

    r = await _post(client, tour.id, other, guild_id="222")

    assert r.status_code == 403
    assert r.json()["detail"] == FORBIDDEN_DETAIL
    assert [s.guild_id for s in await _servers(db, tour.id)] == ["111"]
    assert published == []
