import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.workspace_context import WorkspaceContext, get_workspace_context
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.auth import APIResponse
from app.schemas.comment import (
    CommentCreate,
    CommentCursorPagination,
    CommentResponse,
    CommentUpdate,
)
from app.services.comment import CommentService

router = APIRouter()


async def get_task_context(
    task_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Task, WorkspaceContext]:
    stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    res = await db.execute(stmt)
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    ws_ctx = await get_workspace_context(
        workspace_id=task.workspace_id,
        current_user=current_user,
        db=db,
    )
    return task, ws_ctx


async def get_comment_context(
    comment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Comment, WorkspaceContext]:
    stmt = select(Comment).where(Comment.id == comment_id)
    res = await db.execute(stmt)
    comment = res.scalars().first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

    ws_ctx = await get_workspace_context(
        workspace_id=comment.workspace_id,
        current_user=current_user,
        db=db,
    )
    return comment, ws_ctx


@router.post(
    "/tasks/{task_id}/comments",
    response_model=APIResponse[CommentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Task Comment or Reply",
)
async def create_comment(
    task_id: uuid.UUID,
    data: CommentCreate,
    ctx_tuple: Annotated[tuple[Task, WorkspaceContext], Depends(get_task_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    task, ws_ctx = ctx_tuple
    comment = await CommentService.create_comment(
        db=db,
        workspace_id=ws_ctx.workspace.id,
        task_id=task.id,
        author=ws_ctx.current_user,
        user_role=ws_ctx.role,
        data=data,
    )
    return APIResponse(success=True, data=comment)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=APIResponse[CommentCursorPagination],
    summary="List Task Comments",
)
async def list_comments(
    task_id: uuid.UUID,
    ctx_tuple: Annotated[tuple[Task, WorkspaceContext], Depends(get_task_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    cursor: Optional[str] = Query(None, description="Cursor for pagination (encoded created_at,id)"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
):
    task, ws_ctx = ctx_tuple
    pagination = await CommentService.list_comments(
        db=db,
        workspace_id=ws_ctx.workspace.id,
        task_id=task.id,
        current_user=ws_ctx.current_user,
        user_role=ws_ctx.role,
        cursor=cursor,
        limit=limit,
    )
    return APIResponse(success=True, data=pagination)


@router.patch(
    "/comments/{comment_id}",
    response_model=APIResponse[CommentResponse],
    summary="Update Comment",
)
async def update_comment(
    comment_id: uuid.UUID,
    data: CommentUpdate,
    ctx_tuple: Annotated[tuple[Comment, WorkspaceContext], Depends(get_comment_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    comment, ws_ctx = ctx_tuple
    updated = await CommentService.update_comment(
        db=db,
        workspace_id=ws_ctx.workspace.id,
        comment_id=comment.id,
        current_user=ws_ctx.current_user,
        data=data,
    )
    return APIResponse(success=True, data=updated)


@router.delete(
    "/comments/{comment_id}",
    response_model=APIResponse[dict],
    summary="Delete Comment",
)
async def delete_comment(
    comment_id: uuid.UUID,
    ctx_tuple: Annotated[tuple[Comment, WorkspaceContext], Depends(get_comment_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    comment, ws_ctx = ctx_tuple
    await CommentService.delete_comment(
        db=db,
        workspace_id=ws_ctx.workspace.id,
        comment_id=comment.id,
        current_user=ws_ctx.current_user,
        user_role=ws_ctx.role,
    )
    return APIResponse(success=True, data={"deleted": True, "comment_id": str(comment.id)})

