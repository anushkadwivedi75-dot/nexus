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
    assert reg_res.status_code == 201, reg_res.text
    token = reg_res.json()["data"]["access_token"]
    user_data = reg_res.json()["data"]["user"]
    return token, {"Authorization": f"Bearer {token}"}, user_data


@pytest.mark.asyncio
async def test_project_creation_and_default_statuses(client: AsyncClient):
    _, owner_headers, owner = await create_user_and_token(client, "Project Owner")

    # Create workspace
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Projects WS", "slug": f"pws-{uuid.uuid4().hex[:4]}"},
        headers=owner_headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    # 1. Create project
    proj_payload = {
        "name": "Nexus Platform",
        "key": "NEX",
        "description": "Next-gen collaborative workspace",
        "is_private": False,
    }
    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json=proj_payload,
        headers=owner_headers,
    )
    assert p_res.status_code == 201, p_res.text
    p_data = p_res.json()["data"]
    assert p_data["name"] == "Nexus Platform"
    assert p_data["key"] == "NEX"
    assert p_data["task_counter"] == 0
    p_id = p_data["id"]

    # 2. Check default status columns were initialized
    cols_res = await client.get(f"/api/v1/projects/{p_id}/columns", headers=owner_headers)
    assert cols_res.status_code == 200
    statuses = cols_res.json()["data"]
    assert len(statuses) == 4
    names = [s["name"] for s in statuses]
    assert names == ["Backlog", "Todo", "In Progress", "Done"]
    assert statuses[3]["is_completed_state"] is True


@pytest.mark.asyncio
async def test_project_key_validation_and_conflict(client: AsyncClient):
    _, owner_headers, _ = await create_user_and_token(client, "Key Owner")

    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Key WS", "slug": f"kws-{uuid.uuid4().hex[:4]}"},
        headers=owner_headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    # 1. Invalid key format (lowercase, too short, special characters)
    bad_keys = ["n", "nexus", "NEX_1", "TOOLONGPROJECTKEY", "N!X"]
    for k in bad_keys:
        res = await client.post(
            f"/api/v1/workspaces/{ws_id}/projects",
            json={"name": "Bad Key Project", "key": k},
            headers=owner_headers,
        )
        assert res.status_code in (400, 422), f"Expected validation failure for key '{k}'"

    # 2. Duplicate key conflict in same workspace
    res1 = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "First Project", "key": "ENG"},
        headers=owner_headers,
    )
    assert res1.status_code == 201

    res2 = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Duplicate Key Project", "key": "ENG"},
        headers=owner_headers,
    )
    assert res2.status_code == 409
    assert "already in use" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_private_project_membership_and_isolation(client: AsyncClient):
    _, owner_headers, owner = await create_user_and_token(client, "Priv Owner")
    _, member_headers, member = await create_user_and_token(client, "Priv Member")
    _, outsider_headers, _ = await create_user_and_token(client, "Outsider User")

    # Create workspace and invite member
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Priv WS", "slug": f"priv-ws-{uuid.uuid4().hex[:4]}"},
        headers=owner_headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    inv_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": member["email"], "role": "member"},
        headers=owner_headers,
    )
    await client.post(
        "/api/v1/invitations/accept",
        json={"token": inv_res.json()["data"]["raw_token"]},
        headers=member_headers,
    )

    # 1. Owner creates private project
    p_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Secret Roadmap", "key": "SEC", "is_private": True},
        headers=owner_headers,
    )
    p_id = p_res.json()["data"]["id"]

    # 2. Workspace member cannot access private project before being added
    unauth_res = await client.get(f"/api/v1/projects/{p_id}", headers=member_headers)
    assert unauth_res.status_code == 403
    assert "private project" in unauth_res.json()["detail"].lower()

    # 3. Add member to private project
    add_res = await client.post(
        f"/api/v1/projects/{p_id}/members",
        json={"user_id": member["id"]},
        headers=owner_headers,
    )
    assert add_res.status_code == 201

    # 4. Member can now access private project
    auth_res = await client.get(f"/api/v1/projects/{p_id}", headers=member_headers)
    assert auth_res.status_code == 200
    assert auth_res.json()["data"]["name"] == "Secret Roadmap"

    # 5. Outsider (not in workspace) cannot access or be added
    out_res = await client.get(f"/api/v1/projects/{p_id}", headers=outsider_headers)
    assert out_res.status_code == 403

