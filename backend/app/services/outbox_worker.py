import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import redis.asyncio as aioredis
from app.models.outbox_event import OutboxEvent

logger = logging.getLogger(__name__)

CLAIM_QUERY = text("""
WITH claimable AS (
    SELECT id 
    FROM outbox_events
    WHERE (
        (status = 'PENDING' AND next_retry_at <= NOW() AND is_dead_letter = FALSE)
        OR
        (status = 'PROCESSING' AND claimed_at < NOW() - INTERVAL '60 seconds')
    )
    ORDER BY created_at ASC
    LIMIT :batch_size
    FOR UPDATE SKIP LOCKED
)
UPDATE outbox_events
SET status = 'PROCESSING',
    claimed_at = NOW(),
    claimed_by = :worker_id,
    claim_epoch = claim_epoch + 1
FROM claimable
WHERE outbox_events.id = claimable.id
RETURNING 
    outbox_events.id,
    outbox_events.workspace_id,
    outbox_events.channel,
    outbox_events.event_type,
    outbox_events.payload,
    outbox_events.retry_count,
    outbox_events.claim_epoch;
""")

ACK_QUERY = text("""
UPDATE outbox_events
SET status = 'PUBLISHED',
    published_at = NOW(),
    claimed_by = NULL
WHERE id = :event_id AND claim_epoch = :claimed_epoch;
""")

FAIL_QUERY = text("""
UPDATE outbox_events
SET status = :status,
    retry_count = :retry_count,
    next_retry_at = :next_retry_at,
    is_dead_letter = :is_dead_letter,
    last_error = :last_error,
    claimed_by = NULL
WHERE id = :event_id AND claim_epoch = :claimed_epoch;
""")


class OutboxWorker:
    def __init__(self, worker_id: str | None = None):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self._stop_event = asyncio.Event()

    async def claim_batch(self, db: AsyncSession, batch_size: int = 50) -> List[dict]:
        """
        Atomically claims a batch of pending or expired outbox events using
        PostgreSQL row-level locking (FOR UPDATE SKIP LOCKED) and increments claim_epoch.
        """
        res = await db.execute(
            CLAIM_QUERY,
            {"batch_size": batch_size, "worker_id": self.worker_id},
        )
        rows = res.mappings().all()
        # Commit immediately so row locks are released before Redis network I/O
        await db.commit()
        return [dict(r) for r in rows]

    async def acknowledge_event(
        self, db: AsyncSession, event_id: uuid.UUID, claimed_epoch: int
    ) -> bool:
        """
        Fenced acknowledgement: only succeeds if claim_epoch matches.
        Prevents zombie workers from writing stale acknowledgements.
        """
        res = await db.execute(
            ACK_QUERY,
            {"event_id": event_id, "claimed_epoch": claimed_epoch},
        )
        await db.commit()
        rowcount = res.rowcount
        if rowcount == 0:
            logger.warning(
                "FENCING_REJECTION: Outbox event %s claim_epoch %d was superseded by another worker.",
                event_id,
                claimed_epoch,
            )
            return False
        return True

    async def fail_event(
        self,
        db: AsyncSession,
        event_id: uuid.UUID,
        claimed_epoch: int,
        current_retry_count: int,
        error_msg: str,
    ):
        """
        Records failure with exponential backoff and jitter, or marks dead-letter if max retries exceeded.
        """
        next_retries = current_retry_count + 1
        is_dead_letter = next_retries >= 10
        status_val = "FAILED" if is_dead_letter else "PENDING"

        backoff_seconds = min(60.0, (2.0 ** min(next_retries, 6))) + random.uniform(0.1, 1.0)
        next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)

        await db.execute(
            FAIL_QUERY,
            {
                "event_id": event_id,
                "claimed_epoch": claimed_epoch,
                "status": status_val,
                "retry_count": next_retries,
                "next_retry_at": next_retry_at,
                "is_dead_letter": is_dead_letter,
                "last_error": str(error_msg)[:1000],
            },
        )
        await db.commit()

    async def publish_event(
        self, redis: aioredis.Redis, event: dict
    ):
        """
        Publishes the event to Redis Pub/Sub channels and broadcasts auth invalidation if applicable.
        """
        payload_data = event["payload"]
        message_str = json.dumps(payload_data) if not isinstance(payload_data, str) else payload_data

        # 1. Publish to workspace channel
        target_channel = event["channel"] or f"workspace:{event['workspace_id']}"
        await redis.publish(target_channel, message_str)

        # 2. Check for administrative control signals (auth invalidation)
        event_type = event.get("event_type", "")
        if event_type in ("workspace.member_removed", "workspace.member_updated", "workspace.ownership_transferred"):
            inner_payload = payload_data.get("payload", {}) if isinstance(payload_data, dict) else {}
            target_user_id = inner_payload.get("target_user_id") or inner_payload.get("previous_owner_id")

            if target_user_id:
                action = (
                    "EVICT_WORKSPACE_MEMBER"
                    if event_type == "workspace.member_removed"
                    else "UPDATE_WORKSPACE_PERMISSIONS"
                )
                control_msg = {
                    "action": action,
                    "workspace_id": str(event["workspace_id"]),
                    "user_id": str(target_user_id),
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                }
                await redis.publish("nexus:control:auth_invalidation", json.dumps(control_msg))

    async def process_batch(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: aioredis.Redis,
        batch_size: int = 50,
    ) -> int:
        """Processes a single batch of claimable events."""
        async with session_factory() as db:
            claimed_events = await self.claim_batch(db, batch_size=batch_size)

        if not claimed_events:
            return 0

        for evt in claimed_events:
            event_id = evt["id"]
            claimed_epoch = evt["claim_epoch"]
            retry_count = evt["retry_count"]

            try:
                await self.publish_event(redis, evt)
                async with session_factory() as db:
                    await self.acknowledge_event(db, event_id, claimed_epoch)
            except Exception as e:
                logger.error(
                    "Error publishing outbox event %s to Redis: %s",
                    event_id,
                    e,
                    exc_info=True,
                )
                try:
                    async with session_factory() as db:
                        await self.fail_event(db, event_id, claimed_epoch, retry_count, str(e))
                except Exception as db_err:
                    logger.critical("Failed to record failure for outbox event %s: %s", event_id, db_err)

        return len(claimed_events)

    async def run_loop(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: aioredis.Redis,
        poll_interval: float = 0.5,
    ):
        """Runs the background processing loop until stopped."""
        self.is_running = True
        self._stop_event.clear()
        logger.info("Outbox worker %s started.", self.worker_id)

        while not self._stop_event.is_set():
            try:
                processed_count = await self.process_batch(session_factory, redis)
                if processed_count == 0:
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=poll_interval)
                    except asyncio.TimeoutError:
                        pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Outbox worker loop error: %s", e, exc_info=True)
                await asyncio.sleep(poll_interval)

        self.is_running = False
        logger.info("Outbox worker %s stopped.", self.worker_id)

    def stop(self):
        self._stop_event.set()


outbox_worker = OutboxWorker()
