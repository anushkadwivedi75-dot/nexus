import logging
import uuid
from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, verify_csrf_and_origin
from app.models.user import User
from app.schemas.auth import (
    APIResponse,
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth import auth_service
from app.services.password import password_service
from app.services.token import token_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _set_refresh_cookie(response: Response, raw_token: str):
    """Sets the HTTP-only refresh cookie adhering to RFC 6265bis and Section 6.1."""
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        expires=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/",
        domain=None,  # Mandated by RFC 6265bis for __Host- prefix
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response):
    """Clears the refresh cookie."""
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/",
        domain=None,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=APIResponse[AuthResponse],
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Registers a new user account with Argon2id password hashing."""
    normalized_email = payload.email.lower().strip()

    # Check email uniqueness (uq_users_email_lower)
    stmt = select(User).where(func.lower(User.email) == normalized_email)
    existing_user = (await db.execute(stmt)).scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="EMAIL_ALREADY_EXISTS",
        )

    # Hash password with Argon2id
    hashed_pwd = password_service.hash_password(payload.password)

    new_user = User(
        id=uuid.uuid4(),
        email=normalized_email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name.strip(),
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Create initial refresh token session
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    _, raw_refresh_token = await auth_service.create_session(
        db=db,
        user_id=new_user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    await db.commit()
    await db.refresh(new_user)

    # Issue access token and set refresh cookie
    access_token = token_service.create_access_token(str(new_user.id), new_user.email)
    _set_refresh_cookie(response, raw_refresh_token)

    return APIResponse(
        data=AuthResponse(
            user=UserResponse.model_validate(new_user),
            access_token=access_token,
        )
    )


@router.post(
    "/login",
    response_model=APIResponse[AuthResponse],
    status_code=status.HTTP_200_OK,
    summary="User Login",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticates credentials using Argon2id and issues a new session family."""
    normalized_email = payload.email.lower().strip()

    stmt = select(User).where(func.lower(User.email) == normalized_email)
    user = (await db.execute(stmt)).scalars().first()

    # Mitigate user enumeration side-channels
    if not user or not user.is_active:
        password_service.verify_dummy()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
        )

    if not password_service.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Create new session family
    _, raw_refresh_token = await auth_service.create_session(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    await db.commit()

    access_token = token_service.create_access_token(str(user.id), user.email)
    _set_refresh_cookie(response, raw_refresh_token)

    return APIResponse(
        data=AuthResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token,
        )
    )


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_csrf_and_origin)],
    summary="Rotate Refresh Token",
)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Rotates the refresh token using the concurrency-safe 15-second grace chain protocol (Section 6.4).
    Reads refresh token from HTTP-only cookie.
    """
    raw_token_in = request.cookies.get(settings.refresh_cookie_name)
    if not raw_token_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MISSING_REFRESH_COOKIE",
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        raw_token_out, access_token, user, _ = await auth_service.rotate_refresh_token(
            db=db,
            raw_token_in=raw_token_in,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except HTTPException:
        _clear_refresh_cookie(response)
        raise

    _set_refresh_cookie(response, raw_token_out)

    return APIResponse(
        data=TokenResponse(access_token=access_token)
    )


@router.post(
    "/logout",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_csrf_and_origin)],
    summary="Logout Active Session",
)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Terminates the current refresh token family and clears the cookie."""
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    if raw_token:
        token_hash = auth_service.hash_token(raw_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        token_rec = (await db.execute(stmt)).scalars().first()
        if token_rec:
            await auth_service.revoke_session(db, token_rec.family_id, token_rec.user_id)

    _clear_refresh_cookie(response)
    return APIResponse(data={"message": "Successfully logged out"})


@router.post(
    "/revoke-all-sessions",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Revoke All User Sessions",
)
async def revoke_all_sessions(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Terminates all session families for the caller and invalidates access tokens via Redis epoch."""
    revoked_count = await auth_service.revoke_all_sessions(db, current_user.id)
    _clear_refresh_cookie(response)
    return APIResponse(data={"message": "All sessions revoked", "count": revoked_count})
