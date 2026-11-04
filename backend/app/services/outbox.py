import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.outbox_event import OutboxEvent
from app.schemas.outbox import EventEnvelope

logger = logging.getLogger(__name__)


class OutboxService:
    @classmethod
    async def create_event(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        event_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        payload: dict[str, Any],
        actor_id: uuid.UUID | None = None,
        channel: str | None = None,
    ) -> OutboxEvent:
        """
        Atomically stages an event into the outbox within the caller's active database transaction.
        Enforces EventEnvelope validation and schema versioning.
        """
        event_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        envelope = EventEnvelope(
            schema_version=1,
            event_id=event_id,
            event_type=event_type,
            workspace_id=workspace_id,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            occurred_at=now,
            payload=payload,
        )

        target_channel = channel or f"workspace:{workspace_id}"

        outbox_event = OutboxEvent(
            id=event_id,
            workspace_id=workspace_id,
            channel=target_channel,
            event_type=event_type,
            payload=envelope.model_dump(mode="json"),
            status="PENDING",
            retry_count=0,
            claim_epoch=0,
            is_dead_letter=False,
            created_at=now,
        )
        db.add(outbox_event)
        return outbox_event


outbox_service = OutboxService()

