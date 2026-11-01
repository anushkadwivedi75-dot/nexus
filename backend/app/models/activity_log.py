import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import (
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


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    task_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    verb: Mapped[str] = mapped_column(String(50), nullable=False)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_activity_logs_project",
            ondelete="SET NULL (project_id)",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "task_id"],
            ["tasks.workspace_id", "tasks.id"],
            name="fk_activity_logs_task",
            ondelete="SET NULL (task_id)",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "actor_id"],
            ["workspace_members.workspace_id", "workspace_members.user_id"],
            name="fk_activity_logs_actor_workspace_member",
            ondelete="SET NULL (actor_id)",
        ),
        Index("idx_activity_workspace", "workspace_id", created_at.desc()),
    )

