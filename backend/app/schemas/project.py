import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

KEY_REGEX = re.compile(r"^[A-Z0-9]{2,10}$")


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    key: str = Field(..., min_length=2, max_length=10)
    description: str | None = None
    lead_id: uuid.UUID | None = None
    is_private: bool = False

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        clean = v.strip().upper()
        if not KEY_REGEX.match(clean):
            raise ValueError("Project key must be 2 to 10 uppercase alphanumeric characters (e.g. 'NEX', 'ENG1').")
        return clean


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    lead_id: uuid.UUID | None = None
    is_private: bool | None = None
    status: str | None = Field(None, description="'active', 'archived', 'completed'")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().lower()
        if clean not in ("active", "archived", "completed"):
            raise ValueError("Status must be 'active', 'archived', or 'completed'.")
        return clean


class ProjectResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    key: str
    description: str | None = None
    lead_id: uuid.UUID | None = None
    task_counter: int = 0
    is_private: bool = False
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    tasks_count: int = 0

    model_config = ConfigDict(from_attributes=True)
