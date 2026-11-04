import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.task_status import TaskStatusResponse
from app.schemas.workspace_member import WorkspaceMemberUser


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field("medium", description="'urgent', 'high', 'medium', 'low'")
    due_date: datetime | None = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("urgent", "high", "medium", "low"):
            raise ValueError("Priority must be 'urgent', 'high', 'medium', or 'low'.")
        return clean


class TaskCreate(TaskBase):
    status_id: uuid.UUID
    assignee_ids: list[uuid.UUID] = []
    tag_names: list[str] = []


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    assignee_ids: list[uuid.UUID] | None = None
    tag_names: list[str] | None = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().lower()
        if clean not in ("urgent", "high", "medium", "low"):
            raise ValueError("Priority must be 'urgent', 'high', 'medium', or 'low'.")
        return clean


class TaskMove(BaseModel):
    destination_status_id: uuid.UUID
    prev_task_id: uuid.UUID | None = None
    next_task_id: uuid.UUID | None = None
    version: int = Field(..., description="Optimistic locking version")


class TagResponse(BaseModel):
    id: uuid.UUID
    name: str
    color_hex: str

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: uuid.UUID
    status_id: uuid.UUID
    task_number: int
    task_key: str | None = None
    title: str
    description: str | None = None
    priority: str
    rank: float
    version: int
    creator_id: uuid.UUID | None = None
    due_date: datetime | None = None
    created_at: datetime
    updated_at: datetime
    assignees: list[WorkspaceMemberUser] = []
    tags: list[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)


class BoardColumnResponse(BaseModel):
    status: TaskStatusResponse
    tasks: list[TaskResponse] = []


class BoardResponse(BaseModel):
    project_id: uuid.UUID
    columns: list[BoardColumnResponse] = []

