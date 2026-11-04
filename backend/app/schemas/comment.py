import re
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class CommentAuthor(BaseModel):
    id: Optional[uuid.UUID] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class CommentMentionItem(BaseModel):
    user_id: uuid.UUID
    full_name: Optional[str] = None
    email: Optional[str] = None


class CommentCreate(BaseModel):
    content: str = Field(..., max_length=5000, description="Comment text or Markdown")
    parent_comment_id: Optional[uuid.UUID] = Field(None, description="Optional parent comment ID for replies")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Comment content cannot be empty or purely whitespace.")
        if len(v) > 5000:
            raise ValueError("Comment content exceeds maximum allowed length of 5000 characters.")
        return trimmed


class CommentUpdate(BaseModel):
    content: str = Field(..., max_length=5000, description="Updated comment text")
    version: int = Field(..., description="Optimistic concurrency version of the comment")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Comment content cannot be empty or purely whitespace.")
        if len(v) > 5000:
            raise ValueError("Comment content exceeds maximum allowed length of 5000 characters.")
        return trimmed


class CommentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    author_id: Optional[uuid.UUID] = None
    author: Optional[CommentAuthor] = None
    parent_comment_id: Optional[uuid.UUID] = None
    content: str
    is_deleted: bool = False
    version: int
    created_at: datetime
    updated_at: datetime
    reply_count: int = 0
    replies: List["CommentResponse"] = Field(default_factory=list)
    mentions: List[CommentMentionItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CommentCursorPagination(BaseModel):
    items: List[CommentResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False

