import pytest

from tests.test_auth import ACCOUNT, client_for, provision_parent
from tests.test_child_mode import csrf


@pytest.mark.asyncio
async def test_context_is_stable_rotates_and_rejects_old_pending_requests(auth_app):
    await provision_parent(auth_app, {**ACCOUNT, "nickname": "家长"})
    async with client_for(auth_app) as client:
        login = await client.post("/api/v1/auth/login", json=ACCOUNT)
        assert login.status_code == 200, login.text
        parent_scope = login.json()["context_id"]
        csrf(client)
        first = (await client.post("/api/v1/students", json={"nickname": "姐姐"})).json()
        second = (await client.post("/api/v1/students", json={"nickname": "弟弟"})).json()
        assert (await client.get("/api/v1/auth/session")).json()["context_id"] == parent_scope
        assert (
            await client.post("/api/v1/mode/child", json={"student_id": first["id"]})
        ).status_code == 200
        child = (await client.get("/api/v1/auth/session")).json()
        child_scope = child["context_id"]
        assert child_scope != parent_scope and child["user"] is None
        assert not {"token", "csrf_hash", "hashed_password"} & child.keys()
        assert (
            await client.get(
                f"/api/v1/students/{first['id']}/progress",
                headers={"X-CSF-Learning-Context": parent_scope},
            )
        ).status_code == 409
        assert (
            await client.get(
                f"/api/v1/students/{first['id']}/progress",
                headers={"X-CSF-Learning-Context": child_scope},
            )
        ).status_code == 200
        assert (await client.get("/api/v1/auth/session")).json()["context_id"] == child_scope
        login = await client.post("/api/v1/auth/login", json=ACCOUNT)
        assert login.status_code == 200, login.text
        assert login.json()["context_id"] not in {parent_scope, child_scope}
        csrf(client)
        assert (
            await client.post("/api/v1/mode/child", json={"student_id": second["id"]})
        ).status_code == 200
        scope = (await client.get("/api/v1/auth/session")).json()["context_id"]
        old = await client.get(
            f"/api/v1/students/{first['id']}/progress",
            headers={"X-CSF-Learning-Context": child_scope},
        )
        assert old.status_code == 409 and old.json()["code"] == "LEARNING_CONTEXT_CHANGED"
        assert (
            await client.get(
                f"/api/v1/students/{first['id']}/progress",
                headers={"X-CSF-Learning-Context": scope},
            )
        ).status_code == 404
        assert (
            await client.get(
                f"/api/v1/students/{second['id']}/progress",
                headers={"X-CSF-Learning-Context": scope},
            )
        ).status_code == 200
