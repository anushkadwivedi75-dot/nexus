import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


class WorkspaceMemberService:
    @classmethod
    async def list_members(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> List[dict]:
        """Lists all members of the workspace with user profile details."""
        stmt = (
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(
                # Order: owner first, then admin, then member, then joined_at
                WorkspaceMember.role.desc(),
                WorkspaceMember.joined_at.asc(),
            )
        )
        res = await db.execute(stmt)
        rows = res.all()

        members = []
        for mem, u in rows:
            members.append({
                "id": mem.id,
                "workspace_id": mem.workspace_id,
                "user_id": mem.user_id,
                "role": mem.role,
                "joined_at": mem.joined_at,
                "user": {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "avatar_url": u.avatar_url,
                },
            })
        return members

    @classmethod
    async def update_member_role(
        cls,
        db: AsyncSession,
        workspace: Workspace,
        target_user_id: uuid.UUID,
        new_role: str,
        actor: User,
        actor_role: str,
    ) -> WorkspaceMember:
        """
        Updates a member's role to 'admin' or 'member'.
        Strictly rejects modifying or assigning 'owner'.
        """
        clean_role = new_role.strip().lower()
        if clean_role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CANNOT_ASSIGN_OWNER_VIA_ROLE_UPDATE: Use POST /transfer-ownership to transfer workspace ownership.",
            )

        if clean_role not in ("admin", "member"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be either 'admin' or 'member'.",
            )

        # Lock target membership row FOR UPDATE
        stmt = (
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == target_user_id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        target = res.scalars().first()

        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target member not found in this workspace.",
            )

        # Invariant: Active owner cannot have role modified generically
        if target.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CANNOT_MODIFY_OWNER_ROLE: The workspace owner's role cannot be modified. Use transfer-ownership.",
            )

        # Privilege checks: Admins cannot demote other admins or change owner
        if actor_role != "owner" and target.role == "admin" and actor.id != target_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the workspace owner can modify an administrator's role.",
            )

        old_role = target.role
        target.role = clean_role

        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=actor.id,
            actor_email=actor.email,
            event_name="workspace.member_role_updated",
            payload={
                "target_user_id": str(target_user_id),
                "old_role": old_role,
                "new_role": clean_role,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(target)
        return target

    @classmethod
    async def remove_member(
        cls,
        db: AsyncSession,
        workspace: Workspace,
        target_user_id: uuid.UUID,
        actor: User,
        actor_role: str,
    ) -> bool:
        """
        Removes a member from the workspace.
        Supports admin/owner removal and voluntary self-removal.
        Strictly forbids removing the active workspace owner.
        """
        is_self_removal = actor.id == target_user_id

        # Lock target membership row FOR UPDATE
        stmt = (
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == target_user_id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        target = res.scalars().first()

        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target member not found in this workspace.",
            )

        # Invariant: Cannot remove workspace owner under any circumstance
        if target.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CANNOT_REMOVE_WORKSPACE_OWNER: The workspace owner cannot be removed. Transfer ownership first.",
            )

        if not is_self_removal:
            # Caller must be admin or owner
            if actor_role not in ("owner", "admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to remove workspace members.",
                )
            # Admin cannot remove another admin
            if actor_role == "admin" and target.role == "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workspace administrators cannot remove other administrators.",
                )

        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=actor.id,
            actor_email=actor.email,
            event_name="workspace.member_removed" if not is_self_removal else "workspace.member_left",
            payload={
                "target_user_id": str(target_user_id),
                "role": target.role,
                "is_self_removal": is_self_removal,
            },
        )
        db.add(audit)

        await db.delete(target)
        await db.commit()
        return True


workspace_member_service = WorkspaceMemberService()

