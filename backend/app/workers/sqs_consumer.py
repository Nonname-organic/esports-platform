"""Worker entry point — polls SQS (AWS) or Redis lists (free-tier demo)."""

import asyncio
import json
import logging
import signal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.redis import RedisCache

logger = logging.getLogger(__name__)

# All Redis queue keys polled together via BRPOP.
_REDIS_QUEUE_KEYS = [
    settings.REDIS_QUEUE_MATCH_KEY,
    settings.REDIS_QUEUE_NOTIFICATION_KEY,
    settings.REDIS_QUEUE_ANALYTICS_KEY,
]


class SQSConsumer:
    def __init__(self):
        self._running = True
        if not settings.USE_REDIS_QUEUE:
            import boto3
            self._sqs = boto3.client("sqs", region_name=settings.AWS_REGION)

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        mode = "Redis" if settings.USE_REDIS_QUEUE else "SQS"
        logger.info(f"Worker started (queue backend: {mode})")
        while self._running:
            try:
                await self._poll()
            except Exception as e:
                logger.error(f"Poll error: {e}")
                await asyncio.sleep(5)

    async def _poll(self) -> None:
        if settings.USE_REDIS_QUEUE:
            await self._poll_redis()
        else:
            await self._poll_sqs()

    # ------------------------------------------------------------------
    # SQS backend
    # ------------------------------------------------------------------

    async def _poll_sqs(self) -> None:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._sqs.receive_message(
                QueueUrl=settings.SQS_MATCH_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                VisibilityTimeout=60,
            ),
        )
        for message in response.get("Messages", []):
            await self._process_message(message, delete_from_sqs=True)

    async def _delete_sqs_message(self, receipt_handle: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._sqs.delete_message(
                QueueUrl=settings.SQS_MATCH_QUEUE_URL,
                ReceiptHandle=receipt_handle,
            ),
        )

    # ------------------------------------------------------------------
    # Redis backend
    # ------------------------------------------------------------------

    async def _poll_redis(self) -> None:
        redis = await get_redis()
        # BRPOP blocks up to `timeout` seconds across all queue keys.
        # Returns (key_bytes, value_bytes) or None on timeout.
        result = await redis.brpop(_REDIS_QUEUE_KEYS, timeout=20)
        if result:
            _key, value = result
            payload = value.decode() if isinstance(value, bytes) else value
            await self._process_message({"Body": payload}, delete_from_sqs=False)

    # ------------------------------------------------------------------
    # Shared processing
    # ------------------------------------------------------------------

    async def _process_message(self, message: dict, *, delete_from_sqs: bool) -> None:
        receipt_handle = message.get("ReceiptHandle")
        try:
            body = json.loads(message["Body"])
            event_type = body.get("event_type")

            async with AsyncSessionLocal() as db:
                redis = await get_redis()
                cache = RedisCache(redis)
                await self._dispatch(event_type, body, db, cache)
                await db.commit()

            if delete_from_sqs and receipt_handle:
                await self._delete_sqs_message(receipt_handle)

            logger.info(f"Processed event: {event_type}")

        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            # SQS: VisibilityTimeout expiry causes re-delivery automatically.
            # Redis: message was already popped — re-enqueue on retry if needed.

    async def _dispatch(
        self,
        event_type: str,
        body: dict,
        db: AsyncSession,
        cache: RedisCache,
    ) -> None:
        from app.workers.handlers.analytics_aggregation import handle_analytics_aggregation
        from app.workers.handlers.match_result import handle_match_result
        from app.workers.handlers.notification import handle_notification

        handlers = {
            "match_result_registered": handle_match_result,
            "notification_send": handle_notification,
            "analytics_stats_update": handle_analytics_aggregation,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(body, db, cache)
            if event_type == "match_result_registered":
                await handle_analytics_aggregation(body, db, cache)
        else:
            logger.warning(f"Unknown event type: {event_type}")


async def main() -> None:
    consumer = SQSConsumer()

    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, stopping...")
        consumer.stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    await consumer.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
