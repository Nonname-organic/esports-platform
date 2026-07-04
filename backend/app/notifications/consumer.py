"""NotificationConsumer — domain_events を Matrix に従い通知へ変換する（EventConsumer）。

OutboxRelay の InProcessDispatcher に register される（worker）。
自前の DB セッションで受信者解決・通知作成を行い commit する（Relay の Outbox 記録とは別Tx）。
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.redis import RedisCache
from app.events.envelope import EventEnvelope
from app.notifications.channels import (
    BrowserChannel, ChannelRegistry, DiscordChannel, EmailChannel, Message,
)
from app.notifications.dispatcher import NotificationDispatcher
from app.notifications.matrix import NotifRule, rule_for

logger = structlog.get_logger()


class NotificationConsumer:
    """Matrix に載っているイベント型のみを処理する。"""

    def __init__(self, cache: RedisCache):
        channels = ChannelRegistry([
            BrowserChannel(cache),
            DiscordChannel(cache),
            EmailChannel(),
        ])
        self._dispatcher = NotificationDispatcher(channels)

    # EventConsumer Protocol ---------------------------------------------------
    def handles(self, event_type: str) -> bool:
        return rule_for(event_type) is not None

    async def handle(self, envelope: EventEnvelope) -> None:
        rule = rule_for(envelope.type)
        if rule is None:
            return
        async with AsyncSessionLocal() as db:
            recipients, ctx = await self._resolve(db, envelope, rule)
            if not recipients:
                logger.info("notification_no_recipients", event_type=envelope.type, event_id=envelope.event_id)
                return
            message = Message(
                subtype=rule.subtype,
                title=rule.title,
                body=rule.body_template.format(**ctx),
                action_url=(rule.action_url_template.format(**ctx) if rule.action_url_template else None),
                metadata={"event_id": envelope.event_id, "event_type": envelope.type},
            )
            sent = await self._dispatcher.dispatch(
                db,
                recipients=recipients,
                category=rule.category,
                channels=rule.channels,
                message=message,
            )
            await db.commit()
            logger.info("notification_dispatched", event_type=envelope.type, recipients=len(recipients), sent=sent)

    # 受信者解決 ---------------------------------------------------------------
    async def _resolve(
        self, db: AsyncSession, envelope: EventEnvelope, rule: NotifRule
    ) -> tuple[list[uuid.UUID], dict]:
        """(受信者 user_id 群, テンプレート用コンテキスト) を返す。"""
        if rule.recipients == "registered_team":
            return await self._registered_team(db, envelope)
        logger.warning("notification_unknown_recipients", rule=rule.recipients)
        return [], {}

    async def _registered_team(
        self, db: AsyncSession, envelope: EventEnvelope
    ) -> tuple[list[uuid.UUID], dict]:
        """申請チームの全メンバー（user_id）+ 大会名コンテキスト。"""
        from app.models.player import Player
        from app.models.team import TeamMember
        from app.models.tournament import Tournament

        after = envelope.after or {}
        team_id = after.get("team_id")
        tournament_id = envelope.entity_id
        if not team_id:
            return [], {}

        rows = (await db.execute(
            select(Player.user_id)
            .join(TeamMember, TeamMember.player_id == Player.id)
            .where(TeamMember.team_id == uuid.UUID(str(team_id)),
                   TeamMember.left_at.is_(None),
                   Player.user_id.is_not(None))
        )).scalars().all()
        recipients = [u for u in rows if u]

        tname = await db.scalar(select(Tournament.name).where(Tournament.id == uuid.UUID(str(tournament_id))))
        ctx = {"tournament_name": tname or "大会", "tournament_id": str(tournament_id)}
        return recipients, ctx
