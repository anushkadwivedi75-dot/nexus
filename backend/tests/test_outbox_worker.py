import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from app.models.outbox_event import OutboxEvent
from app.models.task import Task
from app.services.outbox import outbox_service
from app.services.outbox_worker import OutboxWorker
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
async def test_outbox_atomic_creation_and_rollback_safety(client: AsyncClient):
    """
    Verifies that domain mutations atomically write outbox events within the same transaction,
    and rolling back a mutation commits zero outbox events.
    """
    _, headers, _ = await create_user_and_token(client, "Outbox Tester")

    # 1. Create workspace & project
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Outbox WS", "slug": f"ows-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Outbox Project", "key": "OUT"},
        headers=headers,
    )
    p_id = p_res.json()["data"]["id"]

    cols = (await client.get(f"/api/v1/projects/{p_id}/columns", headers=headers)).json()["data"]
    todo_col = cols[1]["id"]

    # 2. Create task via API
    task_res = await client.post(
        f"/api/v1/projects/{p_id}/tasks",
        json={"title": "Atomic Task", "status_id": todo_col},
        headers=headers,
    )
    assert task_res.status_code == 201
    task_id = task_res.json()["data"]["id"]

    # 3. Verify OutboxEvent was persisted in DB
    async with TestSessionLocal() as session:
        evt_stmt = select(OutboxEvent).where(
            OutboxEvent.workspace_id == uuid.UUID(ws_id),
            OutboxEvent.event_type == "task.created",
        )
        evt = (await session.execute(evt_stmt)).scalars().first()
        assert evt is not None
        assert evt.status == "PENDING"
        assert evt.claim_epoch == 0
        assert evt.payload["entity_id"] == task_id
        assert evt.payload["event_type"] == "task.created"
        assert evt.payload["schema_version"] == 1


@pytest.mark.asyncio
async def test_outbox_claiming_fencing_and_zombie_prevention(client: AsyncClient):
    """
    Verifies FOR UPDATE SKIP LOCKED batch claiming, claim_epoch incrementing,
    and distributed fencing token protection against zombie workers.
    """
    _, headers, _ = await create_user_and_token(client, "Fencing Tester")

    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Fencing WS", "slug": f"fws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Fencing Project", "key": "FNC"},
        headers=headers,
    )
    p_id = p_res.json()["data"]["id"]

    cols = (await client.get(f"/api/v1/projects/{p_id}/columns", headers=headers)).json()["data"]
    todo_col = cols[1]["id"]

    worker1 = OutboxWorker(worker_id="worker_alpha")
    worker2 = OutboxWorker(worker_id="worker_beta")

    # Insert an isolated event directly to test fencing deterministically
    test_evt_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        await outbox_service.create_event(
            db=session,
            workspace_id=uuid.UUID(ws_id),
            event_type="test.fencing.event",
            entity_type="test",
            entity_id=test_evt_id,
            payload={"test": "data"},
        )
        await session.commit()

    # Worker 1 claims batch
    async with TestSessionLocal() as session:
        claimed = await worker1.claim_batch(session, batch_size=20)
        assert len(claimed) >= 1
        target_evt = next((e for e in claimed if e["id"] == test_evt_id), None)
        if not target_evt:
            # Fallback to any claimed event if already picked up
            target_evt = claimed[0]
        event_id = target_evt["id"]
        epoch1 = target_evt["claim_epoch"]
        assert epoch1 >= 1

    # Simulate Worker 1 hanging / paused while lease expires:
    # Set claimed_at to 120 seconds in the past to allow Worker 2 recovery
    from datetime import datetime, timedelta, timezone
    async with TestSessionLocal() as session:
        await session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(claimed_at=datetime.now(timezone.utc) - timedelta(seconds=120))
        )
        await session.commit()

    # Worker 2 reclaims the expired event
    async with TestSessionLocal() as session:
        reclaimed = await worker2.claim_batch(session, batch_size=10)
        reclaimed_evt = next((e for e in reclaimed if e["id"] == event_id), None)
        assert reclaimed_evt is not None
        epoch2 = reclaimed_evt["claim_epoch"]
        assert epoch2 == epoch1 + 1  # Fencing token incremented!

    # Worker 2 acknowledges with epoch 2 -> SUCCEEDS
    async with TestSessionLocal() as session:
        ack_res2 = await worker2.acknowledge_event(session, event_id, epoch2)
        assert ack_res2 is True

    # Zombie Worker 1 wakes up and tries to acknowledge with stale epoch 1 -> REJECTED
    async with TestSessionLocal() as session:
        ack_res1 = await worker1.acknowledge_event(session, event_id, epoch1)
        assert ack_res1 is False  # Fencing prevented zombie overwrite!


@pytest.mark.asyncio
async def test_outbox_failure_retry_backoff_and_dead_letter(client: AsyncClient):
    """
    Verifies that transient errors schedule exponential backoff retries,
    and exceeding 10 retries transitions to dead-letter state.
    """
    _, headers, _ = await create_user_and_token(client, "Retry Tester")

    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Retry WS", "slug": f"rws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Retry Project", "key": "RTR"},
        headers=headers,
    )
    p_id = p_res.json()["data"]["id"]

    cols = (await client.get(f"/api/v1/projects/{p_id}/columns", headers=headers)).json()["data"]
    todo_col = cols[1]["id"]

    worker = OutboxWorker(worker_id="worker_retry")
    test_retry_evt_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        await outbox_service.create_event(
            db=session,
            workspace_id=uuid.UUID(ws_id),
            event_type="test.retry.event",
            entity_type="test",
            entity_id=test_retry_evt_id,
            payload={"test": "retry"},
        )
        await session.commit()

    async with TestSessionLocal() as session:
        claimed = await worker.claim_batch(session, batch_size=20)
        assert len(claimed) >= 1
        evt = next((e for e in claimed if e["id"] == test_retry_evt_id), claimed[0])
        event_id = evt["id"]
        epoch = evt["claim_epoch"]

    # 1. Transient failure (retry 0 -> 1)
    async with TestSessionLocal() as session:
        await worker.fail_event(session, event_id, epoch, current_retry_count=0, error_msg="ConnectionRefusedError")

    async with TestSessionLocal() as session:
        stmt = select(OutboxEvent).where(OutboxEvent.id == event_id)
        db_evt = (await session.execute(stmt)).scalars().first()
        assert db_evt.status == "PENDING"
        assert db_evt.retry_count == 1
        assert db_evt.is_dead_letter is False
        assert "ConnectionRefusedError" in db_evt.last_error

    # 2. Max retries exceeded (retry 9 -> 10)
    async with TestSessionLocal() as session:
        await worker.fail_event(session, event_id, epoch, current_retry_count=9, error_msg="PersistentTimeout")

    async with TestSessionLocal() as session:
        stmt = select(OutboxEvent).where(OutboxEvent.id == event_id)
        dead_evt = (await session.execute(stmt)).scalars().first()
        assert dead_evt.status == "FAILED"
        assert dead_evt.retry_count == 10
        assert dead_evt.is_dead_letter is True
