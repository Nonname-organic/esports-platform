"""NotificationDispatcher — 受信者×チャネルへ Message を配信する。

配信判定（③・ユーザーごとON/OFF）は **PreferenceService（唯一のSSOT / ADR-0010）** に委ねる。
Dispatcher は JSONB 構造を知らず、`is_enabled(user, category, channel)` の真偽だけを見る。
1チャネル/1受信者の失敗は隔離してログに残し、他を止めない（Matrix 準拠）。
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.channels import ChannelRegistry, Message
from app.notifications.preferences import PreferenceService

logger = structlog.get_logger()


class NotificationDispatcher:
    def __init__(self, channels: ChannelRegistry):
        self._channels = channels

    async def dispatch(
        self,
        db: AsyncSession,
        *,
        recipients: list[uuid.UUID],
        category: str,
        channels: tuple[str, ...],
        message: Message,
    ) -> int:
        """配信し、実際に送れた (受信者×チャネル) 件数を返す。"""
        prefs = PreferenceService(db)   # 判定は PreferenceService（SSOT）に集約
        sent = 0
        for user_id in recipients:
            for ch_name in channels:
                provider = self._channels.get(ch_name)
                if provider is None:
                    continue
                try:
                    if not await prefs.is_enabled(user_id, category, ch_name):
                        continue
                    ok = await provider.send(db, user_id, message)
                    if ok:
                        sent += 1
                except Exception as e:  # noqa: BLE001 — 1件失敗で全体を止めない
                    logger.warning(
                        "notification_channel_failed",
                        user_id=str(user_id), channel=ch_name, error=str(e)[:200],
                    )
        return sent
