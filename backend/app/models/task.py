import uuid
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        server_default=text("'medium'"),
        nullable=False,
    )
    rank: Mapped[float] = mapped_column(Float, nullable=False)
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    creator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_tasks_workspace_id"),
        UniqueConstraint("project_id", "task_number", name="uq_tasks_project_task_number"),
        CheckConstraint("task_number > 0", name="chk_tasks_task_number_positive"),
        CheckConstraint(
            "priority IN ('urgent', 'high', 'medium', 'low')",
            name="chk_tasks_priority",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_tasks_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "status_id"],
            ["task_statuses.project_id", "task_statuses.id"],
            name="fk_tasks_status",
            ondelete="RESTRICT",
        ),
        Index(
            "idx_tasks_board_sort",
            "project_id",
            "status_id",
            "rank",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_tasks_search",
            func.to_tsvector(text("'english'"), title + text("' '") + func.coalesce(description, text("''"))),
            postgresql_using="gin",
        ),
    )

