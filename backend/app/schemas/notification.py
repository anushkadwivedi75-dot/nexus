import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NotificationActor(BaseModel):
    id: Optional[uuid.UUID] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    recipient_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor: Optional[NotificationActor] = None
    action_type: str
    entity_type: str
    entity_id: uuid.UUID
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    read_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCursorPagination(BaseModel):
    items: List[NotificationResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False
    unread_count: int = 0


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationReadAllRequest(BaseModel):
    workspace_id: Optional[uuid.UUID] = None
