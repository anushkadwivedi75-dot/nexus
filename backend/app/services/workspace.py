import uuid
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from app.services.outbox import outbox_service


class WorkspaceService:
    @classmethod
    async def create_workspace(
        cls,
        db: AsyncSession,
        creator: User,
        data: WorkspaceCreate,
    ) -> Tuple[Workspace, WorkspaceMember]:
        """
        Atomically creates a workspace and assigns the creator role='owner'.
        Enforces the invariant that a workspace never exists without an owner.
        """
        slug = data.slug.strip().lower()

        # Check slug conflict
        existing = await db.execute(
            select(Workspace.id).where(func.lower(Workspace.slug) == slug)
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{slug}' is already taken.",
            )

        workspace_id = uuid.uuid4()
        workspace = Workspace(
            id=workspace_id,
            name=data.name.strip(),
            slug=slug,
            owner_id=creator.id,
        )
        db.add(workspace)
        await db.flush()

        member = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            user_id=creator.id,
            role="owner",
        )
        db.add(member)

        # Audit log for workspace creation
        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=creator.id,
            actor_email=creator.email,
            event_name="workspace.created",
            payload={"name": workspace.name, "slug": workspace.slug},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(workspace)
        await db.refresh(member)

        return workspace, member

    @classmethod
    async def list_user_workspaces(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[dict]:
        """Lists all workspaces the user actively belongs to, with role and member counts."""
        members_count_subquery = (
            select(func.count(WorkspaceMember.id))
            .where(WorkspaceMember.workspace_id == Workspace.id)
            .scalar_subquery()
        )

        stmt = (
            select(
                Workspace,
                WorkspaceMember.role,
                members_count_subquery.label("members_count"),
            )
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        workspaces_out = []
        for ws, role, count in rows:
            workspaces_out.append({
                "id": ws.id,
                "name": ws.name,
                "slug": ws.slug,
                "logo_url": ws.logo_url,
                "owner_id": ws.owner_id,
                "role": role,
                "members_count": count or 1,
                "created_at": ws.created_at,
                "updated_at": ws.updated_at,
            })
        return workspaces_out

    @classmethod
    async def get_workspace_details(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """Fetches workspace details along with caller's role and member count."""
        count_stmt = select(func.count(WorkspaceMember.id)).where(
            WorkspaceMember.workspace_id == workspace_id
        )
        count_res = await db.execute(count_stmt)
        members_count = count_res.scalar() or 1

        mem_stmt = select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        mem_res = await db.execute(mem_stmt)
        role = mem_res.scalar()

        ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await db.execute(ws_stmt)
        ws = ws_res.scalars().first()

        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        return {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug,
            "logo_url": ws.logo_url,
            "owner_id": ws.owner_id,
            "role": role,
            "members_count": members_count,
            "created_at": ws.created_at,
            "updated_at": ws.updated_at,
        }

    @classmethod
    async def update_workspace(
        cls,
        db: AsyncSession,
        workspace: Workspace,
        data: WorkspaceUpdate,
        actor: User,
    ) -> Workspace:
        """Updates workspace details (name, slug, logo_url)."""
        if data.slug is not None:
            new_slug = data.slug.strip().lower()
            if new_slug != workspace.slug:
                # Check for conflict
                stmt = select(Workspace.id).where(
                    func.lower(Workspace.slug) == new_slug,
                    Workspace.id != workspace.id,
                )
                existing = await db.execute(stmt)
                if existing.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Slug '{new_slug}' is already taken.",
                    )
                workspace.slug = new_slug

        if data.name is not None:
            workspace.name = data.name.strip()

        if data.logo_url is not None:
            workspace.logo_url = data.logo_url.strip() or None

        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=actor.id,
            actor_email=actor.email,
            event_name="workspace.updated",
            payload={"name": workspace.name, "slug": workspace.slug},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(workspace)
        return workspace

    @classmethod
    async def delete_workspace(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID,
        actor: User,
    ) -> bool:
        """
        Deletes the workspace. Authorized only for the current owner.
        PostgreSQL composite ON DELETE CASCADE constraints handle child cleanups.
        """
        # Lock workspace row FOR UPDATE
        stmt = select(Workspace).where(Workspace.id == workspace_id).with_for_update()
        res = await db.execute(stmt)
        workspace = res.scalars().first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        if workspace.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the workspace owner can delete the workspace.",
            )

        # Audit log before deletion (workspace_id will be set NULL upon deletion)
        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=actor.id,
            actor_email=actor.email,
            event_name="workspace.deleted",
            payload={"name": workspace.name, "slug": workspace.slug},
        )
        db.add(audit)
        await db.flush()

        await db.delete(workspace)
        await db.commit()
        return True

    @classmethod
    async def transfer_ownership(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        current_owner_id: uuid.UUID,
        new_owner_id: uuid.UUID,
        actor: User,
    ) -> dict:
        """
        Executes the atomic 8-step SQL transaction for workspace ownership transfer.
        Enforces exactly-one-owner and satisfies uq_workspace_single_owner partial index.
        """
        # Step 1: Prevent self-transfer
        if new_owner_id == current_owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CANNOT_TRANSFER_TO_SELF: You are already the workspace owner.",
            )

        # Step 2: Lock workspace row FOR UPDATE
        ws_stmt = select(Workspace).where(Workspace.id == workspace_id).with_for_update()
        ws_res = await db.execute(ws_stmt)
        workspace = ws_res.scalars().first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        # Step 3: Verify caller is still the authoritative workspace owner
        if workspace.owner_id != current_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caller is no longer the active workspace owner.",
            )

        # Step 4: Lock both membership records simultaneously in deterministic user_id ASC order
        mem_stmt = (
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id.in_([current_owner_id, new_owner_id]),
            )
            .order_by(WorkspaceMember.user_id.asc())
            .with_for_update()
        )
        mem_res = await db.execute(mem_stmt)
        members = mem_res.scalars().all()

        # Step 5: Verify target is an active workspace member and caller is the owner
        caller_member = next((m for m in members if m.user_id == current_owner_id), None)
        target_member = next((m for m in members if m.user_id == new_owner_id), None)

        if not caller_member or caller_member.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CANNOT_TRANSFER_OWNERSHIP: Caller does not possess active owner membership.",
            )

        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TARGET_NOT_MEMBER: Target user must be an active member of this workspace to receive ownership.",
            )

        # Step 6: Demote current owner to 'admin' first (satisfies uq_workspace_single_owner)
        caller_member.role = "admin"
        await db.flush()

        # Step 7: Promote target member to 'owner' second
        target_member.role = "owner"
        await db.flush()

        # Step 8: Update workspace.owner_id
        workspace.owner_id = new_owner_id

        # Record audit log
        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_slug=workspace.slug,
            actor_id=actor.id,
            actor_email=actor.email,
            event_name="workspace.ownership_transferred",
            payload={
                "previous_owner_id": str(current_owner_id),
                "new_owner_id": str(new_owner_id),
            },
        )
        db.add(audit)

        # Stage notification to new owner
        from app.services.notification import NotificationService
        actor_name = actor.full_name or actor.email
        await NotificationService.create_notification(
            db=db,
            workspace_id=workspace.id,
            recipient_id=new_owner_id,
            actor_id=actor.id,
            action_type="workspace_ownership_transferred",
            entity_type="workspace",
            entity_id=workspace.id,
            message=f"{actor_name} transferred ownership of workspace '{workspace.name}' to you.",
            payload={
                "workspace_id": str(workspace.id),
                "workspace_name": workspace.name,
                "workspace_slug": workspace.slug,
                "previous_owner_id": str(current_owner_id),
            },
            deduplication_key=f"ownership:{workspace.id}:{new_owner_id}",
        )

        # Transactional Outbox Event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace.id,
            event_type="workspace.ownership_transferred",
            entity_type="workspace",
            entity_id=workspace.id,
            actor_id=actor.id,
            payload={
                "previous_owner_id": str(current_owner_id),
                "new_owner_id": str(new_owner_id),
            },
        )

        await db.commit()

        return {
            "success": True,
            "message": "Ownership successfully transferred.",
            "workspace_id": str(workspace.id),
            "previous_owner_id": str(current_owner_id),
            "previous_owner_role": "admin",
            "new_owner_id": str(new_owner_id),
            "new_owner_role": "owner",
        }


workspace_service = WorkspaceService()

