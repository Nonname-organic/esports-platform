"""
Event-Driven Architecture
EventBridge → SQS → Worker → Analytics/Ranking/Notification

イベントタイプ定義と発行ユーティリティ
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import boto3
from pydantic import BaseModel

from app.core.config import settings


class EventType(str, Enum):
    # Tournament
    TOURNAMENT_CREATED = "TournamentCreated"
    TOURNAMENT_STARTED = "TournamentStarted"
    TOURNAMENT_COMPLETED = "TournamentCompleted"
    TOURNAMENT_CANCELLED = "TournamentCancelled"

    # Check-in
    CHECKIN_OPENED = "CheckInOpened"
    CHECKIN_COMPLETED = "CheckInCompleted"
    AUTO_FORFEIT_TRIGGERED = "AutoForfeitTriggered"

    # Match
    MATCH_CREATED = "MatchCreated"
    MATCH_STARTED = "MatchStarted"
    MATCH_FINISHED = "MatchFinished"
    MATCH_FORFEITED = "MatchForfeited"
    SCORE_UPDATED = "ScoreUpdated"
    ROUND_FINISHED = "RoundFinished"
    MVP_CALCULATED = "MvpCalculated"

    # Player
    PLAYER_REGISTERED = "PlayerRegistered"
    RATING_UPDATED = "RatingUpdated"
    ACHIEVEMENT_EARNED = "AchievementEarned"

    # Team
    TEAM_CREATED = "TeamCreated"
    TEAM_REGISTERED = "TeamRegistered"
    ROSTER_CHANGED = "RosterChanged"

    # Registration
    REGISTRATION_APPROVED = "RegistrationApproved"
    REGISTRATION_REJECTED = "RegistrationRejected"
    RESULT_SUBMITTED = "ResultSubmitted"

    # Analytics
    STATS_AGGREGATED = "StatsAggregated"
    RANKING_UPDATED = "RankingUpdated"


class PlatformEvent(BaseModel):
    event_id: str = ""
    event_type: EventType
    aggregate_id: str
    aggregate_type: str
    payload: dict[str, Any]
    timestamp: str = ""
    version: str = "1.0"
    source: str = "esports-platform"

    def model_post_init(self, __context: Any) -> None:
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class EventBus:
    """EventBridge + SQS を使ったイベントバス"""

    def __init__(self):
        self._eb_client = None
        self._sqs_client = None

    def _get_eb(self):
        if not self._eb_client:
            self._eb_client = boto3.client("events", region_name=settings.AWS_REGION)
        return self._eb_client

    def _get_sqs(self):
        if not self._sqs_client:
            self._sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)
        return self._sqs_client

    async def publish(self, event: PlatformEvent) -> None:
        """イベントを EventBridge に発行（デモ環境では SQS に直接送信）"""
        try:
            if settings.ENVIRONMENT == "demo":
                # デモ環境: SQS に直接送信
                await self._publish_to_sqs(event)
            else:
                # 本番環境: EventBridge 経由
                await self._publish_to_eventbridge(event)
        except Exception as e:
            # イベント発行失敗はログに記録するが例外は上に伝播しない
            import structlog
            structlog.get_logger().error("event_publish_failed", event_type=event.event_type, error=str(e))

    async def _publish_to_sqs(self, event: PlatformEvent) -> None:
        import asyncio
        loop = asyncio.get_event_loop()
        queue_url = settings.SQS_MATCH_QUEUE_URL or ""
        if not queue_url:
            return
        sqs = self._get_sqs()
        await loop.run_in_executor(
            None,
            lambda: sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=event.model_dump_json(),
                MessageAttributes={
                    "EventType": {
                        "StringValue": event.event_type.value,
                        "DataType": "String",
                    }
                },
            ),
        )

    async def _publish_to_eventbridge(self, event: PlatformEvent) -> None:
        import asyncio
        loop = asyncio.get_event_loop()
        eb = self._get_eb()
        await loop.run_in_executor(
            None,
            lambda: eb.put_events(
                Entries=[{
                    "Source": event.source,
                    "DetailType": event.event_type.value,
                    "Detail": event.model_dump_json(),
                    "EventBusName": "esports-platform",
                }]
            ),
        )


# シングルトン
event_bus = EventBus()


async def publish_event(event_type: EventType, aggregate_id: str, aggregate_type: str, payload: dict) -> None:
    """イベント発行ショートカット"""
    event = PlatformEvent(
        event_type=event_type,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        payload=payload,
    )
    await event_bus.publish(event)
