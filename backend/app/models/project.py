import uuid
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Project(Base):
    __tablename__ = "projects"

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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    task_counter: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        server_default=text("'active'"),
        nullable=False,
    )
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
        UniqueConstraint("workspace_id", "id", name="uq_projects_workspace_id"),
        Index(
            "uq_projects_key",
            "workspace_id",
            "key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint("key ~ '^[A-Z0-9]{2,10}$'", name="chk_projects_key_format"),
        CheckConstraint(
            "task_counter >= 0 AND task_counter < 9223372036854775800",
            name="chk_projects_task_counter",
        ),
        CheckConstraint("status IN ('active', 'archived', 'completed')", name="chk_projects_status"),
        ForeignKeyConstraint(
            ["workspace_id", "lead_id"],
            ["workspace_members.workspace_id", "workspace_members.user_id"],
            name="fk_projects_lead_workspace_member",
            ondelete="SET NULL (lead_id)",
        ),
    )

