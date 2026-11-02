import time
import uuid
import jwt
import pytest
from app.core.config import settings
from app.core.redis import set_user_revocation_epoch
from app.services.token import token_service


@pytest.mark.asyncio
async def test_access_token_creation_and_validation():
    user_id = str(uuid.uuid4())
    email = "test@example.com"

    token = token_service.create_access_token(user_id, email)
    assert token is not None

    payload = await token_service.verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE


@pytest.mark.asyncio
async def test_access_token_invalid_signature():
    user_id = str(uuid.uuid4())
    email = "test@example.com"
    token = jwt.encode(
        {"sub": user_id, "email": email, "exp": int(time.time()) + 900, "iat": int(time.time()), "iss": "nexus-api", "aud": "nexus-web"},
        "wrong_signing_key_12345",
        algorithm="HS256",
    )
    payload = await token_service.verify_access_token(token)
    assert payload is None


@pytest.mark.asyncio
async def test_access_token_revocation_epoch():
    user_id = str(uuid.uuid4())
    email = "revoked@example.com"

    # Issue token at T0
    token = token_service.create_access_token(user_id, email)
    assert await token_service.verify_access_token(token) is not None

    # User revokes session at T0 + 2
    epoch_timestamp = int(time.time()) + 2
    await set_user_revocation_epoch(user_id, epoch_timestamp, ttl=900)

    # Verification must fail because token iat < epoch
    payload = await token_service.verify_access_token(token)
    assert payload is None
