import base64
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.notification import (
    NotificationActor,
    NotificationCursorPagination,
    NotificationResponse,
)
from app.services.outbox import outbox_service


class NotificationService:
    @staticmethod
    def _encode_cursor(created_at: datetime, notif_id: uuid.UUID) -> str:
        raw = f"{created_at.isoformat()}|{notif_id}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _decode_cursor(cursor_str: str) -> Tuple[datetime, uuid.UUID]:
        try:
            raw = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
            dt_str, id_str = raw.split("|", 1)
            return datetime.fromisoformat(dt_str), uuid.UUID(id_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid notification pagination cursor format.",
            )

    @classmethod
    async def create_notification(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        recipient_id: uuid.UUID,
        actor_id: Optional[uuid.UUID],
        action_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        deduplication_key: Optional[str] = None,
    ) -> Optional[Notification]:
        """
        Atomically creates an in-app notification and stages a recipient-targeted outbox event.
        Suppresses self-notifications, validates workspace membership, and prevents duplicate records.
        """
        # 1. Suppress actor self-notification
        if actor_id and recipient_id == actor_id:
            return None

        # 2. Validate recipient is an active member of this workspace
        mem_stmt = select(WorkspaceMember.id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == recipient_id,
        )
        mem_res = await db.execute(mem_stmt)
        if not mem_res.scalars().first():
            return None

        # 3. Deduplication check
        if deduplication_key:
            dedup_stmt = select(Notification).where(
                Notification.workspace_id == workspace_id,
                Notification.recipient_id == recipient_id,
                Notification.deduplication_key == deduplication_key,
                Notification.archived_at.is_(None),
            )
            existing = (await db.execute(dedup_stmt)).scalars().first()
            if existing:
                return existing

        now = datetime.now(timezone.utc)
        notif = Notification(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            recipient_id=recipient_id,
            actor_id=actor_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            message=message,
            payload=payload or {},
            is_read=False,
            deduplication_key=deduplication_key,
            created_at=now,
        )
        db.add(notif)
        await db.flush()

        # 4. Stage recipient-targeted transactional outbox event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace_id,
            event_type="notification.created",
            entity_type="notification",
            entity_id=notif.id,
            actor_id=actor_id,
            channel=f"user:{recipient_id}",
            payload={
                "notification_id": str(notif.id),
                "workspace_id": str(workspace_id),
                "recipient_id": str(recipient_id),
                "actor_id": str(actor_id) if actor_id else None,
                "action_type": action_type,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "message": message,
                "payload": payload or {},
                "created_at": notif.created_at.isoformat(),
            },
        )

        return notif

    @classmethod
    async def list_notifications(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
        is_read: Optional[bool] = None,
        include_archived: bool = False,
        action_type: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> NotificationCursorPagination:
        """Fetches recipient's notifications with cursor pagination and batch-loaded actors."""
        page_size = max(1, min(limit, 50))

        query = select(Notification).where(Notification.recipient_id == user_id)

        if not include_archived:
            query = query.where(Notification.archived_at.is_(None))

        if workspace_id:
            query = query.where(Notification.workspace_id == workspace_id)

        if is_read is not None:
            query = query.where(Notification.is_read == is_read)

        if action_type:
            query = query.where(Notification.action_type == action_type)

        if cursor:
            cursor_dt, cursor_id = cls._decode_cursor(cursor)
            query = query.where(
                (Notification.created_at < cursor_dt)
                | ((Notification.created_at == cursor_dt) & (Notification.id < cursor_id))
            )

        query = query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(page_size + 1)
        res = await db.execute(query)
        notifications = list(res.scalars().all())

        has_more = len(notifications) > page_size
        if has_more:
            notifications = notifications[:page_size]

        next_cursor = None
        if notifications and has_more:
            last = notifications[-1]
            next_cursor = cls._encode_cursor(last.created_at, last.id)

        # Batch load actors to eliminate N+1 queries
        actor_ids: Set[uuid.UUID] = {n.actor_id for n in notifications if n.actor_id}
        actors_by_id: Dict[uuid.UUID, NotificationActor] = {}
        if actor_ids:
            actors_stmt = select(User).where(User.id.in_(list(actor_ids)))
            actors_res = await db.execute(actors_stmt)
            for u in actors_res.scalars().all():
                actors_by_id[u.id] = NotificationActor(
                    id=u.id,
                    full_name=u.full_name,
                    email=u.email,
                    avatar_url=u.avatar_url,
                )

        # Compute unread count
        unread_count = await cls.get_unread_count(db, user_id, workspace_id)

        items = [
            NotificationResponse(
                id=n.id,
                workspace_id=n.workspace_id,
                recipient_id=n.recipient_id,
                actor_id=n.actor_id,
                actor=actors_by_id.get(n.actor_id) if n.actor_id else None,
                action_type=n.action_type,
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                message=n.message,
                payload=n.payload or {},
                is_read=n.is_read,
                read_at=n.read_at,
                archived_at=n.archived_at,
                created_at=n.created_at,
            )
            for n in notifications
        ]

        return NotificationCursorPagination(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            unread_count=unread_count,
        )

    @classmethod
    async def get_unread_count(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Returns the recipient's unread, unarchived notifications count."""
        stmt = (
            select(func.count(Notification.id))
            .where(
                Notification.recipient_id == user_id,
                Notification.is_read.is_(False),
                Notification.archived_at.is_(None),
            )
        )
        if workspace_id:
            stmt = stmt.where(Notification.workspace_id == workspace_id)

        res = await db.execute(stmt)
        return res.scalar_one() or 0

    @classmethod
    async def mark_as_read(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> NotificationResponse:
        """Marks a notification as read and emits a real-time event on user channel."""
        stmt = (
            select(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_id == user_id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        notif = res.scalars().first()

        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)

            await outbox_service.create_event(
                db=db,
                workspace_id=notif.workspace_id,
                event_type="notification.read",
                entity_type="notification",
                entity_id=notif.id,
                channel=f"user:{user_id}",
                payload={
                    "notification_id": str(notif.id),
                    "read_at": notif.read_at.isoformat(),
                },
            )
            await db.commit()
            await db.refresh(notif)

        actor_info = None
        if notif.actor_id:
            u_stmt = select(User).where(User.id == notif.actor_id)
            u_res = await db.execute(u_stmt)
            u = u_res.scalars().first()
            if u:
                actor_info = NotificationActor(id=u.id, full_name=u.full_name, email=u.email, avatar_url=u.avatar_url)

        return NotificationResponse(
            id=notif.id,
            workspace_id=notif.workspace_id,
            recipient_id=notif.recipient_id,
            actor_id=notif.actor_id,
            actor=actor_info,
            action_type=notif.action_type,
            entity_type=notif.entity_type,
            entity_id=notif.entity_id,
            message=notif.message,
            payload=notif.payload or {},
            is_read=notif.is_read,
            read_at=notif.read_at,
            archived_at=notif.archived_at,
            created_at=notif.created_at,
        )

    @classmethod
    async def mark_as_unread(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> NotificationResponse:
        """Marks a notification as unread and emits a real-time event on user channel."""
        stmt = (
            select(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_id == user_id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        notif = res.scalars().first()

        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

        if notif.is_read:
            notif.is_read = False
            notif.read_at = None

            await outbox_service.create_event(
                db=db,
                workspace_id=notif.workspace_id,
                event_type="notification.unread",
                entity_type="notification",
                entity_id=notif.id,
                channel=f"user:{user_id}",
                payload={
                    "notification_id": str(notif.id),
                },
            )
            await db.commit()
            await db.refresh(notif)

        actor_info = None
        if notif.actor_id:
            u_stmt = select(User).where(User.id == notif.actor_id)
            u_res = await db.execute(u_stmt)
            u = u_res.scalars().first()
            if u:
                actor_info = NotificationActor(id=u.id, full_name=u.full_name, email=u.email, avatar_url=u.avatar_url)

        return NotificationResponse(
            id=notif.id,
            workspace_id=notif.workspace_id,
            recipient_id=notif.recipient_id,
            actor_id=notif.actor_id,
            actor=actor_info,
            action_type=notif.action_type,
            entity_type=notif.entity_type,
            entity_id=notif.entity_id,
            message=notif.message,
            payload=notif.payload or {},
            is_read=notif.is_read,
            read_at=notif.read_at,
            archived_at=notif.archived_at,
            created_at=notif.created_at,
        )

    @classmethod
    async def mark_all_as_read(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Atomic bulk mark-as-read for current user."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_read.is_(False),
                Notification.archived_at.is_(None),
            )
            .values(is_read=True, read_at=now)
        )
        if workspace_id:
            stmt = stmt.where(Notification.workspace_id == workspace_id)

        res = await db.execute(stmt)
        count = res.rowcount

        # Stage outbox event
        target_ws_id = workspace_id
        if not target_ws_id:
            mem_stmt = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id).limit(1)
            target_ws_id = (await db.execute(mem_stmt)).scalar()

        if target_ws_id:
            await outbox_service.create_event(
                db=db,
                workspace_id=target_ws_id,
                event_type="notification.read_all",
                entity_type="notification",
                entity_id=user_id,
                channel=f"user:{user_id}",
                payload={
                    "marked_count": count,
                    "read_at": now.isoformat(),
                },
            )

        await db.commit()
        return count

    @classmethod
    async def archive_notification(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> bool:
        """Archives a notification, removing it from default inbox queries."""
        stmt = (
            select(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_id == user_id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        notif = res.scalars().first()

        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

        if notif.archived_at is None:
            now = datetime.now(timezone.utc)
            notif.archived_at = now
            await outbox_service.create_event(
                db=db,
                workspace_id=notif.workspace_id,
                event_type="notification.archived",
                entity_type="notification",
                entity_id=notif.id,
                channel=f"user:{user_id}",
                payload={
                    "notification_id": str(notif.id),
                    "archived_at": now.isoformat(),
                },
            )
            await db.commit()

        return True
