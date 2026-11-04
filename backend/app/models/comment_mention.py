import uuid
from datetime import datetime
from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class CommentMention(Base):
    __tablename__ = "comment_mentions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE", name="fk_comment_mentions_comment"),
        nullable=False,
    )
    mentioned_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "mentioned_user_id"],
            ["workspace_members.workspace_id", "workspace_members.user_id"],
            name="fk_comment_mentions_member",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "comment_id", "mentioned_user_id",
            name="uq_comment_mentions_unique",
        ),
        Index(
            "idx_comment_mentions_user",
            "workspace_id",
            "mentioned_user_id",
        ),
    )

