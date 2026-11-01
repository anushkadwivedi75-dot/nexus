import uuid
from sqlalchemy import ForeignKeyConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TaskTag(Base):
    __tablename__ = "task_tags"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("task_id", "tag_id", name="pk_task_tags"),
        ForeignKeyConstraint(
            ["workspace_id", "task_id"],
            ["tasks.workspace_id", "tasks.id"],
            name="fk_task_tags_task",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "tag_id"],
            ["tags.workspace_id", "tags.id"],
            name="fk_task_tags_tag",
            ondelete="CASCADE",
        ),
    )
