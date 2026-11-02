import time
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.core.redis import delete_grace_stash, get_grace_stash, get_user_revocation_epoch
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth import auth_service
from app.services.password import password_service


@pytest.mark.asyncio
async def test_refresh_rotation_happy_path(db_session):
    # 1. Create active user
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=password_service.hash_password("Password123!"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # 2. Create initial session
    token_rec, raw_r1 = await auth_service.create_session(db_session, user.id)
    await db_session.commit()

    # 3. Rotate R1 -> R2 (Branch A)
    raw_r2, access_token, user_out, family_id = await auth_service.rotate_refresh_token(
        db=db_session,
        raw_token_in=raw_r1,
    )

    assert raw_r2 != raw_r1
    assert access_token is not None
    assert family_id == token_rec.family_id

    # Check R1 is now revoked and points to R2
    await db_session.refresh(token_rec)
    assert token_rec.is_revoked is True
    assert token_rec.replaced_by is not None

    # Check Redis grace stash contains R2
    cached = await get_grace_stash(str(family_id))
    assert cached is not None


@pytest.mark.asyncio
async def test_refresh_grace_window_redis_hit(db_session):
    """Sibling tab presents R1 within 15s grace window -> Redis Hit returns R2 without new DB mutation."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=password_service.hash_password("Password123!"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token_rec, raw_r1 = await auth_service.create_session(db_session, user.id)
    await db_session.commit()

    # Tab 1 rotates R1 -> R2
    raw_r2, _, _, family_id = await auth_service.rotate_refresh_token(
        db=db_session,
        raw_token_in=raw_r1,
    )

    # Count tokens in family
    stmt = select(RefreshToken).where(RefreshToken.family_id == family_id)
    tokens_before = (await db_session.execute(stmt)).scalars().all()
    assert len(tokens_before) == 2  # R1 and R2

    # Tab 2 presents R1 within grace window (e.g. 1 second later)
    raw_recovered, access_token, _, _ = await auth_service.rotate_refresh_token(
        db=db_session,
        raw_token_in=raw_r1,
    )

    # Recovered token must be identical to R2
    assert raw_recovered == raw_r2
    assert access_token is not None

    # Verify no new tokens were inserted in DB (zero split-brain)
    tokens_after = (await db_session.execute(stmt)).scalars().all()
    assert len(tokens_after) == 2


@pytest.mark.asyncio
async def test_refresh_grace_window_redis_miss_atomic_sub_rotation(db_session):
    """Sibling tab presents R1 within 15s grace, but Redis grace stash is deleted (outage) -> Atomic Sub-Rotation."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=password_service.hash_password("Password123!"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token_rec, raw_r1 = await auth_service.create_session(db_session, user.id)
    await db_session.commit()

    # Tab 1 rotates R1 -> R2
    raw_r2, _, _, family_id = await auth_service.rotate_refresh_token(
        db=db_session,
        raw_token_in=raw_r1,
    )

    # Simulate Redis miss / outage by clearing grace stash
    await delete_grace_stash(str(family_id))

    # Tab 2 presents R1 within 15s -> Redis miss triggers atomic sub-rotation R2 -> R3
    raw_r3, access_token, _, _ = await auth_service.rotate_refresh_token(
        db=db_session,
        raw_token_in=raw_r1,
    )

    assert raw_r3 != raw_r2
    assert raw_r3 != raw_r1

    # Invariant: exactly 1 active leaf token exists
    stmt = select(RefreshToken).where(RefreshToken.family_id == family_id, RefreshToken.is_revoked == False)
    active_tokens = (await db_session.execute(stmt)).scalars().all()
    assert len(active_tokens) == 1
    assert auth_service.hash_token(raw_r3) == active_tokens[0].token_hash


@pytest.mark.asyncio
async def test_refresh_replay_attack_revocation(db_session):
    """Presenting a rotated token after 15s grace window triggers complete family revocation & security audit log."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=password_service.hash_password("Password123!"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token_rec, raw_r1 = await auth_service.create_session(db_session, user.id)
    await db_session.commit()

    # Rotate R1 -> R2
    raw_r2, _, _, family_id = await auth_service.rotate_refresh_token(
        db=db_session,
        raw_token_in=raw_r1,
    )

    # Artificially set rotated_at to 30 seconds ago (outside 15s grace)
    past_time = datetime.now(timezone.utc) - timedelta(seconds=30)
    await db_session.refresh(token_rec)
    token_rec.rotated_at = past_time
    await db_session.commit()

    # Attacker replays R1
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.rotate_refresh_token(
            db=db_session,
            raw_token_in=raw_r1,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "REFRESH_TOKEN_REPLAY_DETECTED"

    # Verify all tokens in family are now revoked
    stmt = select(RefreshToken).where(RefreshToken.family_id == family_id)
    family_tokens = (await db_session.execute(stmt)).scalars().all()
    assert all(t.is_revoked for t in family_tokens)

    # Verify audit log recorded
    audit_stmt = select(AuditLog).where(
        AuditLog.event_name == "auth.token_family_revoked_replay_detected",
        AuditLog.actor_id == user.id,
    )
    audit = (await db_session.execute(audit_stmt)).scalars().first()
    assert audit is not None
    assert audit.payload["family_id"] == str(family_id)

    # Verify user revocation epoch was set in Redis
    epoch = await get_user_revocation_epoch(str(user.id))
    assert epoch is not None

