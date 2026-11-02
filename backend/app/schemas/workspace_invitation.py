import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.user import EmailType


class InvitationCreate(BaseModel):
    email: EmailType
    role: str = Field("member", description="Role to grant: 'admin' or 'member'")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        role = v.strip().lower()
        if role == "owner":
            raise ValueError("CANNOT_INVITE_AS_OWNER: Workspaces can have only one owner. Transfer ownership after joining.")
        if role not in ("admin", "member"):
            raise ValueError("Role must be 'admin' or 'member'.")
        return role


class InvitationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    role: str
    status: str
    invited_by: uuid.UUID | None = None
    expires_at: datetime
    created_at: datetime
    raw_token: str | None = None
    invite_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    token: str = Field(..., min_length=16, description="Cryptographic invitation token")

