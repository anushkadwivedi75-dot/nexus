from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.auth import APIResponse
from app.schemas.workspace_invitation import InvitationAccept
from app.services.workspace_invitation import workspace_invitation_service

router = APIRouter()


@router.post(
    "/accept",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Accept Workspace Invitation",
)
async def accept_invitation(
    body: InvitationAccept,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Atomically validates an invitation token and adds caller to workspace_members.
    """
    workspace, member = await workspace_invitation_service.accept_invitation(
        db=db,
        raw_token=body.token,
        user=current_user,
    )
    return APIResponse(
        data={
            "message": "Invitation accepted successfully.",
            "workspace": {
                "id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
            },
            "membership": {
                "id": str(member.id),
                "role": member.role,
                "joined_at": member.joined_at.isoformat(),
            },
        }
    )

