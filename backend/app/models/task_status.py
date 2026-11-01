import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TaskStatus(Base):
    __tablename__ = "task_statuses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    rank: Mapped[float] = mapped_column(Float, nullable=False)
    color_hex: Mapped[str] = mapped_column(
        String(7),
        default="#6366F1",
        server_default=text("'#6366F1'"),
        nullable=False,
    )
    is_completed_state: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_task_statuses_project_id"),
        CheckConstraint("color_hex ~ '^#[0-9A-Fa-f]{6}$'", name="chk_task_statuses_color_hex"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_task_statuses_project",
            ondelete="CASCADE",
        ),
        Index(
            "uq_statuses_name",
            "project_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("idx_statuses_rank", "project_id", "rank"),
    )

