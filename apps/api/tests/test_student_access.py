from contextlib import AsyncExitStack
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.auth.models import AuthSession
from app.students.models import Student
from tests.test_auth import ACCOUNT, client_for, provision_parent


@pytest.mark.asyncio
async def test_two_families_two_students_and_cross_family_requests(auth_app):
    async with AsyncExitStack() as stack:
        clients = [await stack.enter_async_context(client_for(auth_app)) for _ in range(2)]
        groups = []
        families = []
        for n, client in enumerate(clients):
            account = {**ACCOUNT, "email": f"family{n}@example.com"}
            registration = await provision_parent(auth_app, {**account, "nickname": f"家长{n}"})
            families.append(registration["family"]["id"])
            assert (await client.post("/api/v1/auth/login", json=account)).status_code == 200
            client.headers["X-CSF-CSRF"] = client.cookies["csf_csrf"]
            children = []
            for child in range(2):
                created = await client.post(
                    "/api/v1/students", json={"nickname": f"孩子{n}-{child}", "grade": child + 1}
                )
                assert created.status_code == 201
                children.append(created.json())
            groups.append(children)
            listed = (await client.get("/api/v1/students")).json()
            assert {s["id"] for s in listed} == {s["id"] for s in children}
        assert families[0] != families[1]
        # 参数化覆盖两个方向、两个孩子、读取与修改/归档入口。
        for owner in range(2):
            intruder = clients[1 - owner]
            for child in groups[owner]:
                route = "/api/v1/students/" + child["id"]
                assert (await intruder.get(route)).status_code == 404
                assert (
                    await intruder.patch(
                        route, json={"nickname": "篡改"}, headers={"If-Match": "1"}
                    )
                ).status_code == 404
                assert (
                    await intruder.post(route + "/archive", headers={"If-Match": "1"})
                ).status_code == 404
                actual = (await clients[owner].get(route)).json()
                assert actual["nickname"] == child["nickname"]
                assert actual["revision"] == 1
        unknown = await clients[0].get("/api/v1/students/" + str(uuid4()))
        foreign = await clients[0].get("/api/v1/students/" + groups[1][0]["id"])
        assert unknown.status_code == foreign.status_code == 404
        assert unknown.json()["code"] == foreign.json()["code"] == "STUDENT_NOT_FOUND"
        forged = await clients[0].post(
            "/api/v1/students", json={"nickname": "伪造归属", "family_id": families[1]}
        )
        assert forged.status_code == 422
        # 数据库层也拒绝混用家庭与学生的会话上下文。
        async with auth_app.state.database.sessions() as db:
            student = await db.scalar(select(Student).where(Student.nickname == "孩子0-0"))
            wrong = await db.scalar(select(Student).where(Student.nickname == "孩子1-0"))
            row = await db.scalar(select(AuthSession))
            with pytest.raises(IntegrityError):
                await db.execute(
                    update(AuthSession)
                    .where(AuthSession.token == row.token)
                    .values(mode="child", family_id=wrong.family_id, student_id=student.id)
                )
                await db.commit()
            await db.rollback()


@pytest.mark.asyncio
async def test_student_revision_archive_and_validation(auth_app):
    async with client_for(auth_app) as client:
        await provision_parent(auth_app, {**ACCOUNT, "nickname": "家长"})
        await client.post("/api/v1/auth/login", json=ACCOUNT)
        client.headers["X-CSF-CSRF"] = client.cookies["csf_csrf"]
        created = await client.post("/api/v1/students", json={"nickname": "孩子", "grade": 3})
        child = created.json()
        route = "/api/v1/students/" + child["id"]
        assert (await client.patch(route, json={"grade": 4})).status_code == 428
        updated = await client.patch(route, json={"grade": 4}, headers={"If-Match": "1"})
        assert updated.status_code == 200
        assert updated.json()["id"] == child["id"]
        assert updated.json()["nickname"] == "孩子"
        assert updated.json()["grade"] == 4
        assert updated.json()["revision"] == 2
        stale = await client.patch(route, json={"grade": 5}, headers={"If-Match": "1"})
        assert stale.status_code == 409
        for invalid in [
            {"grade": None},
            {"grade": 13},
            {"nickname": "   "},
            {"birth_month": "2026-13"},
            {"school_year": "2026-2028"},
        ]:
            assert (
                await client.patch(route, json=invalid, headers={"If-Match": "2"})
            ).status_code == 422
        archived = await client.post(route + "/archive", headers={"If-Match": "2"})
        assert archived.status_code == 200
        assert archived.json()["archived_at"] is not None
        assert (await client.get("/api/v1/students")).json() == []
        assert len((await client.get("/api/v1/students?include_archived=true")).json()) == 1
        assert (await client.get(route)).json()["grade"] == 4
