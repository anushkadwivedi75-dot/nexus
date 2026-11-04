import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.workspace_member import WorkspaceMember


class ProjectMemberService:
    @classmethod
    async def list_members(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[dict]:
        """Lists members in a private project with user profile details."""
        stmt = (
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at.asc())
        )
        res = await db.execute(stmt)
        rows = res.all()

        members = []
        for pm, u in rows:
            members.append({
                "project_id": pm.project_id,
                "user_id": pm.user_id,
                "joined_at": pm.joined_at,
                "user": {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "avatar_url": u.avatar_url,
                },
            })
        return members

    @classmethod
    async def add_member(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """Adds an active workspace member to the private project."""
        # 1. Verify target user is a member of the workspace
        ws_check = await db.execute(
            select(WorkspaceMember.id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if not ws_check.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be an active workspace member before joining a project.",
            )

        # 2. Check if already a project member
        pm_check = await db.execute(
            select(ProjectMember.user_id).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        if pm_check.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this project.",
            )

        # 3. Insert project member
        pm = ProjectMember(
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
        )
        db.add(pm)
        await db.commit()
        await db.refresh(pm)

        u = (await db.execute(select(User).where(User.id == user_id))).scalars().first()

        return {
            "project_id": pm.project_id,
            "user_id": pm.user_id,
            "joined_at": pm.joined_at,
            "user": {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "avatar_url": u.avatar_url,
            } if u else None,
        }

    @classmethod
    async def remove_member(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Removes a user from the private project."""
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        res = await db.execute(stmt)
        pm = res.scalars().first()

        if not pm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this project.",
            )

        await db.delete(pm)
        await db.commit()
        return True


project_member_service = ProjectMemberService()

