import uuid
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Tag(Base):
    __tablename__ = "tags"

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
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color_hex: Mapped[str] = mapped_column(
        String(7),
        default="#8B5CF6",
        server_default=text("'#8B5CF6'"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_tags_workspace_id"),
        UniqueConstraint("workspace_id", "name", name="uq_tags_workspace_name"),
        CheckConstraint("color_hex ~ '^#[0-9A-Fa-f]{6}$'", name="chk_tags_color_hex"),
    )

