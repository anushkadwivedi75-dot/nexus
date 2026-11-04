import uuid
from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


@dataclass
class ProjectContext:
    workspace: Workspace
    workspace_member: WorkspaceMember
    project: Project
    current_user: User
    is_project_member: bool

    @property
    def can_manage_project(self) -> bool:
        return (
            self.workspace_member.role in ("owner", "admin")
            or self.project.lead_id == self.current_user.id
        )


async def get_project_context(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectContext:
    """
    Authoritative project boundary dependency.
    Resolves project, verifies workspace membership, and enforces private-project access.
    """
    # 1. Fetch active project
    stmt = select(Project).where(
        Project.id == project_id,
        Project.deleted_at.is_(None),
    )
    res = await db.execute(stmt)
    project = res.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    # 2. Fetch workspace & workspace membership
    ws_stmt = select(Workspace).where(Workspace.id == project.workspace_id)
    ws_res = await db.execute(ws_stmt)
    workspace = ws_res.scalars().first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated workspace not found.",
        )

    mem_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == current_user.id,
    )
    mem_res = await db.execute(mem_stmt)
    ws_member = mem_res.scalars().first()

    if not ws_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of the project's workspace.",
        )

    # 3. Check project membership
    pm_stmt = select(ProjectMember).where(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == current_user.id,
    )
    pm_res = await db.execute(pm_stmt)
    is_proj_member = pm_res.scalars().first() is not None

    # 4. Enforce private project visibility
    if project.is_private:
        is_elevated = ws_member.role in ("owner", "admin") or project.lead_id == current_user.id
        if not is_elevated and not is_proj_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access this private project.",
            )

    return ProjectContext(
        workspace=workspace,
        workspace_member=ws_member,
        project=project,
        current_user=current_user,
        is_project_member=is_proj_member,
    )


async def require_project_access(
    ctx: Annotated[ProjectContext, Depends(get_project_context)],
) -> ProjectContext:
    """Ensures caller has permission to view and interact with the project."""
    return ctx


async def require_project_manager(
    ctx: Annotated[ProjectContext, Depends(get_project_context)],
) -> ProjectContext:
    """Ensures caller is Project Lead, Workspace Admin, or Workspace Owner."""
    if not ctx.can_manage_project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: Project Lead, Workspace Admin, or Workspace Owner required.",
        )
    return ctx

