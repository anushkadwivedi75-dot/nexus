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
async def test_invitation_lifecycle_and_acceptance(client: AsyncClient):
    _, owner_headers, owner = await create_user_and_token(client, "Invite Owner")
    _, invitee_headers, invitee = await create_user_and_token(client, "Invitee User")

    # Create workspace
    slug = f"invite-ws-{uuid.uuid4().hex[:4]}"
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Invite WS", "slug": slug},
        headers=owner_headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    # 1. Reject inviting as 'owner'
    bad_invite = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": invitee["email"], "role": "owner"},
        headers=owner_headers,
    )
    assert bad_invite.status_code in (400, 422)

    # 2. Successfully create invitation
    inv_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": invitee["email"], "role": "admin"},
        headers=owner_headers,
    )
    assert inv_res.status_code == 201
    inv_data = inv_res.json()["data"]
    assert inv_data["email"] == invitee["email"]
    assert inv_data["role"] == "admin"
    raw_token = inv_data["raw_token"]
    assert raw_token is not None

    # 3. Duplicate pending invite rejected
    dup_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": invitee["email"], "role": "member"},
        headers=owner_headers,
    )
    assert dup_res.status_code == 409

    # 4. List invitations
    list_res = await client.get(f"/api/v1/workspaces/{ws_id}/invitations", headers=owner_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 5. Accept invitation
    accept_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token},
        headers=invitee_headers,
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["data"]["membership"]["role"] == "admin"

    # 6. Verify invitee is now an admin of the workspace
    details_res = await client.get(f"/api/v1/workspaces/{ws_id}", headers=invitee_headers)
    assert details_res.status_code == 200
    assert details_res.json()["data"]["role"] == "admin"

    # 7. Already accepted invitation cannot be accepted again
    repeat_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token},
        headers=invitee_headers,
    )
    assert repeat_res.status_code == 400


@pytest.mark.asyncio
async def test_invitation_revocation(client: AsyncClient):
    _, owner_headers, _ = await create_user_and_token(client, "Revoke Owner")
    _, invitee_headers, invitee = await create_user_and_token(client, "Revokee User")

    # Create workspace
    slug = f"revoke-ws-{uuid.uuid4().hex[:4]}"
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Revoke WS", "slug": slug},
        headers=owner_headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    # Create invite
    inv_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": invitee["email"], "role": "member"},
        headers=owner_headers,
    )
    inv_id = inv_res.json()["data"]["id"]
    raw_token = inv_res.json()["data"]["raw_token"]

    # Revoke invite
    rev_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations/{inv_id}/revoke",
        headers=owner_headers,
    )
    assert rev_res.status_code == 200

    # Attempt to accept revoked invite
    accept_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token},
        headers=invitee_headers,
    )
    assert accept_res.status_code == 400
    assert "revoked" in accept_res.json()["detail"].lower()

