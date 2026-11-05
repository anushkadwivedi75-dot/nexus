import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.auth import APIResponse
from app.schemas.notification import (
    NotificationCursorPagination,
    NotificationReadAllRequest,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.services.notification import NotificationService

router = APIRouter()


@router.get(
    "/notifications",
    response_model=APIResponse[NotificationCursorPagination],
    status_code=status.HTTP_200_OK,
    summary="List In-App Notifications",
)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Optional[uuid.UUID] = Query(None, description="Filter by workspace ID"),
    is_read: Optional[bool] = Query(None, description="Filter by read/unread state"),
    include_archived: bool = Query(False, description="Whether to include archived items"),
    action_type: Optional[str] = Query(None, description="Filter by action type (e.g. comment_mention, task_assigned)"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
):
    """
    Retrieves cursor-paginated notifications for current user with batch-loaded actors.
    Supports filtering by workspace, read status, and action type.
    """
    pagination = await NotificationService.list_notifications(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id,
        is_read=is_read,
        include_archived=include_archived,
        action_type=action_type,
        cursor=cursor,
        limit=limit,
    )
    return APIResponse(data=pagination)


@router.get(
    "/notifications/unread-count",
    response_model=APIResponse[NotificationUnreadCountResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Unread Notification Count",
)
async def get_unread_count(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Optional[uuid.UUID] = Query(None, description="Optional workspace ID filter"),
):
    """
    Retrieves the aggregate unread, unarchived notification count for the current user.
    """
    count = await NotificationService.get_unread_count(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id,
    )
    return APIResponse(data=NotificationUnreadCountResponse(unread_count=count))


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=APIResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark Notification as Read",
)
async def mark_as_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Marks a specific notification as read and emits real-time update event.
    Guarantees tenant isolation: users can only mark their own notifications.
    """
    notif = await NotificationService.mark_as_read(
        db=db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    return APIResponse(data=notif)


@router.patch(
    "/notifications/{notification_id}/unread",
    response_model=APIResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark Notification as Unread",
)
async def mark_as_unread(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Reverts a notification back to unread state and emits real-time update event.
    """
    notif = await NotificationService.mark_as_unread(
        db=db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    return APIResponse(data=notif)


@router.post(
    "/notifications/read-all",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Mark All Notifications as Read",
)
async def mark_all_as_read(
    payload: NotificationReadAllRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Atomically marks all unread notifications for the user as read.
    Optionally scoped to a specific workspace.
    """
    updated_count = await NotificationService.mark_all_as_read(
        db=db,
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
    )
    return APIResponse(data={"updated_count": updated_count})


@router.post(
    "/notifications/{notification_id}/archive",
    response_model=APIResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Archive Notification",
)
async def archive_notification(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Archives a notification, removing it from default inbox view.
    """
    notif = await NotificationService.archive_notification(
        db=db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    return APIResponse(data=notif)
