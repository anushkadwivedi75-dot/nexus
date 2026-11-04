import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.project_context import (
    ProjectContext,
    require_project_access,
    require_project_manager,
)
from app.core.security import get_current_active_user
from app.core.workspace_context import (
    WorkspaceContext,
    require_workspace_admin,
    require_workspace_member,
)
from app.models.user import User
from app.schemas.auth import APIResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.schemas.project_member import (
    ProjectMemberAdd,
    ProjectMemberResponse,
)
from app.schemas.task import (
    BoardResponse,
    TaskResponse,
)
from app.schemas.task_status import (
    TaskStatusCreate,
    TaskStatusDelete,
    TaskStatusResponse,
    TaskStatusUpdate,
)
from app.services.project import project_service
from app.services.project_member import project_member_service
from app.services.task import task_service
from app.services.task_status import task_status_service

router = APIRouter()


# =============================================================================
# Workspace-Scoped Project Endpoints
# =============================================================================

@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=APIResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
)
async def create_project(
    workspace_id: uuid.UUID,
    data: ProjectCreate,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Creates a project within the workspace, seeds default status columns,
    and initializes the atomic 64-bit task counter.
    """
    project = await project_service.create_project(
        db=db,
        workspace_id=workspace_id,
        creator=ctx.current_user,
        data=data,
    )
    return APIResponse(data=project)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=APIResponse[List[ProjectResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Workspace Projects",
)
async def list_workspace_projects(
    workspace_id: uuid.UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists accessible projects in the workspace, enforcing private project visibility."""
    projects = await project_service.list_workspace_projects(
        db=db,
        workspace_id=workspace_id,
        user_id=ctx.current_user.id,
        ws_role=ctx.membership.role,
    )
    return APIResponse(data=projects)


# =============================================================================
# Project-Scoped Management Endpoints
# =============================================================================

@router.get(
    "/projects/{project_id}",
    response_model=APIResponse[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Project Details",
)
async def get_project(
    project_id: uuid.UUID,
    ctx: Annotated[ProjectContext, Depends(require_project_access)],
):
    """Returns project details after validating workspace membership and private project access."""
    return APIResponse(data=ctx.project)


@router.patch(
    "/projects/{project_id}",
    response_model=APIResponse[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Project",
)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    ctx: Annotated[ProjectContext, Depends(require_project_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Updates project metadata. Authorized for Project Lead, Workspace Admin, or Owner."""
    updated = await project_service.update_project(db, ctx.project, data, ctx.current_user)
    return APIResponse(data=updated)


@router.delete(
    "/projects/{project_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete Project",
)
async def delete_project(
    project_id: uuid.UUID,
    ctx: Annotated[ProjectContext, Depends(require_project_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Soft deletes the project and all child tasks."""
    await project_service.delete_project(db, ctx.project, ctx.current_user)
    return APIResponse(data={"message": "Project deleted successfully."})


# =============================================================================
# Private Project Membership Endpoints
# =============================================================================

@router.get(
    "/projects/{project_id}/members",
    response_model=APIResponse[List[ProjectMemberResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Project Members",
)
async def list_project_members(
    project_id: uuid.UUID,
    ctx: Annotated[ProjectContext, Depends(require_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists members explicitly added to this private project."""
    members = await project_member_service.list_members(db, project_id)
    return APIResponse(data=members)


@router.post(
    "/projects/{project_id}/members",
    response_model=APIResponse[ProjectMemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Project Member",
)
async def add_project_member(
    project_id: uuid.UUID,
    body: ProjectMemberAdd,
    ctx: Annotated[ProjectContext, Depends(require_project_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Adds a workspace member to the private project."""
    member = await project_member_service.add_member(
        db=db,
        workspace_id=ctx.workspace.id,
        project_id=project_id,
        user_id=body.user_id,
    )
    return APIResponse(data=member)


@router.delete(
    "/projects/{project_id}/members/{user_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Remove Project Member",
)
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    ctx: Annotated[ProjectContext, Depends(require_project_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Removes a member from the private project."""
    await project_member_service.remove_member(db, project_id, user_id)
    return APIResponse(data={"message": "Member removed from project successfully."})


# =============================================================================
# Custom Status Column Endpoints
# =============================================================================

@router.get(
    "/projects/{project_id}/columns",
    response_model=APIResponse[List[TaskStatusResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Status Columns",
)
async def list_columns(
    project_id: uuid.UUID,
    ctx: Annotated[ProjectContext, Depends(require_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists active status columns in the project ordered by rank."""
    statuses = await task_status_service.list_statuses(db, project_id)
    return APIResponse(data=statuses)


@router.post(
    "/projects/{project_id}/columns",
    response_model=APIResponse[TaskStatusResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Status Column",
)
async def create_column(
    project_id: uuid.UUID,
    body: TaskStatusCreate,
    ctx: Annotated[ProjectContext, Depends(require_project_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Creates a custom workflow status column."""
    col = await task_status_service.create_status(
        db=db,
        workspace_id=ctx.workspace.id,
        project_id=project_id,
        data=body,
    )
    return APIResponse(data=col)


@router.patch(
    "/projects/{project_id}/columns/{column_id}",
    response_model=APIResponse[TaskStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Status Column",
)
async def update_column(
    project_id: uuid.UUID,
    column_id: uuid.UUID,
    body: TaskStatusUpdate,
    ctx: Annotated[ProjectContext, Depends(require_project_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Updates a status column name, color, rank, or completion state."""
    col = await task_status_service.update_status(
        db=db,
        status_id=column_id,
        project_id=project_id,
        data=body,
    )
    return APIResponse(data=col)


@router.delete(
    "/projects/{project_id}/columns/{column_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete Status Column",
)
async def delete_column(
    project_id: uuid.UUID,
    column_id: uuid.UUID,
    body: TaskStatusDelete,
    ctx: Annotated[ProjectContext, Depends(require_project_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Deletes a status column after safely remapping all active tasks to fallback_status_id."""
    await task_status_service.delete_status(
        db=db,
        status_id=column_id,
        project_id=project_id,
        fallback_status_id=body.fallback_status_id,
    )
    return APIResponse(data={"message": "Column deleted and tasks remapped successfully."})


# =============================================================================
# Board and Roadmap Endpoints
# =============================================================================

@router.get(
    "/projects/{project_id}/board",
    response_model=APIResponse[BoardResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Kanban Board",
)
async def get_board(
    project_id: uuid.UUID,
    ctx: Annotated[ProjectContext, Depends(require_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Returns complete Kanban board structure with status columns and cards."""
    board = await task_service.get_board(db, ctx.workspace.id, ctx.project)
    return APIResponse(data=board)


@router.get(
    "/projects/{project_id}/roadmap",
    response_model=APIResponse[List[TaskResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Project Roadmap",
)
async def get_roadmap(
    project_id: uuid.UUID,
    ctx: Annotated[ProjectContext, Depends(require_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Returns roadmap view tasks ordered by due date, priority, and rank."""
    roadmap = await task_service.get_roadmap(db, ctx.workspace.id, ctx.project)
    return APIResponse(data=roadmap)

