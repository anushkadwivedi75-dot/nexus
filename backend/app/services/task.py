import uuid
from datetime import datetime, timezone
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.outbox_event import OutboxEvent
from app.models.project import Project
from app.models.tag import Tag
from app.models.task import Task
from app.models.task_assignee import TaskAssignee
from app.models.task_status import TaskStatus
from app.models.task_tag import TaskTag
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.task import TaskCreate, TaskMove, TaskUpdate
from app.services.fractional_index import fractional_index_service
from app.services.outbox import outbox_service
from app.services.project import project_service


class TaskService:
    @classmethod
    async def create_task(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project: Project,
        creator: User,
        data: TaskCreate,
    ) -> dict:
        """
        Creates a task atomically with monotonic task numbering and fractional rank.
        """
        # 1. Verify status belongs to this project
        status_check = await db.execute(
            select(TaskStatus).where(
                TaskStatus.id == data.status_id,
                TaskStatus.project_id == project.id,
                TaskStatus.deleted_at.is_(None),
            )
        )
        task_status_row = status_check.scalars().first()
        if not task_status_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status_id for this project.",
            )

        # 2. Allocate monotonic 64-bit task number atomically
        task_number = await project_service.allocate_task_number(
            db=db,
            workspace_id=workspace_id,
            project_id=project.id,
        )

        # 3. Compute initial fractional rank (append to end of status column)
        max_rank_res = await db.execute(
            select(func.max(Task.rank)).where(
                Task.project_id == project.id,
                Task.status_id == data.status_id,
                Task.deleted_at.is_(None),
            )
        )
        current_max_rank = max_rank_res.scalar()
        initial_rank = (current_max_rank + 1000.0) if current_max_rank is not None else 1000.0

        # 4. Create Task
        task = Task(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            project_id=project.id,
            status_id=data.status_id,
            task_number=task_number,
            title=data.title.strip(),
            description=data.description,
            priority=data.priority,
            rank=initial_rank,
            version=1,
            creator_id=creator.id,
            due_date=data.due_date,
        )
        db.add(task)
        await db.flush()

        # 5. Handle assignees (verify each belongs to workspace)
        for uid in data.assignee_ids:
            mem_chk = await db.execute(
                select(WorkspaceMember.id).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == uid,
                )
            )
            if not mem_chk.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Assignee with user ID '{uid}' is not a member of this workspace.",
                )
            assignee = TaskAssignee(
                workspace_id=workspace_id,
                task_id=task.id,
                user_id=uid,
            )
            db.add(assignee)

        # 6. Handle tags
        for tname in data.tag_names:
            clean_tag = tname.strip()
            if not clean_tag:
                continue
            # Find or create tag in workspace
            tag_res = await db.execute(
                select(Tag).where(
                    Tag.workspace_id == workspace_id,
                    func.lower(Tag.name) == clean_tag.lower(),
                )
            )
            tag = tag_res.scalars().first()
            if not tag:
                tag = Tag(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    name=clean_tag,
                    color_hex="#8B5CF6",
                )
                db.add(tag)
                await db.flush()

            tt = TaskTag(
                workspace_id=workspace_id,
                task_id=task.id,
                tag_id=tag.id,
            )
            db.add(tt)

        # 6b. Stage notifications for assigned members
        from app.services.notification import NotificationService
        actor_name = creator.full_name or creator.email
        task_label = f"{project.key}-{task.task_number}"
        for uid in data.assignee_ids:
            await NotificationService.create_notification(
                db=db,
                workspace_id=workspace_id,
                recipient_id=uid,
                actor_id=creator.id,
                action_type="task_assigned",
                entity_type="task",
                entity_id=task.id,
                message=f"{actor_name} assigned you to {task_label}: {task.title}",
                payload={
                    "task_id": str(task.id),
                    "project_id": str(project.id),
                    "task_title": task.title,
                    "task_number": task_label,
                    "priority": task.priority,
                },
                deduplication_key=f"assign:{task.id}:{uid}",
            )

        # 7. Transactional Outbox Event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace_id,
            event_type="task.created",
            entity_type="task",
            entity_id=task.id,
            actor_id=creator.id,
            payload={
                "task_id": str(task.id),
                "project_id": str(project.id),
                "status_id": str(task.status_id),
                "task_number": task.task_number,
                "task_key": f"{project.key}-{task.task_number}",
                "title": task.title,
                "priority": task.priority,
                "rank": task.rank,
                "version": task.version,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            },
        )

        await db.commit()
        return await cls.get_task_details(db, workspace_id, project.id, task.id, project_key=project.key)

    @classmethod
    async def get_task_details(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        project_key: str | None = None,
    ) -> dict:
        """Fetches full task details with assignees and tags."""
        stmt = (
            select(Task)
            .where(
                Task.id == task_id,
                Task.project_id == project_id,
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
            )
        )
        res = await db.execute(stmt)
        task = res.scalars().first()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Get project key if not provided
        if not project_key:
            pkey_res = await db.execute(select(Project.key).where(Project.id == project_id))
            project_key = pkey_res.scalar() or "TASK"

        # Load assignees
        assignee_stmt = (
            select(User)
            .join(TaskAssignee, TaskAssignee.user_id == User.id)
            .where(TaskAssignee.task_id == task.id)
        )
        assignees_res = await db.execute(assignee_stmt)
        assignees = [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "avatar_url": u.avatar_url,
            }
            for u in assignees_res.scalars().all()
        ]

        # Load tags
        tag_stmt = (
            select(Tag)
            .join(TaskTag, TaskTag.tag_id == Tag.id)
            .where(TaskTag.task_id == task.id)
        )
        tags_res = await db.execute(tag_stmt)
        tags = [
            {
                "id": t.id,
                "name": t.name,
                "color_hex": t.color_hex,
            }
            for t in tags_res.scalars().all()
        ]

        return {
            "id": task.id,
            "workspace_id": task.workspace_id,
            "project_id": task.project_id,
            "status_id": task.status_id,
            "task_number": task.task_number,
            "task_key": f"{project_key}-{task.task_number}",
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "rank": task.rank,
            "version": task.version,
            "creator_id": task.creator_id,
            "due_date": task.due_date,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "assignees": assignees,
            "tags": tags,
        }

    @classmethod
    async def update_task(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        data: TaskUpdate,
        current_user: User | None = None,
    ) -> dict:
        """Updates task fields with version increment and assignee/tag management."""
        stmt = (
            select(Task)
            .where(
                Task.id == task_id,
                Task.project_id == project_id,
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        task = res.scalars().first()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        if data.title is not None:
            task.title = data.title.strip()

        if data.description is not None:
            task.description = data.description

        if data.priority is not None:
            task.priority = data.priority

        if data.due_date is not None:
            task.due_date = data.due_date

        # Track assignee modifications for notifications
        added_assignee_ids: set[uuid.UUID] = set()
        removed_assignee_ids: set[uuid.UUID] = set()

        # Update assignees if specified
        if data.assignee_ids is not None:
            # Capture existing assignees before deletion
            old_assignees_res = await db.execute(
                select(TaskAssignee.user_id).where(TaskAssignee.task_id == task.id)
            )
            old_assignee_ids = set(old_assignees_res.scalars().all())
            new_assignee_ids = set(data.assignee_ids)
            added_assignee_ids = new_assignee_ids - old_assignee_ids
            removed_assignee_ids = old_assignee_ids - new_assignee_ids

            from sqlalchemy import delete
            await db.execute(delete(TaskAssignee).where(TaskAssignee.task_id == task.id))

            for uid in data.assignee_ids:
                mem_chk = await db.execute(
                    select(WorkspaceMember.id).where(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.user_id == uid,
                    )
                )
                if not mem_chk.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Assignee with user ID '{uid}' is not a member of this workspace.",
                    )
                db.add(TaskAssignee(workspace_id=workspace_id, task_id=task.id, user_id=uid))

        # Update tags if specified
        if data.tag_names is not None:
            from sqlalchemy import delete
            await db.execute(delete(TaskTag).where(TaskTag.task_id == task.id))

            for tname in data.tag_names:
                clean_tag = tname.strip()
                if not clean_tag:
                    continue
                tag_res = await db.execute(
                    select(Tag).where(
                        Tag.workspace_id == workspace_id,
                        func.lower(Tag.name) == clean_tag.lower(),
                    )
                )
                tag = tag_res.scalars().first()
                if not tag:
                    tag = Tag(
                        id=uuid.uuid4(),
                        workspace_id=workspace_id,
                        name=clean_tag,
                        color_hex="#8B5CF6",
                    )
                    db.add(tag)
                    await db.flush()

                db.add(TaskTag(workspace_id=workspace_id, task_id=task.id, tag_id=tag.id))

        task.version += 1

        # Dispatch assignee notifications
        if added_assignee_ids or removed_assignee_ids:
            from app.services.notification import NotificationService
            actor_name = (current_user.full_name or current_user.email) if current_user else "A team member"
            actor_id = current_user.id if current_user else None

            # Fetch project key for notification label
            proj_stmt = select(Project.key).where(Project.id == project_id)
            proj_res = await db.execute(proj_stmt)
            pkey = proj_res.scalar() or "TASK"
            task_label = f"{pkey}-{task.task_number}"

            for uid in added_assignee_ids:
                await NotificationService.create_notification(
                    db=db,
                    workspace_id=workspace_id,
                    recipient_id=uid,
                    actor_id=actor_id,
                    action_type="task_assigned",
                    entity_type="task",
                    entity_id=task.id,
                    message=f"{actor_name} assigned you to {task_label}: {task.title}",
                    payload={
                        "task_id": str(task.id),
                        "project_id": str(project_id),
                        "task_title": task.title,
                        "task_number": task_label,
                        "priority": task.priority,
                    },
                    deduplication_key=f"assign:{task.id}:{uid}",
                )

            for uid in removed_assignee_ids:
                await NotificationService.create_notification(
                    db=db,
                    workspace_id=workspace_id,
                    recipient_id=uid,
                    actor_id=actor_id,
                    action_type="task_unassigned",
                    entity_type="task",
                    entity_id=task.id,
                    message=f"{actor_name} unassigned you from {task_label}: {task.title}",
                    payload={
                        "task_id": str(task.id),
                        "project_id": str(project_id),
                        "task_title": task.title,
                        "task_number": task_label,
                    },
                    deduplication_key=f"unassign:{task.id}:{uid}:{task.version}",
                )

        # Transactional Outbox Event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace_id,
            event_type="task.updated",
            entity_type="task",
            entity_id=task.id,
            payload={
                "task_id": str(task.id),
                "project_id": str(project_id),
                "status_id": str(task.status_id),
                "title": task.title,
                "priority": task.priority,
                "rank": task.rank,
                "version": task.version,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            },
        )

        await db.commit()
        return await cls.get_task_details(db, workspace_id, project_id, task.id)

    @classmethod
    async def delete_task(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> bool:
        """Soft deletes the task."""
        stmt = (
            select(Task)
            .where(
                Task.id == task_id,
                Task.project_id == project_id,
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        task = res.scalars().first()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        task.deleted_at = datetime.now(timezone.utc)

        # Transactional Outbox Event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace_id,
            event_type="task.deleted",
            entity_type="task",
            entity_id=task.id,
            payload={
                "task_id": str(task.id),
                "project_id": str(project_id),
            },
        )

        await db.commit()
        return True

    @classmethod
    async def move_task(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project: Project,
        task_id: uuid.UUID,
        move: TaskMove,
        current_user: User | None = None,
    ) -> dict:
        """
        Executes deterministic task move under two-column status locks.
        Orders status locks by id ASC to eliminate AB-BA deadlocks.
        Allocates fractional indexing rank and rebalances if exhaustion occurs.
        """
        # 1. Lock task row FOR UPDATE and check version
        task_stmt = (
            select(Task)
            .where(
                Task.id == task_id,
                Task.project_id == project.id,
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
            )
            .with_for_update()
        )
        task_res = await db.execute(task_stmt)
        task = task_res.scalars().first()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Optimistic locking check
        if task.version != move.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"TASK_VERSION_CONFLICT: Expected version {move.version}, but task is at version {task.version}. Please refresh board.",
            )

        source_status_id = task.status_id
        dest_status_id = move.destination_status_id

        # 2. Acquire deterministic two-column status locks (ORDER BY id ASC FOR UPDATE)
        status_ids = sorted(list({source_status_id, dest_status_id}))
        status_lock_stmt = (
            select(TaskStatus)
            .where(
                TaskStatus.id.in_(status_ids),
                TaskStatus.project_id == project.id,
                TaskStatus.deleted_at.is_(None),
            )
            .order_by(TaskStatus.id.asc())
            .with_for_update()
        )
        locked_statuses = (await db.execute(status_lock_stmt)).scalars().all()

        if len(locked_statuses) != len(status_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more specified status columns do not exist in this project.",
            )

        # 3. Retrieve ranks of neighbor tasks if specified
        prev_rank: float | None = None
        next_rank: float | None = None

        if move.prev_task_id:
            prev_res = await db.execute(
                select(Task.rank).where(
                    Task.id == move.prev_task_id,
                    Task.project_id == project.id,
                    Task.status_id == dest_status_id,
                    Task.deleted_at.is_(None),
                )
            )
            prev_rank = prev_res.scalar()
            if prev_rank is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="prev_task_id not found in destination status column.",
                )

        if move.next_task_id:
            next_res = await db.execute(
                select(Task.rank).where(
                    Task.id == move.next_task_id,
                    Task.project_id == project.id,
                    Task.status_id == dest_status_id,
                    Task.deleted_at.is_(None),
                )
            )
            next_rank = next_res.scalar()
            if next_rank is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="next_task_id not found in destination status column.",
                )

        # 4. Calculate new fractional rank
        new_rank, needs_rebalance = fractional_index_service.calculate_rank(prev_rank, next_rank)

        # 5. Apply task update
        task.status_id = dest_status_id
        task.rank = new_rank
        task.version += 1

        # 6. Rebalance if rank exhaustion occurred
        if needs_rebalance:
            dest_tasks_stmt = (
                select(Task)
                .where(
                    Task.project_id == project.id,
                    Task.status_id == dest_status_id,
                    Task.deleted_at.is_(None),
                )
                .order_by(Task.rank.asc(), Task.id.asc())
                .with_for_update()
            )
            dest_tasks = list((await db.execute(dest_tasks_stmt)).scalars().all())
            items = [(t.id, t.rank) for t in dest_tasks]
            rebalanced_mapping = fractional_index_service.rebalance_ranks(items)

            rank_dict = dict(rebalanced_mapping)
            changed_payload = []
            for t in dest_tasks:
                if t.id in rank_dict:
                    t.rank = rank_dict[t.id]
                    t.version += 1
                    changed_payload.append({
                        "task_id": str(t.id),
                        "rank": t.rank,
                        "version": t.version,
                    })

            # Consolidated outbox event for rebalance
            await outbox_service.create_event(
                db=db,
                workspace_id=workspace_id,
                event_type="column.rebalanced",
                entity_type="task_status",
                entity_id=dest_status_id,
                payload={
                    "project_id": str(project.id),
                    "status_id": str(dest_status_id),
                    "tasks": changed_payload,
                },
            )

        # Transactional Outbox Event for task movement
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace_id,
            event_type="task.moved",
            entity_type="task",
            entity_id=task.id,
            payload={
                "task_id": str(task.id),
                "project_id": str(project.id),
                "source_status_id": str(source_status_id),
                "destination_status_id": str(dest_status_id),
                "rank": task.rank,
                "version": task.version,
            },
        )

        # Stage notifications to assignees if status changed across columns
        if source_status_id != dest_status_id:
            from app.services.notification import NotificationService
            actor_name = (current_user.full_name or current_user.email) if current_user else "A team member"
            actor_id = current_user.id if current_user else None

            dest_status_name = next((s.name for s in locked_statuses if s.id == dest_status_id), "another column")
            assignees_res = await db.execute(
                select(TaskAssignee.user_id).where(TaskAssignee.task_id == task.id)
            )
            assignee_ids = assignees_res.scalars().all()
            task_label = f"{project.key}-{task.task_number}"

            for uid in assignee_ids:
                await NotificationService.create_notification(
                    db=db,
                    workspace_id=workspace_id,
                    recipient_id=uid,
                    actor_id=actor_id,
                    action_type="task_status_changed",
                    entity_type="task",
                    entity_id=task.id,
                    message=f"{actor_name} moved {task_label} ({task.title}) to {dest_status_name}",
                    payload={
                        "task_id": str(task.id),
                        "project_id": str(project.id),
                        "status_id": str(dest_status_id),
                        "status_name": dest_status_name,
                        "task_title": task.title,
                        "task_number": task_label,
                    },
                    deduplication_key=f"status:{task.id}:{dest_status_id}:{task.version}",
                )

        await db.commit()
        return await cls.get_task_details(db, workspace_id, project.id, task.id, project_key=project.key)

    @classmethod
    async def get_board(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project: Project,
    ) -> dict:
        """Fetches the complete board structure with status columns and cards."""
        # 1. Fetch active statuses
        statuses_res = await db.execute(
            select(TaskStatus)
            .where(
                TaskStatus.project_id == project.id,
                TaskStatus.deleted_at.is_(None),
            )
            .order_by(TaskStatus.rank.asc(), TaskStatus.id.asc())
        )
        statuses = list(statuses_res.scalars().all())

        # 2. Fetch active tasks with assignees and tags
        tasks_res = await db.execute(
            select(Task)
            .where(
                Task.project_id == project.id,
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
            )
            .order_by(Task.status_id, Task.rank.asc(), Task.id.asc())
        )
        all_tasks = list(tasks_res.scalars().all())

        # Group tasks by status_id
        tasks_by_status: dict[uuid.UUID, list] = {s.id: [] for s in statuses}

        # Bulk load assignees & tags
        task_ids = [t.id for t in all_tasks]
        assignees_by_task: dict[uuid.UUID, list] = {tid: [] for tid in task_ids}
        tags_by_task: dict[uuid.UUID, list] = {tid: [] for tid in task_ids}

        if task_ids:
            a_stmt = (
                select(TaskAssignee.task_id, User)
                .join(User, User.id == TaskAssignee.user_id)
                .where(TaskAssignee.task_id.in_(task_ids))
            )
            a_rows = (await db.execute(a_stmt)).all()
            for tid, u in a_rows:
                assignees_by_task[tid].append({
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "avatar_url": u.avatar_url,
                })

            t_stmt = (
                select(TaskTag.task_id, Tag)
                .join(Tag, Tag.id == TaskTag.tag_id)
                .where(TaskTag.task_id.in_(task_ids))
            )
            t_rows = (await db.execute(t_stmt)).all()
            for tid, tag in t_rows:
                tags_by_task[tid].append({
                    "id": tag.id,
                    "name": tag.name,
                    "color_hex": tag.color_hex,
                })

        for t in all_tasks:
            t_dict = {
                "id": t.id,
                "workspace_id": t.workspace_id,
                "project_id": t.project_id,
                "status_id": t.status_id,
                "task_number": t.task_number,
                "task_key": f"{project.key}-{t.task_number}",
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "rank": t.rank,
                "version": t.version,
                "creator_id": t.creator_id,
                "due_date": t.due_date,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "assignees": assignees_by_task.get(t.id, []),
                "tags": tags_by_task.get(t.id, []),
            }
            if t.status_id in tasks_by_status:
                tasks_by_status[t.status_id].append(t_dict)

        columns = []
        for s in statuses:
            columns.append({
                "status": {
                    "id": s.id,
                    "workspace_id": s.workspace_id,
                    "project_id": s.project_id,
                    "name": s.name,
                    "rank": s.rank,
                    "color_hex": s.color_hex,
                    "is_completed_state": s.is_completed_state,
                },
                "tasks": tasks_by_status.get(s.id, []),
            })

        return {"project_id": project.id, "columns": columns}

    @classmethod
    async def get_roadmap(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project: Project,
    ) -> List[dict]:
        """Fetches roadmap view tasks ordered by due date, priority, and rank."""
        tasks_res = await db.execute(
            select(Task)
            .where(
                Task.project_id == project.id,
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
            )
            .order_by(
                Task.due_date.asc().nulls_last(),
                Task.rank.asc(),
            )
        )
        tasks = list(tasks_res.scalars().all())

        task_ids = [t.id for t in tasks]
        assignees_by_task: dict[uuid.UUID, list] = {tid: [] for tid in task_ids}
        if task_ids:
            a_stmt = (
                select(TaskAssignee.task_id, User)
                .join(User, User.id == TaskAssignee.user_id)
                .where(TaskAssignee.task_id.in_(task_ids))
            )
            a_rows = (await db.execute(a_stmt)).all()
            for tid, u in a_rows:
                assignees_by_task[tid].append({
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "avatar_url": u.avatar_url,
                })

        return [
            {
                "id": t.id,
                "workspace_id": t.workspace_id,
                "project_id": t.project_id,
                "status_id": t.status_id,
                "task_number": t.task_number,
                "task_key": f"{project.key}-{t.task_number}",
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "rank": t.rank,
                "version": t.version,
                "due_date": t.due_date,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "assignees": assignees_by_task.get(t.id, []),
                "tags": [],
            }
            for t in tasks
        ]


task_service = TaskService()
