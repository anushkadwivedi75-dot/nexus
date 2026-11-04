import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_invitation import WorkspaceInvitation
from app.models.workspace_member import WorkspaceMember
from app.services.outbox import outbox_service


class WorkspaceInvitationService:
    @classmethod
    async def create_invitation(
        cls,
        db: AsyncSession,
        workspace: Workspace,
        email: str,
        role: str,
        inviter: User,
    ) -> Tuple[WorkspaceInvitation, str]:
        """
        Creates a cryptographic workspace invitation.
        Checks for duplicate membership and active pending invitations.
        """
        clean_email = email.strip().lower()
        clean_role = role.strip().lower()

        if clean_role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CANNOT_INVITE_AS_OWNER: Workspaces can have only one owner. Transfer ownership after joining.",
            )

        if clean_role not in ("admin", "member"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'admin' or 'member'.",
            )

        # 1. Check if user is already a member of this workspace
        mem_stmt = (
            select(WorkspaceMember.id)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(
                WorkspaceMember.workspace_id == workspace.id,
                func.lower(User.email) == clean_email,
            )
        )
        if (await db.execute(mem_stmt)).scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{clean_email}' is already a member of this workspace.",
            )

        # 2. Check if active pending invite already exists
        now = datetime.now(timezone.utc)
        inv_stmt = select(WorkspaceInvitation).where(
            WorkspaceInvitation.workspace_id == workspace.id,
            func.lower(WorkspaceInvitation.email) == clean_email,
            WorkspaceInvitation.status == "pending",
        )
        existing_invite = (await db.execute(inv_stmt)).scalars().first()
        if existing_invite:
            if existing_invite.expires_at > now:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"An active pending invitation already exists for '{clean_email}'.",
                )
            else:
                # Expire previous stale invite
                existing_invite.status = "expired"
                await db.flush()

        # 3. Generate 256-bit secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = now + timedelta(days=7)

        invitation = WorkspaceInvitation(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            email=clean_email,
            role=clean_role,
            token_hash=token_hash,
            status="pending",
            invited_by=inviter.id,
            expires_at=expires_at,
        )
        db.add(invitation)

        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=inviter.id,
            actor_email=inviter.email,
            event_name="workspace.invitation_created",
            payload={
                "email": clean_email,
                "role": clean_role,
                "expires_at": expires_at.isoformat(),
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(invitation)
        return invitation, raw_token

    @classmethod
    async def list_invitations(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> List[WorkspaceInvitation]:
        """Lists active pending invitations for the workspace, updating expired ones."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.status == "pending",
            )
            .order_by(WorkspaceInvitation.created_at.desc())
        )
        res = await db.execute(stmt)
        invitations = res.scalars().all()

        active = []
        has_expired = False
        for inv in invitations:
            if inv.expires_at <= now:
                inv.status = "expired"
                has_expired = True
            else:
                active.append(inv)

        if has_expired:
            await db.commit()

        return active

    @classmethod
    async def revoke_invitation(
        cls,
        db: AsyncSession,
        workspace: Workspace,
        invitation_id: uuid.UUID,
        actor: User,
    ) -> bool:
        """Revokes a pending invitation."""
        stmt = (
            select(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.id == invitation_id,
                WorkspaceInvitation.workspace_id == workspace.id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        invitation = res.scalars().first()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found in this workspace.",
            )

        if invitation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot revoke invitation with status '{invitation.status}'. Only pending invitations can be revoked.",
            )

        invitation.status = "revoked"

        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=actor.id,
            actor_email=actor.email,
            event_name="workspace.invitation_revoked",
            payload={"invitation_id": str(invitation_id), "email": invitation.email},
        )
        db.add(audit)

        await db.commit()
        return True

    @classmethod
    async def accept_invitation(
        cls,
        db: AsyncSession,
        raw_token: str,
        user: User,
    ) -> Tuple[Workspace, WorkspaceMember]:
        """
        Atomically validates and accepts an invitation token.
        Inserts caller into workspace_members with the invited role.
        """
        token_hash = hashlib.sha256(raw_token.strip().encode()).hexdigest()
        now = datetime.now(timezone.utc)

        # Lock invitation row FOR UPDATE
        stmt = (
            select(WorkspaceInvitation)
            .where(WorkspaceInvitation.token_hash == token_hash)
            .with_for_update()
        )
        res = await db.execute(stmt)
        invitation = res.scalars().first()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or nonexistent invitation token.",
            )

        if invitation.status == "revoked":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has been revoked by a workspace administrator.",
            )

        if invitation.status == "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has already been accepted.",
            )

        if invitation.expires_at <= now:
            invitation.status = "expired"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has expired. Please request a new invitation link.",
            )

        # Lock workspace to ensure it still exists
        ws_stmt = (
            select(Workspace)
            .where(Workspace.id == invitation.workspace_id)
            .with_for_update()
        )
        ws_res = await db.execute(ws_stmt)
        workspace = ws_res.scalars().first()

        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The workspace associated with this invitation no longer exists.",
            )

        # Check if caller is already a member
        mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
        existing_mem = (await db.execute(mem_stmt)).scalars().first()

        if existing_mem:
            # Mark invitation accepted and return existing membership
            invitation.status = "accepted"
            invitation.accepted_at = now
            await db.commit()
            return workspace, existing_mem

        # Create new membership
        new_member = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            user_id=user.id,
            role=invitation.role,
        )
        db.add(new_member)

        # Update invitation
        invitation.status = "accepted"
        invitation.accepted_at = now

        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=user.id,
            actor_email=user.email,
            event_name="workspace.invitation_accepted",
            payload={
                "invitation_id": str(invitation.id),
                "role": invitation.role,
                "email": invitation.email,
            },
        )
        db.add(audit)

        # Transactional Outbox Event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace.id,
            event_type="workspace.invitation_accepted",
            entity_type="invitation",
            entity_id=invitation.id,
            actor_id=user.id,
            payload={
                "invitation_id": str(invitation.id),
                "user_id": str(user.id),
                "role": invitation.role,
            },
        )

        await db.commit()
        await db.refresh(workspace)
        await db.refresh(new_member)

        return workspace, new_member


workspace_invitation_service = WorkspaceInvitationService()

