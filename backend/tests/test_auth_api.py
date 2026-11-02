import uuid
import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_auth_full_lifecycle(client: AsyncClient):
    unique_email = f"alex_{uuid.uuid4().hex[:6]}@nexus.local"
    password = "StrongPassword123!"

    # 1. Registration
    reg_payload = {
        "email": unique_email,
        "password": password,
        "full_name": "Alex Vance",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201, reg_res.text
    reg_json = reg_res.json()
    assert reg_json["success"] is True
    assert reg_json["data"]["user"]["email"] == unique_email
    access_token = reg_json["data"]["access_token"]
    assert access_token is not None

    # Check refresh cookie was set
    cookie_name = settings.refresh_cookie_name
    assert cookie_name in reg_res.cookies

    # 2. Duplicate registration rejected
    dup_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 409

    # 3. Access protected route with Bearer token
    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == unique_email

    # Unauthenticated request rejected
    unauth_res = await client.get("/api/v1/users/me")
    assert unauth_res.status_code == 401

    # 4. Login with valid credentials
    login_payload = {"email": unique_email, "password": password}
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    assert cookie_name in login_res.cookies

    # Login with invalid password rejected
    bad_login_res = await client.post("/api/v1/auth/login", json={"email": unique_email, "password": "WrongPassword!"})
    assert bad_login_res.status_code == 401

    # 5. Rotate refresh token
    refresh_cookie = login_res.cookies.get(cookie_name)
    client.cookies.set(cookie_name, refresh_cookie)
    csrf_headers = {"X-Requested-With": "XMLHttpRequest"}

    ref_res = await client.post("/api/v1/auth/refresh", headers=csrf_headers)
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()["data"]

    # 6. List active sessions
    sess_res = await client.get("/api/v1/users/me/sessions", headers=headers)
    assert sess_res.status_code == 200
    sessions = sess_res.json()["data"]
    assert len(sessions) >= 1

    # 7. Logout active session
    logout_res = await client.post("/api/v1/auth/logout", headers=csrf_headers)
    assert logout_res.status_code == 200

    # 8. Revoke all sessions
    revoke_res = await client.post("/api/v1/auth/revoke-all-sessions", headers=headers)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["data"]["count"] >= 1
