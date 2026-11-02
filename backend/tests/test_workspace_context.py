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
async def test_cross_workspace_isolation_and_context(client: AsyncClient):
    """
    Verifies WorkspaceContext enforcement:
    - User in Workspace A cannot access Workspace B (403 Forbidden)
    - Nonexistent workspace returns 404 Not Found
    - Regular member cannot perform admin updates (403 Forbidden)
    """
    _, user_a_headers, user_a = await create_user_and_token(client, "User A")
    _, user_b_headers, user_b = await create_user_and_token(client, "User B")

    # Workspace A created by User A
    ws_a_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Workspace A", "slug": f"ws-a-{uuid.uuid4().hex[:4]}"},
        headers=user_a_headers,
    )
    ws_a_id = ws_a_res.json()["data"]["id"]

    # Workspace B created by User B
    ws_b_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Workspace B", "slug": f"ws-b-{uuid.uuid4().hex[:4]}"},
        headers=user_b_headers,
    )
    ws_b_id = ws_b_res.json()["data"]["id"]

    # 1. User A attempts to view Workspace B details -> 403 Forbidden
    res1 = await client.get(f"/api/v1/workspaces/{ws_b_id}", headers=user_a_headers)
    assert res1.status_code == 403
    assert "access denied" in res1.json()["detail"].lower()

    # 2. User B attempts to view Workspace A members -> 403 Forbidden
    res2 = await client.get(f"/api/v1/workspaces/{ws_a_id}/members", headers=user_b_headers)
    assert res2.status_code == 403

    # 3. Nonexistent workspace UUID -> 404 Not Found
    fake_id = uuid.uuid4()
    res3 = await client.get(f"/api/v1/workspaces/{fake_id}", headers=user_a_headers)
    assert res3.status_code == 404

    # 4. Invite User B to Workspace A as regular 'member'
    inv_res = await client.post(
        f"/api/v1/workspaces/{ws_a_id}/invitations",
        json={"email": user_b["email"], "role": "member"},
        headers=user_a_headers,
    )
    raw_token = inv_res.json()["data"]["raw_token"]
    await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token},
        headers=user_b_headers,
    )

    # User B can now read Workspace A details
    member_read = await client.get(f"/api/v1/workspaces/{ws_a_id}", headers=user_b_headers)
    assert member_read.status_code == 200
    assert member_read.json()["data"]["role"] == "member"

    # User B (member) attempts admin update -> 403 Forbidden
    member_patch = await client.patch(
        f"/api/v1/workspaces/{ws_a_id}",
        json={"name": "Hacked Name"},
        headers=user_b_headers,
    )
    assert member_patch.status_code == 403
    assert "workspace admin or owner required" in member_patch.json()["detail"].lower()

