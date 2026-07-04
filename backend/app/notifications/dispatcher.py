"""NotificationDispatcher — 受信者×チャネルへ Message を配信する。

Preference（③・ユーザーごとON/OFF）は本 Dispatcher の判定点。現フェーズは全ON のスタブ。
1チャネル/1受信者の失敗は隔離してログに残し、他を止めない（Matrix 準拠）。
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.channels import ChannelRegistry, Message

logger = structlog.get_logger()


class PreferenceResolver:
    """通知設定の判定。③ 実装までは常に有効（全ON）を返すスタブ。

    ③ 実装時: notification_preferences(JSONB) を category/channel で参照するだけで
    Matrix と整合する（precedence: global channel OFF > per-entity mute > category OFF > default ON）。
    """

    async def is_enabled(self, user_id: uuid.UUID, category: str, channel: str) -> bool:
        return True


class NotificationDispatcher:
    def __init__(self, channels: ChannelRegistry, prefs: PreferenceResolver | None = None):
        self._channels = channels
        self._prefs = prefs or PreferenceResolver()

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
        sent = 0
        for user_id in recipients:
            for ch_name in channels:
                provider = self._channels.get(ch_name)
                if provider is None:
                    continue
                try:
                    if not await self._prefs.is_enabled(user_id, category, ch_name):
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
