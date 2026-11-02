import uuid
import pytest
from httpx import AsyncClient


async def create_authenticated_user(client: AsyncClient, name: str = "Test User") -> tuple[str, dict]:
    """Helper to register a user and return the access token and headers."""
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
async def test_workspace_creation_happy_path(client: AsyncClient):
    _, headers, user = await create_authenticated_user(client, "Workspace Creator")
    slug = f"acme-corp-{uuid.uuid4().hex[:4]}"

    create_payload = {"name": "Acme Corporation", "slug": slug}
    res = await client.post("/api/v1/workspaces", json=create_payload, headers=headers)
    assert res.status_code == 201, res.text

    data = res.json()["data"]
    assert data["name"] == "Acme Corporation"
    assert data["slug"] == slug
    assert data["owner_id"] == user["id"]
    assert data["role"] == "owner"
    assert data["members_count"] == 1


@pytest.mark.asyncio
async def test_workspace_slug_validation_and_conflict(client: AsyncClient):
    _, headers, _ = await create_authenticated_user(client, "Slug Tester")

    # 1. Invalid slug formats (uppercase, spaces, special chars)
    bad_slugs = ["Acme Corp", "acme_corp", "-acme-", "acme--corp", "acme!"]
    for bad_slug in bad_slugs:
        res = await client.post(
            "/api/v1/workspaces",
            json={"name": "Bad Slug WS", "slug": bad_slug},
            headers=headers,
        )
        assert res.status_code == 422, f"Expected 422 for slug '{bad_slug}', got {res.status_code}"

    # 2. Duplicate slug returns 409 Conflict
    unique_slug = f"unique-team-{uuid.uuid4().hex[:4]}"
    res1 = await client.post(
        "/api/v1/workspaces",
        json={"name": "First Team", "slug": unique_slug},
        headers=headers,
    )
    assert res1.status_code == 201

    res2 = await client.post(
        "/api/v1/workspaces",
        json={"name": "Duplicate Team", "slug": unique_slug},
        headers=headers,
    )
    assert res2.status_code == 409
    assert "already taken" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_workspace_details_and_update(client: AsyncClient):
    _, headers, _ = await create_authenticated_user(client, "Update Tester")
    slug = f"meta-team-{uuid.uuid4().hex[:4]}"

    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Meta Team", "slug": slug},
        headers=headers,
    )
    ws_id = create_res.json()["data"]["id"]

    # 1. Fetch details
    get_res = await client.get(f"/api/v1/workspaces/{ws_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["role"] == "owner"

    # 2. Update name and logo_url
    patch_res = await client.patch(
        f"/api/v1/workspaces/{ws_id}",
        json={"name": "Updated Meta Team", "logo_url": "https://example.com/logo.png"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()["data"]
    assert updated_data["name"] == "Updated Meta Team"
    assert updated_data["logo_url"] == "https://example.com/logo.png"


@pytest.mark.asyncio
async def test_workspace_deletion_by_owner_and_unauthorized_rejection(client: AsyncClient):
    _, owner_headers, _ = await create_authenticated_user(client, "Owner User")
    _, other_headers, _ = await create_authenticated_user(client, "Other User")

    slug = f"delete-ws-{uuid.uuid4().hex[:4]}"
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "To Be Deleted", "slug": slug},
        headers=owner_headers,
    )
    ws_id = create_res.json()["data"]["id"]

    # Non-member cannot delete
    other_del_res = await client.delete(f"/api/v1/workspaces/{ws_id}", headers=other_headers)
    assert other_del_res.status_code == 403

    # Owner can delete
    owner_del_res = await client.delete(f"/api/v1/workspaces/{ws_id}", headers=owner_headers)
    assert owner_del_res.status_code == 200

    # Workspace should no longer exist
    get_res = await client.get(f"/api/v1/workspaces/{ws_id}", headers=owner_headers)
    assert get_res.status_code == 404

