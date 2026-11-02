import uuid
from datetime import datetime, timezone
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.task_status import TaskStatus
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.project import ProjectCreate, ProjectUpdate

DEFAULT_STATUSES = [
    {"name": "Backlog", "rank": 1000.0, "color_hex": "#94A3B8", "is_completed_state": False},
    {"name": "Todo", "rank": 2000.0, "color_hex": "#38BDF8", "is_completed_state": False},
    {"name": "In Progress", "rank": 3000.0, "color_hex": "#F59E0B", "is_completed_state": False},
    {"name": "Done", "rank": 4000.0, "color_hex": "#10B981", "is_completed_state": True},
]


class ProjectService:
    @classmethod
    async def create_project(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        creator: User,
        data: ProjectCreate,
    ) -> Project:
        """
        Atomically creates a project, seeds default status columns,
        and adds the creator as initial member if private.
        """
        clean_key = data.key.strip().upper()

        # 1. Verify key uniqueness in this workspace (among non-deleted projects)
        key_check = await db.execute(
            select(Project.id).where(
                Project.workspace_id == workspace_id,
                Project.key == clean_key,
                Project.deleted_at.is_(None),
            )
        )
        if key_check.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project key '{clean_key}' is already in use in this workspace.",
            )

        # 2. If lead_id provided, verify lead is an active workspace member
        lead_id = data.lead_id
        if lead_id:
            lead_check = await db.execute(
                select(WorkspaceMember.id).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == lead_id,
                )
            )
            if not lead_check.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project lead must be an active member of this workspace.",
                )

        # 3. Create Project record
        project = Project(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=data.name.strip(),
            key=clean_key,
            description=data.description,
            lead_id=lead_id,
            task_counter=0,
            is_private=data.is_private,
            status="active",
        )
        db.add(project)
        await db.flush()

        # 4. Seed default status columns
        for s in DEFAULT_STATUSES:
            status_col = TaskStatus(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                project_id=project.id,
                name=s["name"],
                rank=s["rank"],
                color_hex=s["color_hex"],
                is_completed_state=s["is_completed_state"],
            )
            db.add(status_col)

        # 5. If private, add creator to project_members
        if data.is_private:
            pm = ProjectMember(
                workspace_id=workspace_id,
                project_id=project.id,
                user_id=creator.id,
            )
            db.add(pm)

        # 6. Audit log
        audit = AuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            workspace_name="",
            workspace_slug="",
            actor_id=creator.id,
            actor_email=creator.email,
            event_name="project.created",
            payload={
                "project_id": str(project.id),
                "name": project.name,
                "key": project.key,
                "is_private": project.is_private,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(project)
        return project

    @classmethod
    async def list_workspace_projects(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        ws_role: str,
    ) -> List[dict]:
        """Lists accessible projects in the workspace with task counts."""
        tasks_count_subquery = (
            select(func.count(Task.id))
            .where(
                Task.project_id == Project.id,
                Task.deleted_at.is_(None),
            )
            .scalar_subquery()
        )

        stmt = (
            select(Project, tasks_count_subquery.label("tasks_count"))
            .where(
                Project.workspace_id == workspace_id,
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at.desc())
        )

        res = await db.execute(stmt)
        rows = res.all()

        is_elevated = ws_role in ("owner", "admin")
        projects_out = []

        for p, count in rows:
            if p.is_private and not is_elevated and p.lead_id != user_id:
                # Check membership in private project
                pm_check = await db.execute(
                    select(ProjectMember.user_id).where(
                        ProjectMember.project_id == p.id,
                        ProjectMember.user_id == user_id,
                    )
                )
                if not pm_check.scalars().first():
                    continue  # User has no access to this private project

            projects_out.append({
                "id": p.id,
                "workspace_id": p.workspace_id,
                "name": p.name,
                "key": p.key,
                "description": p.description,
                "lead_id": p.lead_id,
                "task_counter": p.task_counter,
                "is_private": p.is_private,
                "status": p.status,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "tasks_count": count or 0,
            })

        return projects_out

    @classmethod
    async def allocate_task_number(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> int:
        """
        Allocates an atomic 64-bit monotonic task number in PostgreSQL.
        Guarantees 100% collision-free task numbers under concurrent requests.
        """
        stmt = text(
            """
            UPDATE projects
            SET task_counter = task_counter + 1
            WHERE id = :project_id AND workspace_id = :workspace_id
            RETURNING task_counter;
            """
        )
        res = await db.execute(stmt, {"project_id": project_id, "workspace_id": workspace_id})
        val = res.scalar()
        if val is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        return int(val)

    @classmethod
    async def update_project(
        cls,
        db: AsyncSession,
        project: Project,
        data: ProjectUpdate,
        actor: User,
    ) -> Project:
        """Updates project metadata."""
        if data.name is not None:
            project.name = data.name.strip()

        if data.description is not None:
            project.description = data.description

        if data.status is not None:
            project.status = data.status

        if data.is_private is not None:
            project.is_private = data.is_private

        if data.lead_id is not None:
            # Verify workspace membership
            check = await db.execute(
                select(WorkspaceMember.id).where(
                    WorkspaceMember.workspace_id == project.workspace_id,
                    WorkspaceMember.user_id == data.lead_id,
                )
            )
            if not check.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project lead must be an active workspace member.",
                )
            project.lead_id = data.lead_id

        await db.commit()
        await db.refresh(project)
        return project

    @classmethod
    async def delete_project(
        cls,
        db: AsyncSession,
        project: Project,
        actor: User,
    ) -> bool:
        """Soft deletes the project and marks its deleted_at timestamp."""
        now = datetime.now(timezone.utc)
        project.deleted_at = now

        # Soft delete associated tasks
        await db.execute(
            update(Task)
            .where(Task.project_id == project.id, Task.deleted_at.is_(None))
            .values(deleted_at=now)
        )

        # Soft delete associated task statuses
        await db.execute(
            update(TaskStatus)
            .where(TaskStatus.project_id == project.id, TaskStatus.deleted_at.is_(None))
            .values(deleted_at=now)
        )

        await db.commit()
        return True


project_service = ProjectService()
