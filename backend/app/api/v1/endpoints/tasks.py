import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.project_context import (
    ProjectContext,
    get_project_context,
    require_project_access,
)
from app.core.security import get_current_active_user
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.auth import APIResponse
from app.schemas.task import (
    TaskCreate,
    TaskMove,
    TaskResponse,
    TaskUpdate,
)
from app.services.task import task_service

router = APIRouter()


async def get_task_project_context(
    task_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Task, ProjectContext]:
    """Resolves task and validates caller has access to the enclosing project."""
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    res = await db.execute(stmt)
    task = res.scalars().first()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    ctx = await get_project_context(
        project_id=task.project_id,
        current_user=current_user,
        db=db,
    )
    return task, ctx


@router.post(
    "/projects/{project_id}/tasks",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Task",
)
async def create_task(
    project_id: uuid.UUID,
    data: TaskCreate,
    ctx: Annotated[ProjectContext, Depends(require_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Creates a new task in the project with monotonic 64-bit task numbering
    and fractional rank allocation.
    """
    task = await task_service.create_task(
        db=db,
        workspace_id=ctx.workspace.id,
        project=ctx.project,
        creator=ctx.current_user,
        data=data,
    )
    return APIResponse(data=task)


@router.get(
    "/tasks/{task_id}",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Task Details",
)
async def get_task(
    task_context: Annotated[tuple[Task, ProjectContext], Depends(get_task_project_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Returns task details, assignees, and tags."""
    task, ctx = task_context
    details = await task_service.get_task_details(
        db=db,
        workspace_id=ctx.workspace.id,
        project_id=ctx.project.id,
        task_id=task.id,
        project_key=ctx.project.key,
    )
    return APIResponse(data=details)


@router.patch(
    "/tasks/{task_id}",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Task",
)
async def update_task(
    data: TaskUpdate,
    task_context: Annotated[tuple[Task, ProjectContext], Depends(get_task_project_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Updates task fields with version increment and assignee/tag management."""
    task, ctx = task_context
    updated = await task_service.update_task(
        db=db,
        workspace_id=ctx.workspace.id,
        project_id=ctx.project.id,
        task_id=task.id,
        data=data,
        current_user=ctx.current_user,
    )
    return APIResponse(data=updated)


@router.delete(
    "/tasks/{task_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete Task",
)
async def delete_task(
    task_context: Annotated[tuple[Task, ProjectContext], Depends(get_task_project_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Soft deletes the task, excluding it from board and listing."""
    task, ctx = task_context
    await task_service.delete_task(
        db=db,
        workspace_id=ctx.workspace.id,
        project_id=ctx.project.id,
        task_id=task.id,
    )
    return APIResponse(data={"message": "Task deleted successfully."})


@router.patch(
    "/tasks/{task_id}/move",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Move Task (Kanban)",
)
async def move_task(
    move: TaskMove,
    task_context: Annotated[tuple[Task, ProjectContext], Depends(get_task_project_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Executes a deterministic Kanban card move under two-column status locks.
    Orders status locks by id ASC to eliminate AB-BA deadlocks.
    Allocates fractional indexing rank and rebalances if exhaustion occurs.
    """
    task, ctx = task_context
    moved = await task_service.move_task(
        db=db,
        workspace_id=ctx.workspace.id,
        project=ctx.project,
        task_id=task.id,
        move=move,
        current_user=ctx.current_user,
    )
    return APIResponse(data=moved)

