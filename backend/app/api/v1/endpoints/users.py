import logging
import uuid
from typing import Annotated, List
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import APIResponse, SessionResponse
from app.schemas.user import UserResponse, UserUpdate
from app.services.auth import auth_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get Current User Profile",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieves profile of the currently authenticated user."""
    return APIResponse(data=UserResponse.model_validate(current_user))


@router.patch(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Update Current User Profile",
)
async def update_me(
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Updates profile attributes for the authenticated user."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip() if payload.avatar_url else None
    if payload.bio is not None:
        current_user.bio = payload.bio.strip() if payload.bio else None

    await db.commit()
    await db.refresh(current_user)
    return APIResponse(data=UserResponse.model_validate(current_user))


@router.get(
    "/me/sessions",
    response_model=APIResponse[List[SessionResponse]],
    summary="List Active User Sessions",
)
async def list_sessions(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists all active device session families for the authenticated user."""
    # Identify caller's active family from cookie if present
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    current_family_id = None
    if raw_token:
        token_hash = auth_service.hash_token(raw_token)
        from sqlalchemy import select
        from app.models.refresh_token import RefreshToken
        res = await db.execute(select(RefreshToken.family_id).where(RefreshToken.token_hash == token_hash))
        current_family_id = res.scalar_one_or_none()

    sessions = await auth_service.list_sessions(db, current_user.id, current_family_id=current_family_id)
    return APIResponse(data=[SessionResponse(**s) for s in sessions])


@router.delete(
    "/me/sessions/{family_id}",
    response_model=APIResponse[dict],
    summary="Terminate User Session",
)
async def delete_session(
    family_id: uuid.UUID,
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Terminates a specific device session family."""
    revoked = await auth_service.revoke_session(db, family_id, current_user.id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SESSION_NOT_FOUND",
        )

    # If the user revoked their own current session, clear their cookie
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    if raw_token:
        token_hash = auth_service.hash_token(raw_token)
        from sqlalchemy import select
        from app.models.refresh_token import RefreshToken
        res = await db.execute(select(RefreshToken.family_id).where(RefreshToken.token_hash == token_hash))
        curr_fam = res.scalar_one_or_none()
        if curr_fam == family_id:
            response.delete_cookie(
                key=settings.refresh_cookie_name,
                path="/",
                secure=settings.refresh_cookie_secure,
                httponly=True,
                samesite="lax",
            )

    return APIResponse(data={"message": "Session terminated successfully"})
