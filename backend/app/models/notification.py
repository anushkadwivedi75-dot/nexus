import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        default=dict,
        nullable=False,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deduplication_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('task', 'project', 'comment', 'workspace')",
            name="chk_notifications_entity_type",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "recipient_id"],
            ["workspace_members.workspace_id", "workspace_members.user_id"],
            name="fk_notifications_recipient_workspace_member",
            ondelete="CASCADE",
        ),
        # Default inbox query index
        Index(
            "idx_notifications_recipient",
            "recipient_id",
            "is_read",
            created_at.desc(),
        ),
        # Inbox query with archive filtering
        Index(
            "idx_notifications_inbox",
            "recipient_id",
            "archived_at",
            "is_read",
            created_at.desc(),
        ),
        # Ultra-fast unread count index
        Index(
            "idx_notifications_unread_count",
            "recipient_id",
            postgresql_where=text("archived_at IS NULL AND is_read = false"),
        ),
        # Deduplication lookup index
        Index(
            "idx_notifications_dedup",
            "workspace_id",
            "recipient_id",
            "deduplication_key",
            postgresql_where=text("deduplication_key IS NOT NULL"),
        ),
    )
