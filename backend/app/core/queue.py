"""Queue abstraction — routes to SQS or Redis list depending on USE_REDIS_QUEUE.

Demo (free tier):  USE_REDIS_QUEUE=true  → Upstash Redis LPUSH/BRPOP
AWS (mvp/prod):    USE_REDIS_QUEUE=false → SQS SendMessage
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


async def enqueue_match_event(body: dict) -> None:
    from app.core.config import settings
    await _enqueue(settings.SQS_MATCH_QUEUE_URL, settings.REDIS_QUEUE_MATCH_KEY, body)


async def enqueue_notification_event(body: dict) -> None:
    from app.core.config import settings
    await _enqueue(settings.SQS_NOTIFICATION_QUEUE_URL, settings.REDIS_QUEUE_NOTIFICATION_KEY, body)


async def enqueue_analytics_event(body: dict) -> None:
    from app.core.config import settings
    await _enqueue(settings.SQS_ANALYTICS_QUEUE_URL, settings.REDIS_QUEUE_ANALYTICS_KEY, body)


async def _enqueue(sqs_url: str | None, redis_key: str, body: dict) -> None:
    from app.core.config import settings

    if settings.USE_REDIS_QUEUE:
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.lpush(redis_key, json.dumps(body, ensure_ascii=False))
        log.debug("enqueued to redis", key=redis_key, event_type=body.get("event_type"))
    else:
        if not sqs_url:
            raise RuntimeError(
                "SQS queue URL is not configured. "
                "Set SQS_MATCH/NOTIFICATION/ANALYTICS_QUEUE_URL or enable USE_REDIS_QUEUE."
            )
        import boto3
        loop = asyncio.get_event_loop()
        sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
        await loop.run_in_executor(
            None,
            lambda: sqs.send_message(QueueUrl=sqs_url, MessageBody=json.dumps(body, ensure_ascii=False)),
        )
        log.debug("enqueued to sqs", queue=sqs_url, event_type=body.get("event_type"))
