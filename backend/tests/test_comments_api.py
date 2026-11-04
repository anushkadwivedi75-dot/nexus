import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.outbox_event import OutboxEvent
from app.models.comment import Comment


async def create_task(client: AsyncClient, headers: dict, proj_id: str, title: str = "Test Task") -> dict:
    cols_res = await client.get(f"/api/v1/projects/{proj_id}/columns", headers=headers)
    assert cols_res.status_code == 200, cols_res.text
    status_id = cols_res.json()["data"][0]["id"]
    res = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"title": title, "status_id": status_id},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


@pytest.mark.asyncio
async def test_comment_creation_and_reply_flow(client: AsyncClient, db_session):
    # 1. Setup workspace, project, task
    email = f"alice_{uuid.uuid4().hex[:6]}@nexus.local"
    reg = await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "Alice"})
    token = reg.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws_res = await client.post("/api/v1/workspaces", json={"name": "Engineering", "slug": f"eng-{uuid.uuid4().hex[:6]}"}, headers=headers)
    ws_id = ws_res.json()["data"]["id"]

    proj_res = await client.post(f"/api/v1/workspaces/{ws_id}/projects", json={"name": "API Service", "key": "API"}, headers=headers)
    proj_id = proj_res.json()["data"]["id"]

    task = await create_task(client, headers, proj_id, "Design comment threading")
    task_id = task["id"]

    # 2. Create top-level comment
    c1_res = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Here is the proposal for one-level discussion threads."},
        headers=headers,
    )
    assert c1_res.status_code == 201, c1_res.text
    c1 = c1_res.json()["data"]
    assert c1["content"] == "Here is the proposal for one-level discussion threads."
    assert c1["parent_comment_id"] is None
    assert c1["version"] == 1
    assert c1["author"]["full_name"] == "Alice"
    c1_id = c1["id"]

    # 3. Create reply to top-level comment
    r1_res = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Looks good! We should support mentions.", "parent_comment_id": c1_id},
        headers=headers,
    )
    assert r1_res.status_code == 201, r1_res.text
    r1 = r1_res.json()["data"]
    assert r1["parent_comment_id"] == c1_id
    assert r1["version"] == 1

    # 4. List comments and verify hierarchy
    list_res = await client.get(f"/api/v1/tasks/{task_id}/comments", headers=headers)
    assert list_res.status_code == 200
    page = list_res.json()["data"]
    assert len(page["items"]) == 1
    top_comment = page["items"][0]
    assert top_comment["id"] == c1_id
    assert top_comment["reply_count"] == 1
    assert len(top_comment["replies"]) == 1
    assert top_comment["replies"][0]["id"] == r1["id"]


