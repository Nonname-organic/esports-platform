"""NOTIF-*: 通知は本人のみ（IDOR防止）。"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationChannel, NotificationType
from app.models.tournament import Notification


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _make_notif(db, user_id, title):
    n = Notification(
        user_id=user_id, type=NotificationType.GENERAL, channel=NotificationChannel.IN_APP,
        title=title, body="body", is_read=False, created_at=datetime.now(timezone.utc),
    )
    db.add(n)
    await db.flush()
    return n


@pytest.mark.security
@pytest.mark.asyncio
async def test_notif002_only_own_notifications(
    client: AsyncClient, db: AsyncSession,
    player_user, player_token, second_player_user, second_player_token,
):
    """NOTIF-002: 他人の通知は見えない。"""
    await _make_notif(db, player_user.id, "for-player-1")
    await _make_notif(db, second_player_user.id, "for-player-2")

    r1 = await client.get("/api/v1/notifications", headers=_h(player_token))
    assert r1.status_code == 200
    titles1 = [n["title"] for n in r1.json()["data"]]
    assert "for-player-1" in titles1
    assert "for-player-2" not in titles1


@pytest.mark.asyncio
async def test_notif003_unread_count(
    client: AsyncClient, db: AsyncSession, player_user, player_token,
):
    """NOTIF-003: 未読数。"""
    await _make_notif(db, player_user.id, "n1")
    await _make_notif(db, player_user.id, "n2")
    r = await client.get("/api/v1/notifications/unread-count", headers=_h(player_token))
    assert r.status_code == 200
    assert r.json()["data"]["count"] >= 2


@pytest.mark.asyncio
async def test_notif001_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/notifications")).status_code == 401
