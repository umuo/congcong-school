from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select, update

from app.auth import service
from app.auth.adapters import TokenDatabase
from app.auth.models import AuthSession, User
from app.families.models import Family, Membership

ORIGIN = "https://app.test"
ACCOUNT = {"email": "parent@example.com", "password": "Test-only-password-2026"}


def client_for(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=ORIGIN, headers={"Origin": ORIGIN}
    )


async def provision_parent(app, body):
    """档案/教材回归使用的已完成改密家长夹具；建号 API 另由管理员测试覆盖。"""
    async with app.state.database.sessions() as db:
        user = await service.create_account(
            db,
            login_name=body["email"].casefold(),
            email=body["email"],
            password=body["password"],
            nickname=body["nickname"],
            role="parent",
            must_change_password=False,
        )
        family = Family(name=body["nickname"][:77] + "的家庭")
        db.add(family)
        await db.flush()
        db.add(Membership(user_id=user.id, family_id=family.id, role="owner"))
        await db.commit()
        return {"user": service.user_view(user), "family": await service.family_view(db, user)}


@pytest.mark.asyncio
async def test_closed_registration_login_csrf_and_logout(auth_app):
    async with client_for(auth_app) as client:
        for body in [{**ACCOUNT, "nickname": "测试"}, {"role": "admin"}, {}]:
            closed = await client.post("/api/v1/auth/register", json=body)
            assert closed.status_code == 403
            assert closed.json()["code"] == "REGISTRATION_CLOSED"
        async with auth_app.state.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(User)) == 0
            assert await db.scalar(select(func.count()).select_from(Family)) == 0
        registered = await provision_parent(auth_app, {**ACCOUNT, "nickname": "测试家长"})
        forged = await client.post("/api/v1/auth/login", json={**ACCOUNT, "role": "admin"})
        assert forged.status_code == 422 and ACCOUNT["password"] not in forged.text
        assert (
            await client.post("/api/v1/auth/login", json={**ACCOUNT, "password": "wrong"})
        ).status_code == 401
        login = await client.post("/api/v1/auth/login", json=ACCOUNT)
        assert login.json()["destination"] == "/parent"
        cookies = login.headers.get_list("set-cookie")
        assert any("csf_session=" in c and "HttpOnly" in c and "Secure" in c for c in cookies)
        token = client.cookies["csf_session"]
        async with auth_app.state.database.sessions() as db:
            user = await db.scalar(select(User))
            assert user.hashed_password.startswith("$argon2id$") and not user.is_superuser
            row = await db.scalar(select(AuthSession))
            assert row.token == TokenDatabase.digest(token) and row.token != token
        assert (await client.get("/api/v1/family")).json()["id"] == registered["family"]["id"]
        assert (await client.patch("/api/v1/me", json={"nickname": "新名字"})).status_code == 403
        client.headers["X-CSF-CSRF"] = client.cookies["csf_csrf"]
        assert (await client.patch("/api/v1/me", json={"nickname": "新名字"})).status_code == 200
        wrong = await client.patch(
            "/api/v1/me", json={"nickname": "坏"}, headers={"Origin": "https://other.test"}
        )
        assert wrong.status_code == 403
        assert (await client.post("/api/v1/auth/logout")).status_code == 204
        assert (
            await client.get("/api/v1/me", headers={"Cookie": "csf_session=" + token})
        ).status_code == 401


@pytest.mark.asyncio
async def test_expiration_and_failed_login_rate_limit(auth_app):
    auth_app.state.settings.auth_rate_limit = 2
    await provision_parent(auth_app, {**ACCOUNT, "nickname": "家长"})
    async with client_for(auth_app) as client:
        assert (await client.post("/api/v1/auth/login", json=ACCOUNT)).status_code == 200
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(AuthSession).values(created_at=datetime.now(UTC) - timedelta(days=8))
            )
            await db.commit()
        assert (await client.get("/api/v1/me")).status_code == 401
        client.cookies.clear()
        assert (
            await client.post("/api/v1/auth/login", json={**ACCOUNT, "password": "wrong"})
        ).status_code == 401
        limited = await client.post("/api/v1/auth/login", json=ACCOUNT)
        assert limited.status_code == 429
        assert limited.json()["request_id"] == limited.headers["X-Request-ID"]
        async with auth_app.state.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(AuthSession)) == 1
