import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.password import password_service


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
async def test_engine_level_single_owner_partial_unique_index(db_session: AsyncSession):
    """
    TEST-OWN-01: Engine-Level Single Owner Invariant.
    Concurrent raw SQL insert attempting to insert a second row with role='owner'
    for the same workspace is aborted by PostgreSQL with unique violation on uq_workspace_single_owner.
    """
    # 1. Create two users
    u1 = User(
        id=uuid.uuid4(),
        email=f"owner1_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=password_service.hash_password("Pass123!"),
        full_name="Owner One",
        is_active=True,
    )
    u2 = User(
        id=uuid.uuid4(),
        email=f"owner2_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=password_service.hash_password("Pass123!"),
        full_name="Owner Two",
        is_active=True,
    )
    db_session.add_all([u1, u2])
    await db_session.flush()

    # 2. Create workspace with u1 as owner
    ws = Workspace(
        id=uuid.uuid4(),
        name="Invariant Test WS",
        slug=f"invariant-test-{uuid.uuid4().hex[:4]}",
        owner_id=u1.id,
    )
    db_session.add(ws)
    await db_session.flush()

    m1 = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=u1.id,
        role="owner",
    )
    db_session.add(m1)
    await db_session.commit()

    # 3. Attempt direct SQL insert of second owner for same workspace
    m2 = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=u2.id,
        role="owner",
    )
    db_session.add(m2)

    with pytest.raises(IntegrityError) as exc_info:
        await db_session.commit()

    assert "uq_workspace_single_owner" in str(exc_info.value).lower()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_generic_role_updates_and_removal_restrictions(client: AsyncClient):
    """
    Tests that generic role updates and member removal enforce owner invariants:
    - Rejects assigning role='owner' via PATCH /members/{user_id}
    - Rejects modifying active owner's role
    - Rejects removing workspace owner
    """
    _, owner_headers, owner = await create_user_and_token(client, "Owner Alice")
    _, member_headers, member = await create_user_and_token(client, "Member Bob")

    # Create workspace
    slug = f"roles-test-{uuid.uuid4().hex[:4]}"
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Roles WS", "slug": slug},
        headers=owner_headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    # Invite Bob as member and accept
    inv_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": member["email"], "role": "member"},
        headers=owner_headers,
    )
    raw_token = inv_res.json()["data"]["raw_token"]
    accept_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token},
        headers=member_headers,
    )
    assert accept_res.status_code == 200

    # 1. Reject assigning role='owner' via generic PATCH
    bad_role_res = await client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{member['id']}",
        json={"role": "owner"},
        headers=owner_headers,
    )
    assert bad_role_res.status_code == 422 or bad_role_res.status_code == 400

    # 2. Reject modifying active owner's role via generic PATCH
    bad_owner_mod = await client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{owner['id']}",
        json={"role": "admin"},
        headers=owner_headers,
    )
    assert bad_owner_mod.status_code == 400
    assert "cannot_modify_owner_role" in bad_owner_mod.json()["detail"].lower()

    # 3. Reject removing workspace owner
    bad_remove_owner = await client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{owner['id']}",
        headers=owner_headers,
    )
    assert bad_remove_owner.status_code == 400
    assert "cannot_remove_workspace_owner" in bad_remove_owner.json()["detail"].lower()


@pytest.mark.asyncio
async def test_atomic_ownership_transfer_8_step(client: AsyncClient):
    """
    TEST-OWN-02: Atomic Ownership Transfer.
    Verifies the 8-step SQL transaction transfers ownership from Owner to Member,
    demotes original owner to 'admin', promotes target to 'owner', and maintains
    exactly one owner in the workspace.
    """
    _, owner_headers, owner = await create_user_and_token(client, "Transfer Owner")
    _, member_headers, member = await create_user_and_token(client, "Transfer Target")

    # Create workspace
    slug = f"transfer-ws-{uuid.uuid4().hex[:4]}"
    ws_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Transfer WS", "slug": slug},
        headers=owner_headers,
    )
    ws_id = ws_res.json()["data"]["id"]

    # 1. Self-transfer rejected
    self_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/transfer-ownership",
        json={"new_owner_id": owner["id"]},
        headers=owner_headers,
    )
    assert self_res.status_code == 400
    assert "cannot_transfer_to_self" in self_res.json()["detail"].lower()

    # 2. Transfer to non-member rejected
    non_member_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/transfer-ownership",
        json={"new_owner_id": member["id"]},
        headers=owner_headers,
    )
    assert non_member_res.status_code == 400
    assert "target_not_member" in non_member_res.json()["detail"].lower()

    # Add member to workspace
    inv_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": member["email"], "role": "member"},
        headers=owner_headers,
    )
    raw_token = inv_res.json()["data"]["raw_token"]
    await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token},
        headers=member_headers,
    )

    # 3. Successful 8-step transfer
    tx_res = await client.post(
        f"/api/v1/workspaces/{ws_id}/transfer-ownership",
        json={"new_owner_id": member["id"]},
        headers=owner_headers,
    )
    assert tx_res.status_code == 200
    tx_data = tx_res.json()["data"]
    assert tx_data["previous_owner_role"] == "admin"
    assert tx_data["new_owner_role"] == "owner"

    # Verify workspace details
    details_res = await client.get(f"/api/v1/workspaces/{ws_id}", headers=member_headers)
    assert details_res.status_code == 200
    assert details_res.json()["data"]["owner_id"] == member["id"]
    assert details_res.json()["data"]["role"] == "owner"

    # Verify former owner is now admin
    former_res = await client.get(f"/api/v1/workspaces/{ws_id}", headers=owner_headers)
    assert former_res.status_code == 200
    assert former_res.json()["data"]["role"] == "admin"

