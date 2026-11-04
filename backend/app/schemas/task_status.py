import re
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

COLOR_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class TaskStatusBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color_hex: str = Field("#6366F1", max_length=7)
    is_completed_state: bool = False

    @field_validator("color_hex")
    @classmethod
    def validate_color_hex(cls, v: str) -> str:
        clean = v.strip().upper()
        if not COLOR_REGEX.match(clean):
            raise ValueError("Color must be a valid 6-character hex code (e.g. '#6366F1').")
        return clean


class TaskStatusCreate(TaskStatusBase):
    pass


class TaskStatusUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    color_hex: str | None = Field(None, max_length=7)
    rank: float | None = None
    is_completed_state: bool | None = None

    @field_validator("color_hex")
    @classmethod
    def validate_color_hex(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().upper()
        if not COLOR_REGEX.match(clean):
            raise ValueError("Color must be a valid 6-character hex code (e.g. '#6366F1').")
        return clean


class TaskStatusDelete(BaseModel):
    fallback_status_id: uuid.UUID


class TaskStatusResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: uuid.UUID
    name: str
    rank: float
    color_hex: str
    is_completed_state: bool

    model_config = ConfigDict(from_attributes=True)

