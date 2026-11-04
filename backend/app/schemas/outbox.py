import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EventEnvelope(BaseModel):
    """
    Standardized versioned event envelope for all Nexus domain events.
    Adheres to Section 11 of NEXUS_SYSTEM_BLUEPRINT_PHASE_0_v1.3.1.
    """
    schema_version: int = Field(default=1, description="Event envelope schema version")
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique event identifier")
    event_type: str = Field(..., description="Dot-notated event type (e.g. 'task.created')")
    workspace_id: uuid.UUID = Field(..., description="Tenant workspace identifier")
    actor_id: uuid.UUID | None = Field(default=None, description="User who triggered the event")
    entity_type: str = Field(..., description="Domain entity type ('task', 'project', 'workspace', etc.)")
    entity_id: uuid.UUID = Field(..., description="Identifier of the mutated entity")
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when mutation occurred",
    )
    payload: dict[str, Any] = Field(default_factory=dict, description="Domain event payload")

    model_config = ConfigDict(from_attributes=True)


class ControlInvalidationMessage(BaseModel):
    """
    Real-time administrative invalidation frame broadcast over
    Redis channel 'nexus:control:auth_invalidation'.
    """
    action: str = Field(
        ...,
        description="'EVICT_WORKSPACE_MEMBER' | 'REVOKE_PROJECT_SUBSCRIPTION' | 'REVOKE_USER_SESSIONS'",
    )
    workspace_id: uuid.UUID | None = None
    user_id: uuid.UUID
    project_id: uuid.UUID | None = None
    timestamp: float = Field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp(),
        description="Unix timestamp of invalidation event",
    )

