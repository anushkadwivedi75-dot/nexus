import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import Task
from app.models.task_status import TaskStatus
from app.schemas.task_status import TaskStatusCreate, TaskStatusUpdate


class TaskStatusService:
    @classmethod
    async def list_statuses(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[TaskStatus]:
        """Lists active status columns for a project ordered by rank ASC, id ASC."""
        stmt = (
            select(TaskStatus)
            .where(
                TaskStatus.project_id == project_id,
                TaskStatus.deleted_at.is_(None),
            )
            .order_by(TaskStatus.rank.asc(), TaskStatus.id.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def create_status(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        data: TaskStatusCreate,
    ) -> TaskStatus:
        """Creates a custom status column with rank allocation."""
        clean_name = data.name.strip()

        # Check name uniqueness
        name_check = await db.execute(
            select(TaskStatus.id).where(
                TaskStatus.project_id == project_id,
                func.lower(TaskStatus.name) == clean_name.lower(),
                TaskStatus.deleted_at.is_(None),
            )
        )
        if name_check.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Status column '{clean_name}' already exists in this project.",
            )

        # Allocate rank: max(rank) + 1000.0
        max_rank_res = await db.execute(
            select(func.max(TaskStatus.rank)).where(
                TaskStatus.project_id == project_id,
                TaskStatus.deleted_at.is_(None),
            )
        )
        current_max = max_rank_res.scalar()
        next_rank = (current_max + 1000.0) if current_max is not None else 1000.0

        status_col = TaskStatus(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            name=clean_name,
            rank=next_rank,
            color_hex=data.color_hex.upper(),
            is_completed_state=data.is_completed_state,
        )
        db.add(status_col)
        await db.commit()
        await db.refresh(status_col)
        return status_col

    @classmethod
    async def update_status(
        cls,
        db: AsyncSession,
        status_id: uuid.UUID,
        project_id: uuid.UUID,
        data: TaskStatusUpdate,
    ) -> TaskStatus:
        """Updates status name, color, rank, or completion state."""
        stmt = select(TaskStatus).where(
            TaskStatus.id == status_id,
            TaskStatus.project_id == project_id,
            TaskStatus.deleted_at.is_(None),
        )
        res = await db.execute(stmt)
        col = res.scalars().first()

        if not col:
            raise HTTPException(status_code=404, detail="Status column not found.")

        if data.name is not None:
            clean_name = data.name.strip()
            if clean_name.lower() != col.name.lower():
                # Check conflict
                chk = await db.execute(
                    select(TaskStatus.id).where(
                        TaskStatus.project_id == project_id,
                        func.lower(TaskStatus.name) == clean_name.lower(),
                        TaskStatus.id != status_id,
                        TaskStatus.deleted_at.is_(None),
                    )
                )
                if chk.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Status column '{clean_name}' already exists in this project.",
                    )
            col.name = clean_name

        if data.color_hex is not None:
            col.color_hex = data.color_hex.upper()

        if data.rank is not None:
            col.rank = data.rank

        if data.is_completed_state is not None:
            col.is_completed_state = data.is_completed_state

        await db.commit()
        await db.refresh(col)
        return col

    @classmethod
    async def delete_status(
        cls,
        db: AsyncSession,
        status_id: uuid.UUID,
        project_id: uuid.UUID,
        fallback_status_id: uuid.UUID,
    ) -> bool:
        """
        Deletes a status column after safely remapping all active tasks to fallback_status_id.
        Guarantees zero orphaned task references.
        """
        if status_id == fallback_status_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fallback status cannot be the status column being deleted.",
            )

        # 1. Fetch column to delete
        stmt = select(TaskStatus).where(
            TaskStatus.id == status_id,
            TaskStatus.project_id == project_id,
            TaskStatus.deleted_at.is_(None),
        ).with_for_update()
        col = (await db.execute(stmt)).scalars().first()
        if not col:
            raise HTTPException(status_code=404, detail="Status column to delete not found.")

        # 2. Fetch destination fallback column
        fb_stmt = select(TaskStatus).where(
            TaskStatus.id == fallback_status_id,
            TaskStatus.project_id == project_id,
            TaskStatus.deleted_at.is_(None),
        ).with_for_update()
        fb_col = (await db.execute(fb_stmt)).scalars().first()
        if not fb_col:
            raise HTTPException(status_code=400, detail="Fallback status column not found in this project.")

        # 3. Check active column count (cannot delete the only column)
        count_stmt = select(func.count(TaskStatus.id)).where(
            TaskStatus.project_id == project_id,
            TaskStatus.deleted_at.is_(None),
        )
        total_cols = (await db.execute(count_stmt)).scalar() or 0
        if total_cols <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only status column in a project.",
            )

        # 4. Remap tasks transactionally and increment their version
        await db.execute(
            update(Task)
            .where(Task.status_id == status_id, Task.deleted_at.is_(None))
            .values(status_id=fallback_status_id, version=Task.version + 1)
        )

        # 5. Soft delete column
        col.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        return True


task_status_service = TaskStatusService()

