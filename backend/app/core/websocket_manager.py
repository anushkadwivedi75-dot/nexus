import asyncio
import json
import logging
import uuid
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import redis.asyncio as aioredis
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.workspace_member import WorkspaceMember

logger = logging.getLogger(__name__)


class WebSocketConnection:
    def __init__(
        self,
        websocket: WebSocket,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        authorized_workspaces: Set[str],
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.authorized_workspaces = authorized_workspaces
        self.subscriptions: Set[str] = set()
        self.send_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        self.send_task: asyncio.Task | None = None
        self.is_alive = True

    async def start_sender(self):
        self.send_task = asyncio.create_task(self._sender_loop())

    async def _sender_loop(self):
        try:
            while self.is_alive:
                msg = await self.send_queue.get()
                await self.websocket.send_text(msg)
                self.send_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Error in WebSocket sender loop for %s: %s", self.connection_id, e)
            self.is_alive = False

    async def enqueue(self, message: str) -> bool:
        if not self.is_alive:
            return False
        try:
            self.send_queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            logger.warning("SLOW_CLIENT_DROP: Queue full for connection %s; dropping frame.", self.connection_id)
            return False

    async def close(self, code: int = 1000, reason: str = ""):
        self.is_alive = False
        if self.send_task and not self.send_task.done():
            self.send_task.cancel()
        try:
            await self.websocket.close(code=code, reason=reason)
        except Exception:
            pass


class WebSocketManager:
    def __init__(self):
        # connection_id -> WebSocketConnection
        self.connections: Dict[uuid.UUID, WebSocketConnection] = {}
        # channel_name -> set(connection_id)
        self.channel_subscribers: Dict[str, Set[uuid.UUID]] = {}
        self._lock = asyncio.Lock()
        self._pubsub_task: asyncio.Task | None = None
        self._audit_task: asyncio.Task | None = None
        self._redis: aioredis.Redis | None = None

    async def register(
        self,
        websocket: WebSocket,
        user_id: uuid.UUID,
        authorized_workspaces: Set[str],
    ) -> WebSocketConnection:
        connection_id = uuid.uuid4()
        conn = WebSocketConnection(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            authorized_workspaces=authorized_workspaces,
        )
        async with self._lock:
            self.connections[connection_id] = conn
            # Automatically subscribe user to personal channel
            user_chan = f"user:{user_id}"
            conn.subscriptions.add(user_chan)
            if user_chan not in self.channel_subscribers:
                self.channel_subscribers[user_chan] = set()
            self.channel_subscribers[user_chan].add(connection_id)

        await conn.start_sender()
        logger.info("WebSocket connected: %s (user: %s)", connection_id, user_id)
        return conn

    async def unregister(self, connection_id: uuid.UUID):
        async with self._lock:
            conn = self.connections.pop(connection_id, None)
            if conn:
                for chan in conn.subscriptions:
                    if chan in self.channel_subscribers:
                        self.channel_subscribers[chan].discard(connection_id)
                        if not self.channel_subscribers[chan]:
                            del self.channel_subscribers[chan]
                await conn.close()
                logger.info("WebSocket disconnected: %s", connection_id)

    async def subscribe(
        self,
        connection_id: uuid.UUID,
        channel: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> dict:
        """
        Validates authorization for the channel and adds the subscription.
        """
        conn = self.connections.get(connection_id)
        if not conn:
            return {"type": "error", "code": "NOT_CONNECTED", "message": "Connection not found"}

        clean_channel = channel.strip()
        parts = clean_channel.split(":", 1)
        if len(parts) != 2:
            return {"type": "error", "code": "INVALID_CHANNEL", "message": "Invalid channel format"}

        prefix, target_id_str = parts[0], parts[1]

        # 1. Workspace channel validation
        if prefix == "workspace":
            if target_id_str not in conn.authorized_workspaces:
                return {
                    "type": "error",
                    "code": "FORBIDDEN",
                    "message": "User is not a member of this workspace",
                }

        # 2. Project channel validation
        elif prefix == "project":
            try:
                target_p_id = uuid.UUID(target_id_str)
            except ValueError:
                return {"type": "error", "code": "INVALID_ID", "message": "Invalid project UUID"}

            async with session_factory() as db:
                p_res = await db.execute(select(Project).where(Project.id == target_p_id, Project.deleted_at.is_(None)))
                project = p_res.scalars().first()
                if not project:
                    return {"type": "error", "code": "NOT_FOUND", "message": "Project not found"}

                # Check workspace membership
                if str(project.workspace_id) not in conn.authorized_workspaces:
                    return {"type": "error", "code": "FORBIDDEN", "message": "Access denied to project workspace"}

                # Check private project access
                if project.is_private:
                    # Check if user is lead or explicit member or admin/owner
                    pm_res = await db.execute(
                        select(ProjectMember.id).where(
                            ProjectMember.project_id == project.id,
                            ProjectMember.user_id == conn.user_id,
                        )
                    )
                    is_explicit_member = pm_res.scalars().first() is not None
                    is_lead = project.lead_id == conn.user_id

                    # Check workspace role
                    wm_res = await db.execute(
                        select(WorkspaceMember.role).where(
                            WorkspaceMember.workspace_id == project.workspace_id,
                            WorkspaceMember.user_id == conn.user_id,
                        )
                    )
                    role = wm_res.scalar()
                    is_admin_or_owner = role in ("owner", "admin")

                    if not (is_explicit_member or is_lead or is_admin_or_owner):
                        return {
                            "type": "error",
                            "code": "FORBIDDEN",
                            "message": "Access denied to private project",
                        }

        # 3. User channel validation (only self allowed)
        elif prefix == "user":
            if target_id_str != str(conn.user_id):
                return {"type": "error", "code": "FORBIDDEN", "message": "Cannot subscribe to other user's channel"}

        else:
            return {"type": "error", "code": "UNKNOWN_PREFIX", "message": f"Channel prefix '{prefix}' unsupported"}

        # Authorized -> register subscription
        async with self._lock:
            conn.subscriptions.add(clean_channel)
            if clean_channel not in self.channel_subscribers:
                self.channel_subscribers[clean_channel] = set()
            self.channel_subscribers[clean_channel].add(connection_id)

        logger.debug("Connection %s subscribed to %s", connection_id, clean_channel)
        return {"type": "subscribed", "channel": clean_channel}

    async def unsubscribe(self, connection_id: uuid.UUID, channel: str) -> dict:
        conn = self.connections.get(connection_id)
        if not conn:
            return {"type": "error", "code": "NOT_CONNECTED", "message": "Connection not found"}

        clean_channel = channel.strip()
        async with self._lock:
            conn.subscriptions.discard(clean_channel)
            if clean_channel in self.channel_subscribers:
                self.channel_subscribers[clean_channel].discard(connection_id)
                if not self.channel_subscribers[clean_channel]:
                    del self.channel_subscribers[clean_channel]

        return {"type": "unsubscribed", "channel": clean_channel}

    async def broadcast_to_channel(self, channel: str, message: str):
        """Fans out a message string to all local connections subscribed to channel."""
        subscribers = self.channel_subscribers.get(channel)
        if not subscribers:
            return

        conns = [self.connections.get(cid) for cid in list(subscribers)]
        for conn in conns:
            if conn and conn.is_alive:
                await conn.enqueue(message)

    async def handle_control_invalidation(self, control_msg: dict):
        """
        Executes real-time eviction on Redis control channel signals.
        """
        action = control_msg.get("action")
        user_id_str = control_msg.get("user_id")
        workspace_id_str = control_msg.get("workspace_id")
        project_id_str = control_msg.get("project_id")

        if not user_id_str:
            return

        target_user_id = uuid.UUID(user_id_str)

        # 1. Evict workspace member
        if action in ("EVICT_WORKSPACE_MEMBER", "UPDATE_WORKSPACE_PERMISSIONS"):
            async with self._lock:
                for conn_id, conn in list(self.connections.items()):
                    if conn.user_id == target_user_id:
                        if workspace_id_str and workspace_id_str in conn.authorized_workspaces:
                            if action == "EVICT_WORKSPACE_MEMBER":
                                conn.authorized_workspaces.discard(workspace_id_str)
                                # Remove all workspace-scoped subscriptions
                                ws_chan = f"workspace:{workspace_id_str}"
                                conn.subscriptions.discard(ws_chan)
                                if ws_chan in self.channel_subscribers:
                                    self.channel_subscribers[ws_chan].discard(conn_id)
                                # Evict socket with close code 4403
                                await conn.close(code=4403, reason="MEMBER_REMOVED_FROM_WORKSPACE")

        # 2. Revoke user sessions
        elif action == "REVOKE_USER_SESSIONS":
            async with self._lock:
                for conn_id, conn in list(self.connections.items()):
                    if conn.user_id == target_user_id:
                        await conn.close(code=4401, reason="TOKEN_REVOKED")

        # 3. Revoke project subscription
        elif action == "REVOKE_PROJECT_SUBSCRIPTION" and project_id_str:
            proj_chan = f"project:{project_id_str}"
            async with self._lock:
                for conn_id, conn in list(self.connections.items()):
                    if conn.user_id == target_user_id and proj_chan in conn.subscriptions:
                        conn.subscriptions.discard(proj_chan)
                        if proj_chan in self.channel_subscribers:
                            self.channel_subscribers[proj_chan].discard(conn_id)
                        revoked_frame = json.dumps({
                            "type": "subscription_revoked",
                            "channel": proj_chan,
                            "reason": "MEMBERSHIP_REVOKED",
                        })
                        await conn.enqueue(revoked_frame)

    async def start_redis_listener(self, redis: aioredis.Redis):
        """
        Background subscriber that consumes messages from Redis Pub/Sub
        and distributes them to local WebSocket connections.
        """
        self._redis = redis
        pubsub = redis.pubsub()
        await pubsub.psubscribe("workspace:*")
        await pubsub.psubscribe("user:*")
        await pubsub.subscribe("nexus:control:auth_invalidation")
        logger.info("WebSocketManager Redis Pub/Sub listener subscribed.")

        try:
            async for raw_message in pubsub.listen():
                if raw_message["type"] in ("message", "pmessage"):
                    channel = raw_message["channel"]
                    data = raw_message["data"]

                    if channel == "nexus:control:auth_invalidation":
                        try:
                            ctrl = json.loads(data)
                            await self.handle_control_invalidation(ctrl)
                        except Exception as e:
                            logger.error("Error processing control invalidation: %s", e)
                    else:
                        # Standard workspace domain event -> fan out to local subscribers
                        frame = json.dumps({
                            "type": "event",
                            "channel": channel,
                            "data": json.loads(data) if isinstance(data, str) else data,
                        })
                        await self.broadcast_to_channel(channel, frame)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Redis Pub/Sub listener error: %s", e, exc_info=True)
        finally:
            try:
                await pubsub.aclose()
            except Exception:
                pass

    async def start_periodic_audit(self, session_factory: async_sessionmaker[AsyncSession]):
        """
        Every 60s fail-safe audit: validates connected users' active workspace memberships.
        """
        while True:
            try:
                await asyncio.sleep(60.0)
                if not self.connections:
                    continue

                async with session_factory() as db:
                    for conn_id, conn in list(self.connections.items()):
                        # Check user active state
                        res = await db.execute(
                            select(WorkspaceMember.workspace_id).where(
                                WorkspaceMember.user_id == conn.user_id
                            )
                        )
                        active_ws_ids = {str(w) for w in res.scalars().all()}

                        # If user lost membership to any currently subscribed workspace:
                        for chan in list(conn.subscriptions):
                            if chan.startswith("workspace:"):
                                ws_id = chan.split(":", 1)[1]
                                if ws_id not in active_ws_ids:
                                    logger.warning(
                                        "AUDIT_EVICTION: Connection %s lost membership in %s",
                                        conn_id,
                                        ws_id,
                                    )
                                    await conn.close(code=4403, reason="MEMBER_REMOVED_FROM_WORKSPACE")
                                    await self.unregister(conn_id)
                                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in periodic audit revalidation: %s", e)


websocket_manager = WebSocketManager()
