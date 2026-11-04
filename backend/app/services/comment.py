import base64
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.comment_mention import CommentMention
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.comment import (
    CommentAuthor,
    CommentCreate,
    CommentCursorPagination,
    CommentMentionItem,
    CommentResponse,
    CommentUpdate,
)
from app.services.outbox import outbox_service


class CommentService:
    @staticmethod
    def _encode_cursor(created_at: datetime, comment_id: uuid.UUID) -> str:
        raw = f"{created_at.isoformat()}|{comment_id}"
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
                detail="Invalid pagination cursor format.",
            )

    @classmethod
    async def _verify_task_access(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user: User,
        user_role: str,
    ) -> Tuple[Task, Project]:
        """Ensures task exists in workspace and validates private project membership."""
        stmt = (
            select(Task, Project)
            .join(Project, Project.id == Task.project_id)
            .where(
                Task.id == task_id,
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
                Project.workspace_id == workspace_id,
                Project.deleted_at.is_(None),
            )
        )
        res = await db.execute(stmt)
        row = res.first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        task, project = row[0], row[1]

        # Enforce private project visibility
        if project.is_private and user_role not in ("owner", "admin"):
            member_stmt = select(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
            member_res = await db.execute(member_stmt)
            if not member_res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access tasks in this private project.",
                )

        return task, project

    @classmethod
    async def _resolve_mentions(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        content: str,
    ) -> List[Tuple[uuid.UUID, User]]:
        """
        Parses @username or @email_prefix or @[Full Name](uuid) syntax.
        Validates mentioned users against workspace membership in current workspace.
        Returns deduplicated list of (user_id, User).
        """
        # Match @[Name](uuid) explicit mention format
        explicit_matches = re.findall(r"@\[([^\]]+)\]\(([a-f0-9\-]{36})\)", content)
        explicit_user_ids: Set[uuid.UUID] = set()
        for _, uid_str in explicit_matches:
            try:
                explicit_user_ids.add(uuid.UUID(uid_str))
            except ValueError:
                pass

        # Match simple @handle tokens (alphanumeric, underscore, period)
        simple_handles = set(re.findall(r"@([a-zA-Z0-9_.-]+)", content))

        resolved: Dict[uuid.UUID, User] = {}

        # 1. Resolve explicit IDs verified against workspace membership
        if explicit_user_ids:
            exp_stmt = (
                select(User)
                .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
                .where(
                    WorkspaceMember.workspace_id == workspace_id,
                    User.id.in_(list(explicit_user_ids)),
                )
            )
            exp_res = await db.execute(exp_stmt)
            for u in exp_res.scalars().all():
                resolved[u.id] = u

        # 2. Resolve simple handles (e.g. @alex or @alex.vance)
        if simple_handles:
            # Look up workspace members whose email prefix or full name matches
            mem_stmt = (
                select(User)
                .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
                .where(WorkspaceMember.workspace_id == workspace_id)
            )
            mem_res = await db.execute(mem_stmt)
            all_members = mem_res.scalars().all()

            for handle in simple_handles:
                clean_handle = handle.lower().strip()
                for u in all_members:
                    email_prefix = u.email.split("@")[0].lower()
                    name_slug = re.sub(r"\s+", "", u.full_name.lower()) if u.full_name else ""
                    first_name = u.full_name.split()[0].lower() if u.full_name else ""

                    if clean_handle in (email_prefix, name_slug, first_name):
                        resolved[u.id] = u

        return list(resolved.items())

    @classmethod
    async def create_comment(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        author: User,
        user_role: str,
        data: CommentCreate,
    ) -> CommentResponse:
        """Creates a comment or reply with thread validation, mention detection, and outbox event."""
        task, project = await cls._verify_task_access(db, workspace_id, task_id, author, user_role)

        # Validate parent comment if this is a reply
        if data.parent_comment_id:
            parent_stmt = select(Comment).where(
                Comment.id == data.parent_comment_id,
                Comment.workspace_id == workspace_id,
            )
            parent_res = await db.execute(parent_stmt)
            parent = parent_res.scalars().first()

            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found.")

            if parent.task_id != task_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent comment does not belong to this task.",
                )

            if parent.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot reply to a deleted comment.",
                )

            # Enforce 1-level thread depth: replies can only be made to top-level comments
            if parent.parent_comment_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nested replies beyond 1 level are not permitted.",
                )

        # Create comment entity
        comment = Comment(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            task_id=task_id,
            author_id=author.id,
            parent_comment_id=data.parent_comment_id,
            content=data.content,
            version=1,
        )
        db.add(comment)
        await db.flush()

        # Resolve and persist member mentions
        mentions = await cls._resolve_mentions(db, workspace_id, data.content)
        mention_items: List[CommentMentionItem] = []
        for uid, user_obj in mentions:
            db.add(
                CommentMention(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    comment_id=comment.id,
                    mentioned_user_id=uid,
                )
            )
            mention_items.append(
                CommentMentionItem(
                    user_id=uid,
                    full_name=user_obj.full_name,
                    email=user_obj.email,
                )
            )

        # Stage transactional outbox event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace_id,
            event_type="comment.created",
            entity_type="comment",
            entity_id=comment.id,
            actor_id=author.id,
            payload={
                "comment_id": str(comment.id),
                "task_id": str(task_id),
                "project_id": str(project.id),
                "parent_comment_id": str(data.parent_comment_id) if data.parent_comment_id else None,
                "author_id": str(author.id),
                "content": comment.content,
                "version": comment.version,
                "created_at": comment.created_at.isoformat(),
                "mentioned_user_ids": [str(uid) for uid, _ in mentions],
            },
        )

        await db.commit()
        await db.refresh(comment)

        author_info = CommentAuthor(
            id=author.id,
            full_name=author.full_name,
            email=author.email,
            avatar_url=author.avatar_url,
        )

        return CommentResponse(
            id=comment.id,
            workspace_id=comment.workspace_id,
            task_id=comment.task_id,
            author_id=comment.author_id,
            author=author_info,
            parent_comment_id=comment.parent_comment_id,
            content=comment.content,
            is_deleted=False,
            version=comment.version,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            reply_count=0,
            replies=[],
            mentions=mention_items,
        )

    @classmethod
    async def list_comments(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        current_user: User,
        user_role: str,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> CommentCursorPagination:
        """Fetches top-level comments with cursor pagination and attaches their 1-level replies."""
        await cls._verify_task_access(db, workspace_id, task_id, current_user, user_role)
        page_size = max(1, min(limit, 50))

        # 1. Fetch top-level comments (parent_comment_id IS NULL)
        top_query = (
            select(Comment)
            .where(
                Comment.workspace_id == workspace_id,
                Comment.task_id == task_id,
                Comment.parent_comment_id.is_(None),
            )
        )

        if cursor:
            cursor_dt, cursor_id = cls._decode_cursor(cursor)
            top_query = top_query.where(
                (Comment.created_at > cursor_dt)
                | ((Comment.created_at == cursor_dt) & (Comment.id > cursor_id))
            )

        top_query = top_query.order_by(Comment.created_at.asc(), Comment.id.asc()).limit(page_size + 1)
        res = await db.execute(top_query)
        top_comments = list(res.scalars().all())

        has_more = len(top_comments) > page_size
        if has_more:
            top_comments = top_comments[:page_size]

        next_cursor = None
        if top_comments and has_more:
            last = top_comments[-1]
            next_cursor = cls._encode_cursor(last.created_at, last.id)

        top_ids = [c.id for c in top_comments]

        # 2. Fetch all replies for these top-level comments in one batch
        replies_by_parent: Dict[uuid.UUID, List[Comment]] = {cid: [] for cid in top_ids}
        all_comment_ids = list(top_ids)

        if top_ids:
            reply_stmt = (
                select(Comment)
                .where(
                    Comment.workspace_id == workspace_id,
                    Comment.task_id == task_id,
                    Comment.parent_comment_id.in_(top_ids),
                )
                .order_by(Comment.created_at.asc(), Comment.id.asc())
            )
            reply_res = await db.execute(reply_stmt)
            for r in reply_res.scalars().all():
                if r.parent_comment_id in replies_by_parent:
                    replies_by_parent[r.parent_comment_id].append(r)
                all_comment_ids.append(r.id)

        # 3. Batch load authors to prevent N+1 queries
        all_author_ids: Set[uuid.UUID] = set()
        for c in top_comments:
            if c.author_id:
                all_author_ids.add(c.author_id)
        for replies in replies_by_parent.values():
            for r in replies:
                if r.author_id:
                    all_author_ids.add(r.author_id)

        authors_by_id: Dict[uuid.UUID, CommentAuthor] = {}
        if all_author_ids:
            authors_stmt = select(User).where(User.id.in_(list(all_author_ids)))
            authors_res = await db.execute(authors_stmt)
            for u in authors_res.scalars().all():
                authors_by_id[u.id] = CommentAuthor(
                    id=u.id,
                    full_name=u.full_name,
                    email=u.email,
                    avatar_url=u.avatar_url,
                )

        # 4. Batch load mentions
        mentions_by_comment: Dict[uuid.UUID, List[CommentMentionItem]] = {cid: [] for cid in all_comment_ids}
        if all_comment_ids:
            m_stmt = (
                select(CommentMention, User)
                .join(User, User.id == CommentMention.mentioned_user_id)
                .where(CommentMention.comment_id.in_(all_comment_ids))
            )
            m_res = await db.execute(m_stmt)
            for cm, u in m_res.all():
                mentions_by_comment[cm.comment_id].append(
                    CommentMentionItem(
                        user_id=u.id,
                        full_name=u.full_name,
                        email=u.email,
                    )
                )

        # 5. Format responses
        def format_comment(c: Comment, child_replies: List[CommentResponse] = None) -> CommentResponse:
            is_deleted = c.deleted_at is not None
            display_content = "[This comment has been deleted.]" if is_deleted else c.content
            author_info = None if is_deleted else (authors_by_id.get(c.author_id) if c.author_id else None)

            return CommentResponse(
                id=c.id,
                workspace_id=c.workspace_id,
                task_id=c.task_id,
                author_id=None if is_deleted else c.author_id,
                author=author_info,
                parent_comment_id=c.parent_comment_id,
                content=display_content,
                is_deleted=is_deleted,
                version=c.version,
                created_at=c.created_at,
                updated_at=c.updated_at,
                reply_count=len(child_replies) if child_replies else 0,
                replies=child_replies or [],
                mentions=mentions_by_comment.get(c.id, []) if not is_deleted else [],
            )

        items: List[CommentResponse] = []
        for top in top_comments:
            raw_replies = replies_by_parent.get(top.id, [])
            formatted_replies = [format_comment(r) for r in raw_replies]
            items.append(format_comment(top, formatted_replies))

        return CommentCursorPagination(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @classmethod
    async def update_comment(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        comment_id: uuid.UUID,
        current_user: User,
        data: CommentUpdate,
    ) -> CommentResponse:
        """Updates a comment with author validation, optimistic concurrency version check, and outbox event."""
        stmt = (
            select(Comment)
            .where(
                Comment.id == comment_id,
                Comment.workspace_id == workspace_id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        comment = res.scalars().first()

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

        if comment.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a deleted comment.")

        # Author authorization
        if comment.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this comment.",
            )

        # Optimistic concurrency check
        if comment.version != data.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"COMMENT_VERSION_CONFLICT: Expected version {data.version}, but comment is at version {comment.version}. Please refresh.",
            )

        comment.content = data.content
        comment.version += 1

        # Refresh mentions
        # Remove existing mentions
        old_m_stmt = select(CommentMention).where(CommentMention.comment_id == comment.id)
        old_mentions = (await db.execute(old_m_stmt)).scalars().all()
        for om in old_mentions:
            await db.delete(om)

        new_mentions = await cls._resolve_mentions(db, workspace_id, data.content)
        mention_items: List[CommentMentionItem] = []
        for uid, user_obj in new_mentions:
            db.add(
                CommentMention(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    comment_id=comment.id,
                    mentioned_user_id=uid,
                )
            )
            mention_items.append(
                CommentMentionItem(
                    user_id=uid,
                    full_name=user_obj.full_name,
                    email=user_obj.email,
                )
            )

        # Transactional Outbox Event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace_id,
            event_type="comment.updated",
            entity_type="comment",
            entity_id=comment.id,
            actor_id=current_user.id,
            payload={
                "comment_id": str(comment.id),
                "task_id": str(comment.task_id),
                "content": comment.content,
                "version": comment.version,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else datetime.now(timezone.utc).isoformat(),
            },
        )

        await db.commit()
        await db.refresh(comment)

        author_info = CommentAuthor(
            id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            avatar_url=current_user.avatar_url,
        )

        return CommentResponse(
            id=comment.id,
            workspace_id=comment.workspace_id,
            task_id=comment.task_id,
            author_id=comment.author_id,
            author=author_info,
            parent_comment_id=comment.parent_comment_id,
            content=comment.content,
            is_deleted=False,
            version=comment.version,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            reply_count=0,
            replies=[],
            mentions=mention_items,
        )

    @classmethod
    async def delete_comment(
        cls,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        comment_id: uuid.UUID,
        current_user: User,
        user_role: str,
    ) -> bool:
        """Soft-deletes a comment preserving thread integrity, validating author or admin moderation."""
        stmt = (
            select(Comment)
            .where(
                Comment.id == comment_id,
                Comment.workspace_id == workspace_id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        comment = res.scalars().first()

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

        if comment.deleted_at is not None:
            return True  # Idempotent soft delete

        is_author = comment.author_id == current_user.id
        is_admin_or_owner = user_role in ("owner", "admin")

        if not (is_author or is_admin_or_owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this comment.",
            )

        comment.deleted_at = datetime.now(timezone.utc)
        comment.version += 1

        # Transactional Outbox Event
        await outbox_service.create_event(
            db=db,
            workspace_id=workspace_id,
            event_type="comment.deleted",
            entity_type="comment",
            entity_id=comment.id,
            actor_id=current_user.id,
            payload={
                "comment_id": str(comment.id),
                "task_id": str(comment.task_id),
                "parent_comment_id": str(comment.parent_comment_id) if comment.parent_comment_id else None,
            },
        )

        await db.commit()
        return True

