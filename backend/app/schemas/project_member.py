import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.workspace_member import WorkspaceMemberUser


class ProjectMemberAdd(BaseModel):
    user_id: uuid.UUID


class ProjectMemberResponse(BaseModel):
    project_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime
    user: WorkspaceMemberUser | None = None

    model_config = ConfigDict(from_attributes=True)

