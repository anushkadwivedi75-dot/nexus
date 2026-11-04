import asyncio
import json
import uuid
import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from app.core.redis import redis_client
from app.core.websocket_manager import websocket_manager
from app.main import app
from conftest import TestSessionLocal


async def create_user_and_token(client: AsyncClient, name: str) -> tuple[str, dict, dict]:
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    password = "StrongPassword123!"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["data"]["access_token"]
    user_data = reg_res.json()["data"]["user"]
    return token, {"Authorization": f"Bearer {token}"}, user_data


@pytest.mark.asyncio
async def test_ws_ticket_generation_and_single_use_getdel(client: AsyncClient):
    """
    Verifies that POST /api/v1/auth/ws-ticket generates a single-use 60-second UUID ticket,
    populates the user's workspaces in Redis, and cannot be reused after consumption.
    """
    _, headers, user = await create_user_and_token(client, "Ticket User")

    # Create a workspace
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Ticket WS", "slug": f"tws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    # 1. Request ticket
    t_res = await client.post("/api/v1/auth/ws-ticket", headers=headers)
    assert t_res.status_code == 200
    ticket_uuid = t_res.json()["data"]["ticket"]
    assert ticket_uuid is not None

    # 2. First consumption via GETDEL in Redis -> returns valid payload
    first_getdel = await redis_client.getdel(f"ws_ticket:{ticket_uuid}")
    assert first_getdel is not None
    data = json.loads(first_getdel)
    assert data["user_id"] == user["id"]
    assert ws_id in data["workspaces"]

    # 3. Second consumption -> returns None (single-use guarantee prevents replay attacks)
    second_getdel = await redis_client.getdel(f"ws_ticket:{ticket_uuid}")
    assert second_getdel is None


@pytest.mark.asyncio
async def test_websocket_lifecycle_and_channel_authorization(client: AsyncClient):
    """
    Verifies WebSocket handshake via ticket, connected welcome frame,
    ping/pong heartbeat, authorized workspace subscription,
    and rejection of unauthorized workspace subscriptions.
    """
    token, headers, user = await create_user_and_token(client, "Socket User")

    # Create workspace
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Socket WS", "slug": f"skws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    # Generate ticket
    t_res = await client.post("/api/v1/auth/ws-ticket", headers=headers)
    ticket_uuid = t_res.json()["data"]["ticket"]

    # Connect with TestClient (synchronous wrapper over ASGI websocket)
    with TestClient(app) as tc:
        with tc.websocket_connect(f"/ws?ticket={ticket_uuid}") as ws:
            # 1. Receive connected frame
            connected_frame = ws.receive_json()
            assert connected_frame["type"] == "connected"
            assert connected_frame["user_id"] == user["id"]

            # 2. Send ping -> receive heartbeat
            ws.send_json({"action": "ping"})
            heartbeat_frame = ws.receive_json()
            assert heartbeat_frame["type"] == "heartbeat"

            # 3. Subscribe to authorized workspace -> SUCCESS
            ws.send_json({"action": "subscribe", "channel": f"workspace:{ws_id}"})
            sub_frame = ws.receive_json()
            assert sub_frame["type"] == "subscribed"
            assert sub_frame["channel"] == f"workspace:{ws_id}"

            # 4. Subscribe to unauthorized workspace -> FORBIDDEN
            unauth_ws_id = str(uuid.uuid4())
            ws.send_json({"action": "subscribe", "channel": f"workspace:{unauth_ws_id}"})
            err_frame = ws.receive_json()
            assert err_frame["type"] == "error"
            assert err_frame["code"] == "FORBIDDEN"

            # 5. Unsubscribe from workspace
            ws.send_json({"action": "unsubscribe", "channel": f"workspace:{ws_id}"})
            unsub_frame = ws.receive_json()
            assert unsub_frame["type"] == "unsubscribed"


@pytest.mark.asyncio
async def test_websocket_redis_fanout_and_member_eviction(client: AsyncClient):
    """
    Verifies that domain events published to Redis fan out to subscribed WebSocket clients,
    and administrative eviction control signals terminate unauthorized connections.
    """
    token, headers, user = await create_user_and_token(client, "Eviction User")

    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Evict WS", "slug": f"evws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    t_res = await client.post("/api/v1/auth/ws-ticket", headers=headers)
    ticket_uuid = t_res.json()["data"]["ticket"]

    with TestClient(app) as tc:
        with tc.websocket_connect(f"/ws?ticket={ticket_uuid}") as ws:
            ws.receive_json()  # connected frame

            # Subscribe to workspace
            ws.send_json({"action": "subscribe", "channel": f"workspace:{ws_id}"})
            ws.receive_json()  # subscribed frame

            # Broadcast a test domain event directly to the channel via WebSocketManager
            test_event = {
                "schema_version": 1,
                "event_id": str(uuid.uuid4()),
                "event_type": "task.created",
                "workspace_id": ws_id,
                "entity_type": "task",
                "entity_id": str(uuid.uuid4()),
                "payload": {"title": "Real-time task"},
            }
            await websocket_manager.broadcast_to_channel(
                f"workspace:{ws_id}",
                json.dumps({"type": "event", "channel": f"workspace:{ws_id}", "data": test_event}),
            )

            # Client receives event frame
            received_event = ws.receive_json()
            assert received_event["type"] == "event"
            assert received_event["data"]["payload"]["title"] == "Real-time task"

            # Send administrative control signal: EVICT_WORKSPACE_MEMBER
            await websocket_manager.handle_control_invalidation({
                "action": "EVICT_WORKSPACE_MEMBER",
                "workspace_id": ws_id,
                "user_id": user["id"],
            })

            # Verify connection is terminated with code 4403
            import starlette.websockets
            with pytest.raises(starlette.websockets.WebSocketDisconnect) as exc_info:
                ws.receive_json()
            assert exc_info.value.code == 4403
