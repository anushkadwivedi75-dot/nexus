import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.redis import (
    delete_grace_stash,
    get_grace_stash,
    set_grace_stash,
    set_user_revocation_epoch,
)
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.crypto import crypto_service
from app.services.token import token_service

logger = logging.getLogger(__name__)

GRACE_PERIOD_SECONDS = 15


class AuthService:
    @staticmethod
    def generate_raw_token() -> str:
        """Generates a cryptographically secure 256-bit URL-safe token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Computes the SHA-256 digest of a raw token."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    async def create_session(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        family_id: uuid.UUID | None = None,
    ) -> Tuple[RefreshToken, str]:
        """Creates a new refresh token session record."""
        raw_token = cls.generate_raw_token()
        token_hash = cls.hash_token(raw_token)
        session_family_id = family_id or uuid.uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_record = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            family_id=session_family_id,
            is_revoked=False,
            expires_at=expires_at,
            created_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(token_record)
        await db.flush()
        return token_record, raw_token

    @classmethod
    async def rotate_refresh_token(
        cls,
        db: AsyncSession,
        raw_token_in: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Tuple[str, str, User, uuid.UUID]:
        """
        Rotates a refresh token implementing Section 6.4:
        - Branch A: Unrotated token -> commit-first DB rotation + post-commit AES-256-GCM Redis grace stash.
        - Branch B: Rotated within 15s grace -> traverse chain to leaf, check Redis stash or execute atomic sub-rotation.
        - Branch C: Replayed >= 15s -> family revocation + Redis epoch + audit log + 403 Forbidden.
        Returns: (raw_token_out, access_token, user, family_id)
        """
        token_hash_in = cls.hash_token(raw_token_in)
        now = datetime.now(timezone.utc)

        # 1. Look up presented token FOR UPDATE to prevent race conditions on this row
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash_in).with_for_update()
        result = await db.execute(stmt)
        token_record = result.scalars().first()

        if not token_record:
            logger.warning("Presented refresh token hash not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INVALID_REFRESH_TOKEN",
            )

        # Check expiration
        if token_record.expires_at < now:
            logger.warning("Presented refresh token expired at %s", token_record.expires_at)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="REFRESH_TOKEN_EXPIRED",
            )

        # Fetch associated user
        user = await db.get(User, token_record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_INACTIVE_OR_NOT_FOUND",
            )

        family_id_str = str(token_record.family_id)
        user_id_str = str(user.id)

        # =====================================================================
        # Branch A: Happy Path (Unrotated Token)
        # =====================================================================
        if not token_record.is_revoked:
            raw_new = cls.generate_raw_token()
            hash_new = cls.hash_token(raw_new)
            new_id = uuid.uuid4()
            expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

            new_record = RefreshToken(
                id=new_id,
                user_id=user.id,
                token_hash=hash_new,
                family_id=token_record.family_id,
                is_revoked=False,
                expires_at=expires_at,
                created_at=now,
                ip_address=ip_address or token_record.ip_address,
                user_agent=user_agent or token_record.user_agent,
            )
            db.add(new_record)
            await db.flush()

            # Mark old token rotated and link replaced_by pointer
            token_record.is_revoked = True
            token_record.rotated_at = now
            token_record.replaced_by = new_id

            # Commit PostgreSQL first (Commit-First design)
            await db.commit()

            # Post-commit Redis grace stash (15s TTL, AES-256-GCM encrypted)
            encrypted_payload = crypto_service.encrypt_token(raw_new, family_id_str, user_id_str)
            await set_grace_stash(family_id_str, encrypted_payload, ttl=GRACE_PERIOD_SECONDS)

            access_token = token_service.create_access_token(user_id_str, user.email)
            return raw_new, access_token, user, token_record.family_id

        # =====================================================================
        # Branch B & C: Token has is_revoked == True
        # =====================================================================
        rotated_at = token_record.rotated_at or token_record.created_at
        time_since_rotation = (now - rotated_at).total_seconds()

        # Check if within 15-second grace window
        if time_since_rotation < GRACE_PERIOD_SECONDS and token_record.replaced_by is not None:
            logger.info("Grace window hit (%.2fs < %ds) for family %s. Traversing chain.", time_since_rotation, GRACE_PERIOD_SECONDS, family_id_str)

            # Traverse replaced_by pointer chain to find current leaf
            curr = token_record
            visited = {curr.id}
            while curr.replaced_by is not None:
                # Validate intermediary hop rotation timestamp
                if curr.rotated_at and (now - curr.rotated_at).total_seconds() >= GRACE_PERIOD_SECONDS:
                    break
                next_stmt = select(RefreshToken).where(RefreshToken.id == curr.replaced_by).with_for_update()
                next_res = await db.execute(next_stmt)
                next_token = next_res.scalars().first()
                if not next_token or next_token.id in visited:
                    break
                visited.add(next_token.id)
                curr = next_token

            leaf_token = curr

            # If leaf token was explicitly terminated (is_revoked == True and replaced_by is None)
            if leaf_token.is_revoked and leaf_token.replaced_by is None:
                logger.info("Token family %s was explicitly terminated during grace period", family_id_str)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="SESSION_TERMINATED",
                )

            # Sub-branch B1: Redis Grace Stash Hit
            cached_encrypted = await get_grace_stash(family_id_str)
            if cached_encrypted:
                decrypted_raw = crypto_service.decrypt_token(cached_encrypted, family_id_str, user_id_str)
                if decrypted_raw:
                    # Verify leaf token is unrevoked in PostgreSQL
                    if not leaf_token.is_revoked:
                        logger.info("Redis grace stash hit for family %s. Returning cached leaf token without DB mutation.", family_id_str)
                        access_token = token_service.create_access_token(user_id_str, user.email)
                        return decrypted_raw, access_token, user, token_record.family_id

            # Sub-branch B2: Redis Miss / Outage (Atomic Sub-Rotation per ADR-04)
            logger.info("Redis grace stash miss/outage for family %s. Performing atomic sub-rotation.", family_id_str)
            if not leaf_token.is_revoked:
                raw_next = cls.generate_raw_token()
                hash_next = cls.hash_token(raw_next)
                next_id = uuid.uuid4()
                expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

                next_record = RefreshToken(
                    id=next_id,
                    user_id=user.id,
                    token_hash=hash_next,
                    family_id=token_record.family_id,
                    is_revoked=False,
                    expires_at=expires_at,
                    created_at=now,
                    ip_address=ip_address or leaf_token.ip_address,
                    user_agent=user_agent or leaf_token.user_agent,
                )
                db.add(next_record)
                await db.flush()

                leaf_token.is_revoked = True
                leaf_token.rotated_at = now
                leaf_token.replaced_by = next_id

                await db.commit()

                # Update Redis stash
                encrypted_payload = crypto_service.encrypt_token(raw_next, family_id_str, user_id_str)
                await set_grace_stash(family_id_str, encrypted_payload, ttl=GRACE_PERIOD_SECONDS)

                access_token = token_service.create_access_token(user_id_str, user.email)
                return raw_next, access_token, user, token_record.family_id

        # =====================================================================
        # Branch C: Replay Attack Detected (Outside 15s Grace)
        # =====================================================================
        logger.warning(
            "REFRESH TOKEN REPLAY DETECTED for family %s (rotated %.2fs ago). Revoking entire family.",
            family_id_str,
            time_since_rotation,
        )

        # 1. Invalidate entire family in PostgreSQL
        revoke_stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == token_record.family_id)
            .values(is_revoked=True)
        )
        await db.execute(revoke_stmt)

        # 2. Record security audit log
        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=None,
            workspace_name="SYSTEM",
            workspace_slug="system",
            actor_id=user.id,
            actor_email=user.email,
            event_name="auth.token_family_revoked_replay_detected",
            ip_address=ip_address,
            user_agent=user_agent,
            payload={
                "family_id": family_id_str,
                "replayed_token_id": str(token_record.id),
                "rotated_at": rotated_at.isoformat(),
                "time_since_rotation_seconds": time_since_rotation,
            },
            created_at=now,
        )
        db.add(audit)
        await db.commit()

        # 3. Invalidate Redis state (set user revocation epoch and delete grace key)
        await set_user_revocation_epoch(user_id_str, int(now.timestamp()), ttl=900)
        await delete_grace_stash(family_id_str)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="REFRESH_TOKEN_REPLAY_DETECTED",
        )

    @classmethod
    async def revoke_session(
        cls,
        db: AsyncSession,
        family_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Revokes a specific refresh token family (single session logout)."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.user_id == user_id)
            .values(is_revoked=True, replaced_by=None)
        )
        res = await db.execute(stmt)
        await db.commit()

        # Clean Redis grace stash for this session family
        await delete_grace_stash(str(family_id))
        return res.rowcount > 0

    @classmethod
    async def revoke_all_sessions(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """Revokes all active refresh token families for the user (global logout)."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(is_revoked=True, replaced_by=None)
        )
        res = await db.execute(stmt)
        await db.commit()

        # Set global user revocation epoch in Redis
        await set_user_revocation_epoch(str(user_id), int(now.timestamp()), ttl=900)
        return res.rowcount

    @classmethod
    async def list_sessions(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        current_family_id: uuid.UUID | None = None,
    ) -> List[dict]:
        """Lists active session families for the user."""
        stmt = (
            select(
                RefreshToken.family_id,
                func.min(RefreshToken.created_at).label("created_at"),
                func.max(RefreshToken.expires_at).label("expires_at"),
                func.max(RefreshToken.ip_address).label("ip_address"),
                func.max(RefreshToken.user_agent).label("user_agent"),
            )
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .group_by(RefreshToken.family_id)
            .order_by(desc("created_at"))
        )
        result = await db.execute(stmt)
        rows = result.all()

        sessions = []
        for row in rows:
            sessions.append({
                "family_id": str(row.family_id),
                "created_at": row.created_at,
                "expires_at": row.expires_at,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "is_current": (row.family_id == current_family_id) if current_family_id else False,
            })
        return sessions


auth_service = AuthService()
