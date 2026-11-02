import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemberRoleUpdate(BaseModel):
    role: str = Field(..., description="Role to assign: 'admin' or 'member'")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        role = v.strip().lower()
        if role == "owner":
            raise ValueError("CANNOT_ASSIGN_OWNER_VIA_ROLE_UPDATE: Use the dedicated ownership transfer endpoint.")
        if role not in ("admin", "member"):
            raise ValueError("Role must be either 'admin' or 'member'.")
        return role


class WorkspaceMemberUser(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    user: WorkspaceMemberUser | None = None

    model_config = ConfigDict(from_attributes=True)

