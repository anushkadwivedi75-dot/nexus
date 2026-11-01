import uuid
from sqlalchemy import ForeignKeyConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TaskAssignee(Base):
    __tablename__ = "task_assignees"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("task_id", "user_id", name="pk_task_assignees"),
        ForeignKeyConstraint(
            ["workspace_id", "task_id"],
            ["tasks.workspace_id", "tasks.id"],
            name="fk_task_assignees_task",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "user_id"],
            ["workspace_members.workspace_id", "workspace_members.user_id"],
            name="fk_task_assignees_workspace_member",
            ondelete="CASCADE",
        ),
    )

