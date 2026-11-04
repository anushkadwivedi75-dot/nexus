import json
import logging
import time
import uuid
from typing import Set
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.redis import get_user_revocation_epoch, redis_client
from app.core.websocket_manager import websocket_manager
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.services.token import token_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: str | None = Query(default=None),
    token: str | None = Query(default=None),
):
    """
    Authenticated WebSocket connection endpoint.
    Performs handshake validation via single-use ticket (Redis GETDEL) or JWT token,
    checks revocation epoch, and enters client event/subscription protocol loop.
    """
    user_id: uuid.UUID | None = None
    authorized_workspaces: Set[str] = set()

    # 1. Ticket-based handshake authentication (Primary per Section 12.1)
    if ticket:
        try:
            ticket_raw = await redis_client.getdel(f"ws_ticket:{ticket}")
            if not ticket_raw:
                await websocket.close(code=4401, reason="INVALID_OR_EXPIRED_TICKET")
                return
            ticket_data = json.loads(ticket_raw)
            user_id = uuid.UUID(ticket_data["user_id"])
            authorized_workspaces = set(ticket_data.get("workspaces", []))
        except Exception as e:
            logger.warning("WebSocket ticket validation failure: %s", e)
            await websocket.close(code=4401, reason="INVALID_TICKET_PAYLOAD")
            return

    # 2. Direct token handshake authentication (Fallback / dev convenience)
    elif token:
        try:
            payload = token_service.decode_access_token(token)
            user_id = uuid.UUID(payload["sub"])
            token_iat = payload.get("iat", 0)

            # Check revocation epoch in Redis
            epoch = await get_user_revocation_epoch(str(user_id))
            if epoch and token_iat < epoch:
                await websocket.close(code=4401, reason="TOKEN_REVOKED")
                return

            # Fetch active workspaces
            async with AsyncSessionLocal() as db:
                stmt = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
                res = await db.execute(stmt)
                authorized_workspaces = {str(wid) for wid in res.scalars().all()}
        except Exception as e:
            logger.warning("WebSocket token validation failure: %s", e)
            await websocket.close(code=4401, reason="INVALID_TOKEN")
            return

    else:
        await websocket.close(code=4401, reason="MISSING_CREDENTIALS")
        return

    # 3. Verify user active state in DB
    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = user_res.scalars().first()
        if not user:
            await websocket.close(code=4403, reason="USER_INACTIVE")
            return

    # 4. Accept connection and register
    await websocket.accept()
    conn = await websocket_manager.register(websocket, user_id, authorized_workspaces)

    # Send connected handshake frame
    await conn.enqueue(json.dumps({
        "type": "connected",
        "connection_id": str(conn.connection_id),
        "user_id": str(conn.user_id),
    }))

    # 5. Message loop
    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                await conn.enqueue(json.dumps({
                    "type": "error",
                    "code": "BAD_JSON",
                    "message": "Malformed JSON payload",
                }))
                continue

            action = msg.get("action")

            if action == "ping":
                await conn.enqueue(json.dumps({
                    "type": "heartbeat",
                    "timestamp": time.time(),
                }))

            elif action == "subscribe":
                channel = msg.get("channel")
                if not channel:
                    await conn.enqueue(json.dumps({
                        "type": "error",
                        "code": "MISSING_CHANNEL",
                        "message": "Missing channel argument",
                    }))
                    continue
                result = await websocket_manager.subscribe(conn.connection_id, channel, AsyncSessionLocal)
                await conn.enqueue(json.dumps(result))

            elif action == "unsubscribe":
                channel = msg.get("channel")
                if not channel:
                    await conn.enqueue(json.dumps({
                        "type": "error",
                        "code": "MISSING_CHANNEL",
                        "message": "Missing channel argument",
                    }))
                    continue
                result = await websocket_manager.unsubscribe(conn.connection_id, channel)
                await conn.enqueue(json.dumps(result))

            else:
                await conn.enqueue(json.dumps({
                    "type": "error",
                    "code": "UNKNOWN_ACTION",
                    "message": f"Action '{action}' is not supported",
                }))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: %s", conn.connection_id)
    except Exception as e:
        logger.debug("WebSocket error on connection %s: %s", conn.connection_id, e)
    finally:
        await websocket_manager.unregister(conn.connection_id)

