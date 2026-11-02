import asyncio
import uuid
import pytest
from httpx import AsyncClient


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
async def test_task_creation_and_atomic_numbering(client: AsyncClient):
    """
    TEST-TASK-01: Verifies task creation allocates monotonic 64-bit task numbers
    formatted as {PROJECT_KEY}-{NUMBER}.
    """
    _, headers, user = await create_user_and_token(client, "Task Creator")

    # Create workspace & project
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Task WS", "slug": f"tws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Core Engine", "key": "CORE"},
        headers=headers,
    )
    p_id = p_res.json()["data"]["id"]

    # Get status columns
    cols_res = await client.get(f"/api/v1/projects/{p_id}/columns", headers=headers)
    todo_status_id = cols_res.json()["data"][1]["id"]  # "Todo" column

    # 1. Create first task
    t1_res = await client.post(
        f"/api/v1/projects/{p_id}/tasks",
        json={
            "title": "Build authentication engine",
            "description": "## Specifications\nImplement Argon2id with 64MB memory cost.",
            "status_id": todo_status_id,
            "priority": "high",
            "assignee_ids": [user["id"]],
            "tag_names": ["security", "auth"],
        },
        headers=headers,
    )
    assert t1_res.status_code == 201, t1_res.text
    t1 = t1_res.json()["data"]
    assert t1["task_number"] == 1
    assert t1["task_key"] == "CORE-1"
    assert t1["version"] == 1
    assert len(t1["assignees"]) == 1
    assert len(t1["tags"]) == 2

    # 2. Create second task
    t2_res = await client.post(
        f"/api/v1/projects/{p_id}/tasks",
        json={
            "title": "Configure Redis grace stash",
            "status_id": todo_status_id,
            "priority": "urgent",
        },
        headers=headers,
    )
    assert t2_res.status_code == 201
    t2 = t2_res.json()["data"]
    assert t2["task_number"] == 2
    assert t2["task_key"] == "CORE-2"
    assert t2["rank"] > t1["rank"]  # Appended rank


@pytest.mark.asyncio
async def test_task_updates_and_soft_deletion(client: AsyncClient):
    _, headers, _ = await create_user_and_token(client, "Task Updater")

    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Crud WS", "slug": f"cws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "UI Redesign", "key": "UI"},
        headers=headers,
    )
    p_id = p_res.json()["data"]["id"]

    cols_res = await client.get(f"/api/v1/projects/{p_id}/columns", headers=headers)
    status_id = cols_res.json()["data"][0]["id"]

    # Create task
    t_res = await client.post(
        f"/api/v1/projects/{p_id}/tasks",
        json={"title": "Original Title", "status_id": status_id, "priority": "low"},
        headers=headers,
    )
    t_id = t_res.json()["data"]["id"]
    assert t_res.json()["data"]["version"] == 1

    # 1. Update task title and priority -> increments version
    patch_res = await client.patch(
        f"/api/v1/tasks/{t_id}",
        json={"title": "Updated Title", "priority": "high"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()["data"]
    assert updated["title"] == "Updated Title"
    assert updated["priority"] == "high"
    assert updated["version"] == 2

    # 2. Soft delete task
    del_res = await client.delete(f"/api/v1/tasks/{t_id}", headers=headers)
    assert del_res.status_code == 200

    # 3. Soft deleted task is excluded from task details and board
    get_res = await client.get(f"/api/v1/tasks/{t_id}", headers=headers)
    assert get_res.status_code == 404

    board_res = await client.get(f"/api/v1/projects/{p_id}/board", headers=headers)
    assert board_res.status_code == 200
    all_board_tasks = [t for col in board_res.json()["data"]["columns"] for t in col["tasks"]]
    assert not any(t["id"] == t_id for t in all_board_tasks)
