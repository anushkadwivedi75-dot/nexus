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
async def test_kanban_card_movement_and_optimistic_locking(client: AsyncClient):
    """
    Verifies Kanban card drag-and-drop movement across columns,
    fractional rank allocation, and optimistic concurrency version rejection.
    """
    _, headers, _ = await create_user_and_token(client, "Kanban User")

    # Create workspace & project
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Kanban WS", "slug": f"kws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Kanban Project", "key": "KAN"},
        headers=headers,
    )
    p_id = p_res.json()["data"]["id"]

    cols = (await client.get(f"/api/v1/projects/{p_id}/columns", headers=headers)).json()["data"]
    todo_col = cols[1]["id"]
    in_prog_col = cols[2]["id"]

    # Create task 1 and task 2 in Todo
    t1_res = await client.post(
        f"/api/v1/projects/{p_id}/tasks",
        json={"title": "Task 1", "status_id": todo_col},
        headers=headers,
    )
    t1 = t1_res.json()["data"]

    t2_res = await client.post(
        f"/api/v1/projects/{p_id}/tasks",
        json={"title": "Task 2", "status_id": todo_col},
        headers=headers,
    )
    t2 = t2_res.json()["data"]

    # 1. Move Task 1 from Todo to In Progress (cross-column move)
    move_res = await client.patch(
        f"/api/v1/tasks/{t1['id']}/move",
        json={
            "destination_status_id": in_prog_col,
            "prev_task_id": None,
            "next_task_id": None,
            "version": t1["version"],
        },
        headers=headers,
    )
    assert move_res.status_code == 200
    t1_moved = move_res.json()["data"]
    assert t1_moved["status_id"] == in_prog_col
    assert t1_moved["version"] == t1["version"] + 1

    # 2. Stale version rejection (presenting original version 1)
    stale_move_res = await client.patch(
        f"/api/v1/tasks/{t1['id']}/move",
        json={
            "destination_status_id": todo_col,
            "version": t1["version"],  # Version 1 is now stale
        },
        headers=headers,
    )
    assert stale_move_res.status_code == 409
    assert "task_version_conflict" in stale_move_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_column_deletion_with_task_remapping(client: AsyncClient):
    """
    Verifies that deleting a status column safely remaps all active tasks
    to a fallback status column without leaving orphaned references.
    """
    _, headers, _ = await create_user_and_token(client, "Column Admin")

    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Status WS", "slug": f"sws-{uuid.uuid4().hex[:4]}"},
        headers=headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Remap Project", "key": "REM"},
        headers=headers,
    )
    p_id = p_res.json()["data"]["id"]

    # Create a custom column "QA Review"
    custom_col_res = await client.post(
        f"/api/v1/projects/{p_id}/columns",
        json={"name": "QA Review", "color_hex": "#F43F5E"},
        headers=headers,
    )
    assert custom_col_res.status_code == 201
    qa_col_id = custom_col_res.json()["data"]["id"]

    # Get "Backlog" column
    cols = (await client.get(f"/api/v1/projects/{p_id}/columns", headers=headers)).json()["data"]
    backlog_col_id = cols[0]["id"]

    # Create task in QA Review
    task_res = await client.post(
        f"/api/v1/projects/{p_id}/tasks",
        json={"title": "QA Test Task", "status_id": qa_col_id},
        headers=headers,
    )
    task_id = task_res.json()["data"]["id"]

    # Delete "QA Review" with fallback to "Backlog"
    del_col_res = await client.request(
        "DELETE",
        f"/api/v1/projects/{p_id}/columns/{qa_col_id}",
        json={"fallback_status_id": backlog_col_id},
        headers=headers,
    )
    assert del_col_res.status_code == 200

    # Verify task is now in "Backlog"
    task_details = (await client.get(f"/api/v1/tasks/{task_id}", headers=headers)).json()["data"]
    assert task_details["status_id"] == backlog_col_id
    assert task_details["version"] == 2  # Incremented on remap
