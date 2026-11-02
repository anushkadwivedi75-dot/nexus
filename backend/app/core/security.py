import logging
import uuid
from typing import Annotated
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.token import token_service

logger = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Validates Bearer JWT access token and verifies in-memory Redis revocation epoch.
    Returns the authenticated User model.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NOT_AUTHENTICATED",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = await token_service.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_EXPIRED_OR_REVOKED_TOKEN",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_TOKEN_PAYLOAD",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="USER_NOT_FOUND",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="USER_INACTIVE",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INACTIVE_USER",
        )
    return current_user


def verify_csrf_and_origin(
    request: Request,
    x_requested_with: Annotated[str | None, Header()] = None,
    x_nexus_client: Annotated[str | None, Header()] = None,
):
    """
    CSRF verification per Blueprint Section 6.2:
    1. Origin / Referer check against allowed origins.
    2. Mandatory custom header ('X-Requested-With' or 'X-Nexus-Client').
    """
    # 1. Origin inspection
    origin = request.headers.get("origin")
    if origin and origin not in settings.CORS_ORIGINS:
        logger.warning("CSRF violation: Invalid origin %s", origin)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INVALID_ORIGIN",
        )

    # 2. Mandatory Custom Header for cookie-authenticated mutating endpoints
    if not (x_requested_with == "XMLHttpRequest" or x_nexus_client == "web"):
        # For development flexibility allow standard testing if origin is explicitly trusted
        if not (origin in settings.CORS_ORIGINS and settings.DEBUG):
            logger.warning("CSRF violation: Missing custom header")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="MISSING_ANTI_CSRF_HEADER",
            )

