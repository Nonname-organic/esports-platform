"""S3 export handler: ships raw analytics_events to S3 as NDJSON.

Partition layout:
  s3://<bucket>/analytics/raw/
    year=YYYY/month=MM/day=DD/<batch-uuid>.jsonl

Each line is a JSON object (one event per line).  Athena and Glue can
read this format natively with a ROW FORMAT SERDE 'org.openx.data.jsonserde'.

This handler is designed to be called from the ARQ scheduler (daily at 3 AM)
and can also be triggered manually via a one-off ARQ job.
"""

import io
import json
import logging
import uuid
from datetime import datetime, timezone

import aioboto3
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.analytics import AnalyticsRepository

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000
_S3_PREFIX = "analytics/raw"


async def handle_stats_export(db: AsyncSession) -> int:
    """Export unprocessed analytics_events to S3 and mark them processed.

    Returns the total number of events exported.
    """
    if not settings.S3_BUCKET_NAME:
        logger.info("S3_BUCKET_NAME not configured — skipping export")
        return 0

    repo = AnalyticsRepository(db)
    total_exported = 0

    session = aioboto3.Session()
    async with session.client("s3", region_name=settings.AWS_REGION) as s3:
        while True:
            events = await repo.get_unprocessed_events(limit=_BATCH_SIZE)
            if not events:
                break

            # Partition by date
            by_date: dict[str, list] = {}
            for event in events:
                ts = event.created_at
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                partition = f"year={ts.year}/month={ts.month:02d}/day={ts.day:02d}"
                by_date.setdefault(partition, []).append(event)

            for partition, partition_events in by_date.items():
                ndjson = io.StringIO()
                for ev in partition_events:
                    record = {
                        "id": str(ev.id),
                        "event_type": ev.event_type,
                        "source": ev.source.value if hasattr(ev.source, "value") else ev.source,
                        "tournament_id": str(ev.tournament_id) if ev.tournament_id else None,
                        "team_id": str(ev.team_id) if ev.team_id else None,
                        "player_id": str(ev.player_id) if ev.player_id else None,
                        "match_id": str(ev.match_id) if ev.match_id else None,
                        "payload": ev.payload,
                        "created_at": ev.created_at.isoformat(),
                    }
                    ndjson.write(json.dumps(record, ensure_ascii=False) + "\n")

                key = f"{_S3_PREFIX}/{partition}/{uuid.uuid4()}.jsonl"
                await s3.put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=key,
                    Body=ndjson.getvalue().encode("utf-8"),
                    ContentType="application/x-ndjson",
                )
                logger.info(
                    "Exported %d events → s3://%s/%s",
                    len(partition_events),
                    settings.S3_BUCKET_NAME,
                    key,
                )

            event_ids = [ev.id for ev in events]
            await repo.mark_events_processed(event_ids)
            await db.commit()

            total_exported += len(events)

            if len(events) < _BATCH_SIZE:
                break

    logger.info("S3 export complete: %d total events exported", total_exported)
    return total_exported
