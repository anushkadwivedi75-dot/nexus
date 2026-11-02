import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.workspace_context import (
    WorkspaceContext,
    require_workspace_admin,
    require_workspace_member,
    require_workspace_owner,
)
from app.models.user import User
from app.schemas.auth import APIResponse
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceTransferOwnership,
    WorkspaceUpdate,
)
from app.schemas.workspace_invitation import (
    InvitationCreate,
    InvitationResponse,
)
from app.schemas.workspace_member import (
    MemberRoleUpdate,
    WorkspaceMemberResponse,
)
from app.services.workspace import workspace_service
from app.services.workspace_invitation import workspace_invitation_service
from app.services.workspace_member import workspace_member_service

router = APIRouter()


# =============================================================================
# Workspace Management Endpoints
# =============================================================================

@router.post(
    "",
    response_model=APIResponse[WorkspaceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace",
)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Atomically creates a workspace and assigns the creator role='owner'.
    Satisfies uq_workspace_single_owner and enforces exactly one owner.
    """
    workspace, _ = await workspace_service.create_workspace(db, current_user, data)
    resp = WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        logo_url=workspace.logo_url,
        owner_id=workspace.owner_id,
        role="owner",
        members_count=1,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )
    return APIResponse(data=resp)


@router.get(
    "",
    response_model=APIResponse[List[WorkspaceResponse]],
    status_code=status.HTTP_200_OK,
    summary="List User Workspaces",
)
async def list_workspaces(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists all workspaces the authenticated user belongs to."""
    workspaces = await workspace_service.list_user_workspaces(db, current_user.id)
    return APIResponse(data=workspaces)


@router.get(
    "/{workspace_id}",
    response_model=APIResponse[WorkspaceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Workspace Details",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Returns workspace details and caller's role."""
    details = await workspace_service.get_workspace_details(db, workspace_id, ctx.current_user.id)
    return APIResponse(data=details)


@router.patch(
    "/{workspace_id}",
    response_model=APIResponse[WorkspaceResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Workspace",
)
async def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Updates workspace metadata (name, slug, logo_url). Authorized for Admin and Owner."""
    updated = await workspace_service.update_workspace(db, ctx.workspace, data, ctx.current_user)
    details = await workspace_service.get_workspace_details(db, workspace_id, ctx.current_user.id)
    return APIResponse(data=details)


@router.delete(
    "/{workspace_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete Workspace",
)
async def delete_workspace(
    workspace_id: uuid.UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Deletes workspace. Authorized for Owner only. Cascades child records."""
    await workspace_service.delete_workspace(db, workspace_id, ctx.current_user.id, ctx.current_user)
    return APIResponse(data={"message": "Workspace deleted successfully."})


@router.post(
    "/{workspace_id}/transfer-ownership",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Transfer Workspace Ownership",
)
async def transfer_ownership(
    workspace_id: uuid.UUID,
    body: WorkspaceTransferOwnership,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Dedicated atomic 8-step SQL transaction to transfer workspace ownership.
    Demotes current owner to admin first, promotes target to owner second.
    """
    res = await workspace_service.transfer_ownership(
        db=db,
        workspace_id=workspace_id,
        current_owner_id=ctx.current_user.id,
        new_owner_id=body.new_owner_id,
        actor=ctx.current_user,
    )
    return APIResponse(data=res)


# =============================================================================
# Team Membership Management Endpoints
# =============================================================================

@router.get(
    "/{workspace_id}/members",
    response_model=APIResponse[List[WorkspaceMemberResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Workspace Members",
)
async def list_members(
    workspace_id: uuid.UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists workspace members with public profiles and roles. Excludes sensitive auth fields."""
    members = await workspace_member_service.list_members(db, workspace_id)
    return APIResponse(data=members)


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=APIResponse[WorkspaceMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Member Role",
)
async def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    body: MemberRoleUpdate,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Updates a member's role to 'admin' or 'member'.
    Rejects setting or modifying 'owner' role.
    """
    member = await workspace_member_service.update_member_role(
        db=db,
        workspace=ctx.workspace,
        target_user_id=user_id,
        new_role=body.role,
        actor=ctx.current_user,
        actor_role=ctx.membership.role,
    )
    # Return updated member representation
    members = await workspace_member_service.list_members(db, workspace_id)
    updated_repr = next((m for m in members if m["user_id"] == user_id), None)
    return APIResponse(data=updated_repr)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Remove Workspace Member",
)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Removes a member from the workspace.
    Supports Admin/Owner removal and voluntary self-removal.
    Rejects owner removal under any condition.
    """
    await workspace_member_service.remove_member(
        db=db,
        workspace=ctx.workspace,
        target_user_id=user_id,
        actor=ctx.current_user,
        actor_role=ctx.membership.role,
    )
    return APIResponse(data={"message": "Member removed successfully."})


# =============================================================================
# Invitation Management Endpoints
# =============================================================================

@router.post(
    "/{workspace_id}/invitations",
    response_model=APIResponse[InvitationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace Invitation",
)
async def create_invitation(
    workspace_id: uuid.UUID,
    body: InvitationCreate,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Creates a cryptographic invitation token for joining the workspace."""
    invitation, raw_token = await workspace_invitation_service.create_invitation(
        db=db,
        workspace=ctx.workspace,
        email=body.email,
        role=body.role,
        inviter=ctx.current_user,
    )
    resp = InvitationResponse(
        id=invitation.id,
        workspace_id=invitation.workspace_id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        invited_by=invitation.invited_by,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        raw_token=raw_token,
        invite_url=f"/invite/{raw_token}",
    )
    return APIResponse(data=resp)


@router.get(
    "/{workspace_id}/invitations",
    response_model=APIResponse[List[InvitationResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Workspace Invitations",
)
async def list_invitations(
    workspace_id: uuid.UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists pending invitations for the workspace."""
    invitations = await workspace_invitation_service.list_invitations(db, workspace_id)
    return APIResponse(data=invitations)


@router.post(
    "/{workspace_id}/invitations/{invitation_id}/revoke",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Revoke Workspace Invitation",
)
async def revoke_invitation(
    workspace_id: uuid.UUID,
    invitation_id: uuid.UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revokes a pending workspace invitation."""
    await workspace_invitation_service.revoke_invitation(
        db=db,
        workspace=ctx.workspace,
        invitation_id=invitation_id,
        actor=ctx.current_user,
    )
    return APIResponse(data={"message": "Invitation revoked successfully."})

