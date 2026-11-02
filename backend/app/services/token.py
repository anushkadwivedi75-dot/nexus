import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.core.config import settings
from app.core.redis import get_user_revocation_epoch

logger = logging.getLogger(__name__)


class TokenService:
    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """
        Issues a short-lived (15 min) JWT access token with required claims:
        sub, email, iat, exp, iss, aud.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return token

    @staticmethod
    async def verify_access_token(token: str) -> Dict[str, Any] | None:
        """
        Validates JWT signature, expiration, issuer, audience, and checks
        in-memory Redis user revocation epoch.
        Returns decoded claims dictionary or None if invalid/revoked.
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
                options={"require": ["sub", "exp", "iat", "iss", "aud"]},
            )
        except ExpiredSignatureError:
            logger.debug("Access token signature expired")
            return None
        except InvalidTokenError as e:
            logger.debug("Invalid access token: %s", e)
            return None

        user_id = payload.get("sub")
        token_iat = payload.get("iat")

        if not user_id or token_iat is None:
            return None

        # Check in-memory Redis revocation epoch (Section 6.5)
        revocation_epoch = await get_user_revocation_epoch(user_id)
        if revocation_epoch is not None and token_iat < revocation_epoch:
            logger.info("Access token for user %s revoked via revocation epoch (%s < %s)", user_id, token_iat, revocation_epoch)
            return None

        return payload


token_service = TokenService()
