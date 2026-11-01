from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.auth.adapters import TokenDatabase
from app.auth.models import AuthSession
from tests.test_auth import ACCOUNT, client_for, provision_parent


def csrf(client):
    client.headers["X-CSF-CSRF"] = client.cookies["csf_csrf"]


@pytest.mark.asyncio
async def test_shared_session_downgrade_separate_device_and_parent_reverification(auth_app):
    async with client_for(auth_app) as device_a, client_for(auth_app) as device_b:
        await provision_parent(auth_app, {**ACCOUNT, "nickname": "家长"})
        assert (await device_a.post("/api/v1/auth/login", json=ACCOUNT)).status_code == 200
        csrf(device_a)
        first = (
            await device_a.post(
                "/api/v1/students", json={"nickname": "姐姐", "parent_notes": "仅家长可见"}
            )
        ).json()
        second = (
            await device_a.post("/api/v1/students", json={"nickname": "弟弟", "grade": 2})
        ).json()
        assert (await device_b.post("/api/v1/auth/login", json=ACCOUNT)).status_code == 200
        csrf(device_b)
        shared_token = device_a.cookies["csf_session"]
        switched = await device_a.post("/api/v1/mode/child", json={"student_id": first["id"]})
        assert switched.status_code == 200
        profile = await device_a.get("/api/v1/learning/profile")
        assert set(profile.json()) == {"id", "nickname", "avatar", "grade"}
        assert profile.json()["id"] == first["id"]
        for path in ["/me", "/family", "/students", "/students/" + second["id"]]:
            assert (await device_a.get("/api/v1" + path)).status_code == 403
        forged_write = await device_a.patch(
            "/api/v1/students/" + first["id"],
            json={"nickname": "篡改"},
            headers={"If-Match": "1"},
        )
        assert forged_write.status_code == 403
        assert (
            await device_a.post("/api/v1/mode/child", json={"student_id": second["id"]})
        ).status_code == 403
        # 同一 Cookie 的另一个标签页也被服务端降权；混合 Bearer 不能提升权限。
        async with client_for(auth_app) as shared_tab:
            denied = await shared_tab.get(
                "/api/v1/me",
                headers={
                    "Cookie": "csf_session=" + shared_token,
                    "Authorization": "Bearer " + device_b.cookies["csf_session"],
                },
            )
            assert denied.status_code == 403
        assert (await device_b.get("/api/v1/me")).status_code == 200
        # 另一设备归档孩子后，原孩子会话不能继续学习。
        archived = await device_b.post(
            "/api/v1/students/" + first["id"] + "/archive", headers={"If-Match": "1"}
        )
        assert archived.status_code == 200
        assert (await device_a.get("/api/v1/learning/profile")).status_code == 409
        wrong = await device_a.post("/api/v1/mode/parent", json={"password": "wrong"})
        assert wrong.status_code == 401
        assert (await device_a.get("/api/v1/me")).status_code == 403
        restored = await device_a.post(
            "/api/v1/mode/parent", json={"password": ACCOUNT["password"]}
        )
        assert restored.status_code == 200
        assert device_a.cookies["csf_session"] != shared_token
        csrf(device_a)
        assert (await device_a.get("/api/v1/me")).status_code == 200
        async with client_for(auth_app) as replay:
            assert (
                await replay.get("/api/v1/me", headers={"Cookie": "csf_session=" + shared_token})
            ).status_code == 401
        current = device_a.cookies["csf_session"]
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(AuthSession)
                .where(AuthSession.token == TokenDatabase.digest(current))
                .values(parent_verified_at=datetime.now(UTC) - timedelta(minutes=6))
            )
            await db.commit()
        assert (
            await device_a.post("/api/v1/mode/child", json={"student_id": second["id"]})
        ).status_code == 403
        assert (
            await device_a.post("/api/v1/auth/reauth", json={"password": ACCOUNT["password"]})
        ).status_code == 200
        csrf(device_a)
        assert (
            await device_a.post("/api/v1/mode/child", json={"student_id": second["id"]})
        ).status_code == 200
        assert (await device_a.get("/api/v1/learning/profile")).json()["id"] == second["id"]
        assert (await device_b.get("/api/v1/me")).status_code == 200