@pytest.mark.asyncio
async def test_comment_validation_rules(client: AsyncClient):
    email = f"bob_{uuid.uuid4().hex[:6]}@nexus.local"
    reg = await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "Bob"})
    token = reg.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = (await client.post("/api/v1/workspaces", json={"name": "Dev", "slug": f"dev-{uuid.uuid4().hex[:6]}"}, headers=headers)).json()["data"]
    proj = (await client.post(f"/api/v1/workspaces/{ws['id']}/projects", json={"name": "Core", "key": "COR"}, headers=headers)).json()["data"]
    task = await create_task(client, headers, proj["id"], "Task 1")
    task2 = await create_task(client, headers, proj["id"], "Task 2")

    # 1. Empty content rejected
    empty_res = await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": ""}, headers=headers)
    assert empty_res.status_code == 422

    # 2. Whitespace-only content rejected
    ws_res = await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": "    \n\t  "}, headers=headers)
    assert ws_res.status_code == 422

    # 3. Content over 5000 chars rejected
    long_res = await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": "a" * 5001}, headers=headers)
    assert long_res.status_code == 422

    # 4. Non-existent parent rejected
    bad_parent = await client.post(
        f"/api/v1/tasks/{task['id']}/comments",
        json={"content": "reply", "parent_comment_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert bad_parent.status_code == 404

    # 5. Cross-task parent rejected
    c_t2 = (await client.post(f"/api/v1/tasks/{task2['id']}/comments", json={"content": "Comment on task 2"}, headers=headers)).json()["data"]
    cross_task = await client.post(
        f"/api/v1/tasks/{task['id']}/comments",
        json={"content": "Illegal cross-task reply", "parent_comment_id": c_t2["id"]},
        headers=headers,
    )
    assert cross_task.status_code == 400
    assert "belong to this task" in cross_task.json()["detail"]

    # 6. Nested reply beyond 1 level rejected
    c1 = (await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": "Top-level"}, headers=headers)).json()["data"]
    r1 = (await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": "Reply 1", "parent_comment_id": c1["id"]}, headers=headers)).json()["data"]
    nested_res = await client.post(
        f"/api/v1/tasks/{task['id']}/comments",
        json={"content": "Nested reply 2", "parent_comment_id": r1["id"]},
        headers=headers,
    )
    assert nested_res.status_code == 400
    assert "Nested replies beyond 1 level" in nested_res.json()["detail"]


@pytest.mark.asyncio
async def test_comment_updates_and_version_conflict(client: AsyncClient):
    # Setup users
    user1_email = f"charlie_{uuid.uuid4().hex[:6]}@nexus.local"
    user2_email = f"dana_{uuid.uuid4().hex[:6]}@nexus.local"
    reg1 = await client.post("/api/v1/auth/register", json={"email": user1_email, "password": "Password123!", "full_name": "Charlie"})
    reg2 = await client.post("/api/v1/auth/register", json={"email": user2_email, "password": "Password123!", "full_name": "Dana"})
    token1 = reg1.json()["data"]["access_token"]
    token2 = reg2.json()["data"]["access_token"]

    ws = (await client.post("/api/v1/workspaces", json={"name": "Team", "slug": f"team-{uuid.uuid4().hex[:6]}"}, headers={"Authorization": f"Bearer {token1}"})).json()["data"]
    # Invite Dana
    inv = await client.post(f"/api/v1/workspaces/{ws['id']}/invitations", json={"email": user2_email, "role": "member"}, headers={"Authorization": f"Bearer {token1}"})
    raw_token = inv.json()["data"]["raw_token"]
    await client.post("/api/v1/invitations/accept", json={"token": raw_token}, headers={"Authorization": f"Bearer {token2}"})

    proj = (await client.post(f"/api/v1/workspaces/{ws['id']}/projects", json={"name": "Product", "key": "PRD"}, headers={"Authorization": f"Bearer {token1}"})).json()["data"]
    task = await create_task(client, {"Authorization": f"Bearer {token1}"}, proj["id"], "Task update test")

    # Charlie posts comment
    comm = (await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": "Original content"}, headers={"Authorization": f"Bearer {token1}"})).json()["data"]
    assert comm["version"] == 1

    # Dana tries to edit Charlie's comment -> 403 Forbidden
    dana_edit = await client.patch(
        f"/api/v1/comments/{comm['id']}",
        json={"content": "Hacked content", "version": 1},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert dana_edit.status_code == 403

    # Charlie edits with stale version -> 409 Conflict
    stale_edit = await client.patch(
        f"/api/v1/comments/{comm['id']}",
        json={"content": "Conflict content", "version": 99},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert stale_edit.status_code == 409
    assert "COMMENT_VERSION_CONFLICT" in stale_edit.json()["detail"]

    # Charlie edits with correct version -> 200 OK
    good_edit = await client.patch(
        f"/api/v1/comments/{comm['id']}",
        json={"content": "Edited content", "version": 1},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert good_edit.status_code == 200
    updated = good_edit.json()["data"]
    assert updated["content"] == "Edited content"
    assert updated["version"] == 2


@pytest.mark.asyncio
async def test_comment_soft_deletion_and_thread_integrity(client: AsyncClient):
    owner_email = f"owner_{uuid.uuid4().hex[:6]}@nexus.local"
    member_email = f"member_{uuid.uuid4().hex[:6]}@nexus.local"
    reg_o = await client.post("/api/v1/auth/register", json={"email": owner_email, "password": "Password123!", "full_name": "Owner"})
    reg_m = await client.post("/api/v1/auth/register", json={"email": member_email, "password": "Password123!", "full_name": "Member"})
    t_owner = reg_o.json()["data"]["access_token"]
    t_member = reg_m.json()["data"]["access_token"]

    ws = (await client.post("/api/v1/workspaces", json={"name": "Ops", "slug": f"ops-{uuid.uuid4().hex[:6]}"}, headers={"Authorization": f"Bearer {t_owner}"})).json()["data"]
    inv = await client.post(f"/api/v1/workspaces/{ws['id']}/invitations", json={"email": member_email, "role": "member"}, headers={"Authorization": f"Bearer {t_owner}"})
    raw_token = inv.json()["data"]["raw_token"]
    await client.post("/api/v1/invitations/accept", json={"token": raw_token}, headers={"Authorization": f"Bearer {t_member}"})

    proj = (await client.post(f"/api/v1/workspaces/{ws['id']}/projects", json={"name": "Infra", "key": "INF"}, headers={"Authorization": f"Bearer {t_owner}"})).json()["data"]
    task = await create_task(client, {"Authorization": f"Bearer {t_owner}"}, proj["id"], "Delete test")

    # Member posts top-level comment
    comm = (await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": "Member comment"}, headers={"Authorization": f"Bearer {t_member}"})).json()["data"]
    # Owner posts reply
    rep = (await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": "Owner reply", "parent_comment_id": comm["id"]}, headers={"Authorization": f"Bearer {t_owner}"})).json()["data"]

    # Member soft-deletes their top-level comment
    del_res = await client.delete(f"/api/v1/comments/{comm['id']}", headers={"Authorization": f"Bearer {t_member}"})
    assert del_res.status_code == 200

    # Verify listing displays placeholder but preserves reply thread
    list_res = await client.get(f"/api/v1/tasks/{task['id']}/comments", headers={"Authorization": f"Bearer {t_owner}"})
    items = list_res.json()["data"]["items"]
    assert len(items) == 1
    parent = items[0]
    assert parent["is_deleted"] is True
    assert parent["content"] == "[This comment has been deleted.]"
    assert parent["author"] is None
    assert len(parent["replies"]) == 1
    assert parent["replies"][0]["id"] == rep["id"]
    assert parent["replies"][0]["content"] == "Owner reply"

    # Cannot reply to a deleted comment
    cannot_reply = await client.post(
        f"/api/v1/tasks/{task['id']}/comments",
        json={"content": "Replying to deleted comment", "parent_comment_id": comm["id"]},
        headers={"Authorization": f"Bearer {t_owner}"},
    )
    assert cannot_reply.status_code == 400
    assert "Cannot reply to a deleted comment" in cannot_reply.json()["detail"]


@pytest.mark.asyncio
async def test_member_mentions_and_isolation(client: AsyncClient):
    alice_email = f"alice_{uuid.uuid4().hex[:6]}@nexus.local"
    bob_email = f"bob_{uuid.uuid4().hex[:6]}@nexus.local"
    eve_email = f"eve_{uuid.uuid4().hex[:6]}@nexus.local"

    r_alice = await client.post("/api/v1/auth/register", json={"email": alice_email, "password": "Password123!", "full_name": "Alice Wonderland"})
    r_bob = await client.post("/api/v1/auth/register", json={"email": bob_email, "password": "Password123!", "full_name": "Bob Builder"})
    r_eve = await client.post("/api/v1/auth/register", json={"email": eve_email, "password": "Password123!", "full_name": "Eve External"})

    t_alice = r_alice.json()["data"]["access_token"]
    t_bob = r_bob.json()["data"]["access_token"]
    bob_id = r_bob.json()["data"]["user"]["id"]
    eve_id = r_eve.json()["data"]["user"]["id"]

    ws = (await client.post("/api/v1/workspaces", json={"name": "DevSec", "slug": f"devsec-{uuid.uuid4().hex[:6]}"}, headers={"Authorization": f"Bearer {t_alice}"})).json()["data"]
    # Only add Bob to workspace (Eve is an external user not in this workspace)
    inv = await client.post(f"/api/v1/workspaces/{ws['id']}/invitations", json={"email": bob_email, "role": "member"}, headers={"Authorization": f"Bearer {t_alice}"})
    raw_token = inv.json()["data"]["raw_token"]
    await client.post("/api/v1/invitations/accept", json={"token": raw_token}, headers={"Authorization": f"Bearer {t_bob}"})

    proj = (await client.post(f"/api/v1/workspaces/{ws['id']}/projects", json={"name": "Security", "key": "SEC"}, headers={"Authorization": f"Bearer {t_alice}"})).json()["data"]
    task = await create_task(client, {"Authorization": f"Bearer {t_alice}"}, proj["id"], "Audit mentions")

    # Alice mentions Bob via explicit mention @[Bob](<bob_id>) and attempts to mention external Eve @[Eve](<eve_id>) and @fakeuser
    content = f"Hey @[Bob]({bob_id}) check this out, also pinging @[Eve]({eve_id}) and @fakeuser"
    c_res = await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": content}, headers={"Authorization": f"Bearer {t_alice}"})
    assert c_res.status_code == 201
    comment = c_res.json()["data"]

    # Bob must be resolved as a mention, Eve and fakeuser must NOT be recorded
    mentions = comment["mentions"]
    assert len(mentions) == 1
    assert str(mentions[0]["user_id"]) == str(bob_id)


@pytest.mark.asyncio
async def test_cursor_pagination(client: AsyncClient):
    email = f"user_{uuid.uuid4().hex[:6]}@nexus.local"
    reg = await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "Paginator"})
    token = reg.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = (await client.post("/api/v1/workspaces", json={"name": "PagWS", "slug": f"pag-{uuid.uuid4().hex[:6]}"}, headers=headers)).json()["data"]
    proj = (await client.post(f"/api/v1/workspaces/{ws['id']}/projects", json={"name": "PagProj", "key": "PAG"}, headers=headers)).json()["data"]
    task = await create_task(client, headers, proj["id"], "Pagination test")

    # Create 5 top-level comments
    c_ids = []
    for i in range(5):
        res = await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": f"Comment {i + 1}"}, headers=headers)
        c_ids.append(res.json()["data"]["id"])

    # Fetch page 1 (limit=2)
    p1 = (await client.get(f"/api/v1/tasks/{task['id']}/comments?limit=2", headers=headers)).json()["data"]
    assert len(p1["items"]) == 2
    assert p1["items"][0]["id"] == c_ids[0]
    assert p1["items"][1]["id"] == c_ids[1]
    assert p1["has_more"] is True
    assert p1["next_cursor"] is not None

    # Fetch page 2 (limit=2) using cursor
    p2 = (await client.get(f"/api/v1/tasks/{task['id']}/comments?limit=2&cursor={p1['next_cursor']}", headers=headers)).json()["data"]
    assert len(p2["items"]) == 2
    assert p2["items"][0]["id"] == c_ids[2]
    assert p2["items"][1]["id"] == c_ids[3]
    assert p2["has_more"] is True

    # Fetch page 3 (remaining 1)
    p3 = (await client.get(f"/api/v1/tasks/{task['id']}/comments?limit=2&cursor={p2['next_cursor']}", headers=headers)).json()["data"]
    assert len(p3["items"]) == 1
    assert p3["items"][0]["id"] == c_ids[4]
    assert p3["has_more"] is False
    assert p3["next_cursor"] is None


@pytest.mark.asyncio
async def test_outbox_events_atomicity_for_comments(client: AsyncClient, db_session):
    email = f"outbox_{uuid.uuid4().hex[:6]}@nexus.local"
    reg = await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "OutboxTester"})
    token = reg.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = (await client.post("/api/v1/workspaces", json={"name": "OutboxWS", "slug": f"out-{uuid.uuid4().hex[:6]}"}, headers=headers)).json()["data"]
    proj = (await client.post(f"/api/v1/workspaces/{ws['id']}/projects", json={"name": "OutboxProj", "key": "OBX"}, headers=headers)).json()["data"]
    task = await create_task(client, headers, proj["id"], "Outbox task")

    # Create comment
    c = (await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content": "Atomicity test"}, headers=headers)).json()["data"]
    c_id = c["id"]

    # Verify outbox event exists in database
    stmt = select(OutboxEvent).where(
        OutboxEvent.workspace_id == uuid.UUID(ws["id"]),
        OutboxEvent.event_type == "comment.created",
    )
    res = await db_session.execute(stmt)
    event = res.scalars().first()
    assert event is not None
    assert event.payload["payload"]["comment_id"] == c_id
    assert event.payload["payload"]["task_id"] == task["id"]
    assert event.payload["payload"]["version"] == 1
