import uuid
from datetime import datetime
from sqlalchemy import (
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"), default=1, nullable=False)
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
        # Composite FK linking comment strictly to task inside workspace
        ForeignKeyConstraint(
            ["workspace_id", "task_id"],
            ["tasks.workspace_id", "tasks.id"],
            name="fk_comments_task",
            ondelete="CASCADE",
        ),
        # Composite FK linking comment strictly to workspace member
        ForeignKeyConstraint(
            ["workspace_id", "author_id"],
            ["workspace_members.workspace_id", "workspace_members.user_id"],
            name="fk_comments_author_workspace_member",
            ondelete="SET NULL (author_id)",
        ),
        # Unique constraint to allow self-referencing composite foreign key
        UniqueConstraint(
            "workspace_id", "task_id", "id",
            name="uq_comments_workspace_task_id",
        ),
        # Composite self-referencing FK guaranteeing replies belong to same task and workspace
        ForeignKeyConstraint(
            ["workspace_id", "task_id", "parent_comment_id"],
            ["comments.workspace_id", "comments.task_id", "comments.id"],
            name="fk_comments_parent_comment",
            ondelete="CASCADE",
        ),
        # Cursor pagination index
        Index(
            "idx_comments_task_created_id",
            "task_id",
            "created_at",
            "id",
        ),
        # Reply lookup index
        Index(
            "idx_comments_parent_id",
            "parent_comment_id",
        ),
        # Workspace scoping index
        Index(
            "idx_comments_workspace_task",
            "workspace_id",
            "task_id",
        ),
    )
