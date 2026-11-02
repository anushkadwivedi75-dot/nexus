import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=2, max_length=120)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        clean = v.strip().lower()
        if not SLUG_REGEX.match(clean):
            raise ValueError(
                "Slug must contain only lowercase alphanumeric characters and single hyphens, with no leading or trailing hyphens."
            )
        return clean


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    slug: str | None = Field(None, min_length=2, max_length=120)
    logo_url: str | None = Field(None, max_length=512)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().lower()
        if not SLUG_REGEX.match(clean):
            raise ValueError(
                "Slug must contain only lowercase alphanumeric characters and single hyphens, with no leading or trailing hyphens."
            )
        return clean


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    owner_id: uuid.UUID
    role: str | None = None
    members_count: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceTransferOwnership(BaseModel):
    new_owner_id: uuid.UUID

