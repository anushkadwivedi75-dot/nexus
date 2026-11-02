import uuid
from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


@dataclass
class WorkspaceContext:
    workspace: Workspace
    membership: WorkspaceMember
    current_user: User

    @property
    def is_owner(self) -> bool:
        return self.membership.role == "owner" and self.workspace.owner_id == self.current_user.id

    @property
    def is_admin(self) -> bool:
        return self.membership.role in ("owner", "admin")

    @property
    def role(self) -> str:
        return self.membership.role


async def get_workspace_context(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceContext:
    """
    Authoritative tenant boundary dependency.
    Resolves the requested workspace, validates active membership, and injects context.
    Rejects nonexistent or unauthorized access before business queries execute.
    """
    # 1. Fetch workspace
    ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
    ws_res = await db.execute(ws_stmt)
    workspace = ws_res.scalars().first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    # 2. Fetch membership
    mem_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id,
    )
    mem_res = await db.execute(mem_stmt)
    membership = mem_res.scalars().first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this workspace.",
        )

    return WorkspaceContext(
        workspace=workspace,
        membership=membership,
        current_user=current_user,
    )


async def require_workspace_member(
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
) -> WorkspaceContext:
    """Ensures the caller has at least active member-level access."""
    return ctx


async def require_workspace_admin(
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
) -> WorkspaceContext:
    """Ensures the caller has admin or owner privileges within the workspace."""
    if not ctx.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: Workspace Admin or Owner required.",
        )
    return ctx


async def require_workspace_owner(
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
) -> WorkspaceContext:
    """Ensures the caller is the authoritative workspace owner."""
    if not ctx.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: Workspace Owner required.",
        )
    return ctx

