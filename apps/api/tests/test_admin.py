import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.auth.bootstrap import bootstrap
from app.auth.models import AuthSession, StudentAccount, User
from app.families.models import Family, Membership
from app.students.models import Student
from tests.test_auth import ACCOUNT, client_for, provision_parent

INITIAL = "Initial-only-password-2026"
NEW = "Changed-only-password-2026"


def csrf(client):
    client.headers["X-CSF-CSRF"] = client.cookies["csf_csrf"]


async def login_change(client, login_name, old=INITIAL):
    result = await client.post("/api/v1/auth/login", json={"login": login_name, "password": old})
    assert result.status_code == 200, result.text
    csrf(client)
    if result.json()["must_change_password"]:
        changed = await client.post(
            "/api/v1/auth/change-password", json={"password": old, "new_password": NEW}
        )
        assert changed.status_code == 200, changed.text
        csrf(client)
        return changed.json()
    return result.json()


async def init_admin(app):
    settings = app.state.settings.model_copy(
        update={
            "bootstrap_admin_login": "admin",
            "bootstrap_admin_password": __import__("pydantic").SecretStr(INITIAL),
        }
    )
    results = await asyncio.gather(
        bootstrap(settings, app.state.database), bootstrap(settings, app.state.database)
    )
    assert sorted(results) == [False, True]
    return settings


@pytest.mark.asyncio
async def test_bootstrap_first_change_and_admin_account_transactions(auth_app, monkeypatch):
    with pytest.raises(ValueError, match="CSF_BOOTSTRAP"):
        await bootstrap(auth_app.state.settings, auth_app.state.database)
    legacy = await provision_parent(auth_app, {**ACCOUNT, "nickname": "重名测试"})
    from pydantic import SecretStr

    collision = auth_app.state.settings.model_copy(
        update={
            "bootstrap_admin_login": ACCOUNT["email"],
            "bootstrap_admin_password": SecretStr(INITIAL),
        }
    )
    with pytest.raises(ValueError, match="重名"):
        await bootstrap(collision, auth_app.state.database)
    async with auth_app.state.database.sessions() as db:
        from sqlalchemy import delete

        await db.execute(delete(Family).where(Family.id == UUID(legacy["family"]["id"])))
        await db.execute(delete(User).where(User.id == UUID(legacy["user"]["id"])))
        await db.commit()
    settings = await init_admin(auth_app)
    async with client_for(auth_app) as admin:
        initial = await admin.post(
            "/api/v1/auth/login", json={"login": "ADMIN", "password": INITIAL}
        )
        assert initial.json()["destination"] == "/change-password"
        old_token = admin.cookies["csf_session"]
        csrf(admin)
        assert (await admin.get("/api/v1/admin/parents")).json()[
            "code"
        ] == "PASSWORD_CHANGE_REQUIRED"
        assert (
            await admin.post("/api/v1/auth/reauth", json={"password": INITIAL})
        ).status_code == 403
        assert (await admin.get("/api/v1/auth/session")).json()["must_change_password"]
        await login_change(admin, "admin")
        assert (await admin.get("/api/v1/auth/session")).json()["destination"] == "/admin"
        assert admin.cookies["csf_session"] != old_token
        assert not await bootstrap(settings, auth_app.state.database)
        assert (await admin.get("/api/v1/family")).status_code == 403
        assert not (
            await admin.get("/api/v1/admin/login-availability", params={"login_name": "ADMIN"})
        ).json()["available"]
        assert (
            await admin.get("/api/v1/admin/login-availability", params={"login_name": "parent-one"})
        ).json()["available"]
        body = {
            "login_name": "parent-one",
            "password": INITIAL,
            "nickname": "家长",
            "family_name": "家庭甲",
        }
        # 并发重复创建只能有一个成功；失败创建的家庭必须回滚。
        results = await asyncio.gather(
            *[admin.post("/api/v1/admin/parents", json=body) for _ in range(2)]
        )
        assert sorted(r.status_code for r in results) == [201, 409]
        parent = next(r.json() for r in results if r.status_code == 201)
        check = await admin.get(
            "/api/v1/admin/login-availability", params={"login_name": " PARENT-ONE "}
        )
        assert check.json() == {"login_name": "parent-one", "available": False}
        assert (
            await admin.get("/api/v1/admin/login-availability", params={"login_name": "bad name"})
        ).status_code == 422
        assert "password" not in parent and "hashed_password" not in parent
        async with auth_app.state.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Family)) == 1
            assert await db.scalar(select(func.count()).select_from(Membership)) == 1
        guardian = await admin.post(
            "/api/v1/admin/parents",
            json={
                **body,
                "login_name": "guardian",
                "family_name": None,
                "family_id": parent["family_id"],
            },
        )
        assert guardian.status_code == 201
        assert (
            await admin.post("/api/v1/admin/parents", json={**body, "role": "admin"})
        ).status_code == 422
        foreign = await admin.post(
            "/api/v1/admin/students",
            json={
                "login_name": "orphan",
                "password": INITIAL,
                "nickname": "不存在",
                "family_id": parent["family_id"],
                "student_id": str(uuid4()),
            },
        )
        assert foreign.status_code == 404
        # 创建账号中途出错也不能留下家庭。
        from app.admin import router as admin_module

        async def broken(*args, **kwargs):
            raise RuntimeError("simulated failure")

        with monkeypatch.context() as patch:
            patch.setattr(admin_module, "new_user", broken)
            with pytest.raises(RuntimeError, match="simulated failure"):
                await admin.post("/api/v1/admin/parents", json={**body, "login_name": "broken"})
        async with auth_app.state.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Family)) == 1
            assert await db.scalar(select(func.count()).select_from(User)) == 3
        # 重新初始化绝不覆盖改过的管理员密码，也不复活账号。
        async with client_for(auth_app) as check:
            assert (
                await check.post("/api/v1/auth/login", json={"login": "admin", "password": INITIAL})
            ).status_code == 401
        self_id = (await admin.get("/api/v1/auth/session")).json()["user"]["id"]
        assert (await admin.post(f"/api/v1/admin/users/{self_id}/disable")).status_code == 404
        assert (await admin.post(f"/api/v1/admin/users/{parent['id']}/disable")).status_code == 204
        assert not (
            await admin.get("/api/v1/admin/login-availability", params={"login_name": "PARENT-ONE"})
        ).json()["available"]
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(AuthSession).values(
                    parent_verified_at=datetime.now(UTC) - timedelta(minutes=6)
                )
            )
            await db.commit()
        assert (await admin.get("/api/v1/admin/parents")).json()["code"] == "PARENT_REAUTH_REQUIRED"
        assert (await admin.post("/api/v1/auth/reauth", json={"password": NEW})).status_code == 200


@pytest.mark.asyncio
async def test_student_binding_role_boundaries_reset_disable_and_archive(auth_app):
    await init_admin(auth_app)
    auth_app.state.settings.auth_rate_limit = 100
    async with (
        client_for(auth_app) as admin,
        client_for(auth_app) as parent,
        client_for(auth_app) as child,
    ):
        await login_change(admin, "admin")
        families = []
        groups = []
        for n in range(2):
            created = await admin.post(
                "/api/v1/admin/parents",
                json={
                    "login_name": f"parent{n}",
                    "password": INITIAL,
                    "nickname": f"家长{n}",
                    "family_name": f"家庭{n}",
                },
            )
            assert created.status_code == 201
            assert not created.json()["must_change_password"]
            families.append(created.json())
            await login_change(parent, f"parent{n}")
            group = []
            for k in range(2):
                profile = (
                    await parent.post(
                        "/api/v1/students",
                        json={"nickname": f"孩子{n}{k}", "parent_notes": "不能给孩子看"},
                    )
                ).json()
                account = await admin.post(
                    "/api/v1/admin/students",
                    json={
                        "login_name": f"child{n}{k}",
                        "password": INITIAL,
                        "nickname": profile["nickname"],
                        "family_id": created.json()["family_id"],
                        "student_id": profile["id"],
                    },
                )
                assert account.status_code == 201, account.text
                assert not account.json()["must_change_password"]
                group.append(account.json())
            groups.append(group)
        first = groups[0][0]
        duplicate = await admin.post(
            "/api/v1/admin/students",
            json={
                "login_name": "duplicate",
                "password": INITIAL,
                "nickname": "重复",
                "family_id": first["family_id"],
                "student_id": first["student_id"],
            },
        )
        assert duplicate.status_code == 409
        mixed = await admin.post(
            "/api/v1/admin/students",
            json={
                "login_name": "foreign",
                "password": INITIAL,
                "nickname": "混合",
                "family_id": groups[1][0]["family_id"],
                "student_id": first["student_id"],
            },
        )
        assert mixed.status_code == 404
        async with auth_app.state.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(User)) == 7
            assert await db.scalar(select(func.count()).select_from(Student)) == 4
            row = await db.get(StudentAccount, UUID(first["id"]))
            original_student = row.student_id
            with pytest.raises(IntegrityError):
                await db.execute(
                    update(StudentAccount)
                    .where(StudentAccount.user_id == row.user_id)
                    .values(family_id=UUID(groups[1][0]["family_id"]))
                )
            await db.rollback()
        # 四个学生各自只看到自己，且学生账号确实没有邮箱/家长成员身份。
        for n in range(2):
            for k in range(2):
                state = await login_change(child, f"child{n}{k}")
                assert state["role"] == "student" and state["destination"] == "/learn"
                assert not state["must_change_password"]
                profile = (await child.get("/api/v1/learning/profile")).json()
                assert profile["id"] == groups[n][k]["student_id"]
                assert set(profile) == {"id", "nickname", "grade", "avatar"}
                for path in ["/me", "/family", "/students", "/admin/parents"]:
                    assert (await child.get("/api/v1" + path)).status_code == 403
                assert (
                    await child.post("/api/v1/mode/parent", json={"password": INITIAL})
                ).status_code == 403
                assert (
                    await child.post(
                        "/api/v1/mode/child", json={"student_id": groups[n][1 - k]["student_id"]}
                    )
                ).status_code == 403
                async with auth_app.state.database.sessions() as db:
                    user = await db.get(User, UUID(groups[n][k]["id"]))
                    assert user.email is None
                    assert (
                        await db.scalar(select(Membership.id).where(Membership.user_id == user.id))
                        is None
                    )
        # 家长同样不能管理账号，管理员不能直接读取家庭档案。
        assert (await parent.get("/api/v1/admin/students")).status_code == 403
        assert (
            await parent.get("/api/v1/admin/login-availability", params={"login_name": "parent0"})
        ).status_code == 403
        async with client_for(auth_app) as anonymous:
            assert (
                await anonymous.get(
                    "/api/v1/admin/login-availability", params={"login_name": "parent0"}
                )
            ).status_code == 401
        assert (await admin.get("/api/v1/students/" + first["student_id"])).status_code == 403
        await login_change(child, "child00", old=INITIAL)
        old_token = child.cookies["csf_session"]
        assert (
            await admin.post(
                f"/api/v1/admin/users/{first['id']}/reset-password", json={"password": INITIAL}
            )
        ).status_code == 204
        assert (await child.get("/api/v1/learning/profile")).status_code == 401
        reset_state = await login_change(child, "child00")
        assert not reset_state["must_change_password"] and reset_state["destination"] == "/learn"
        assert child.cookies["csf_session"] != old_token
        # 家长代入会话随家长停用失效，独立学生仍可用。
        await login_change(parent, "parent0", old=INITIAL)
        assert (
            await parent.post("/api/v1/mode/child", json={"student_id": first["student_id"]})
        ).status_code == 200
        assert (
            await admin.post(f"/api/v1/admin/users/{families[0]['id']}/disable")
        ).status_code == 204
        assert (await parent.get("/api/v1/learning/profile")).status_code == 401
        assert (await child.get("/api/v1/learning/profile")).status_code == 200
        # 归档不删账号/历史，但独立账号无法再登录或继续学习。
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(Student)
                .where(Student.id == original_student)
                .values(archived_at=datetime.now(UTC))
            )
            await db.commit()
        assert (await child.get("/api/v1/learning/profile")).status_code == 409
        assert (
            await child.post("/api/v1/auth/login", json={"login": "child00", "password": INITIAL})
        ).status_code == 401
        # 学生账号单独停用不影响兄弟姐妹。
        other = groups[1][0]
        assert (await admin.post(f"/api/v1/admin/users/{other['id']}/disable")).status_code == 204
        assert (
            await child.post("/api/v1/auth/login", json={"login": "child10", "password": INITIAL})
        ).status_code == 401
        assert (
            await child.post("/api/v1/auth/login", json={"login": "child11", "password": INITIAL})
        ).status_code == 200


@pytest.mark.asyncio
async def test_student_deletion_revokes_only_bound_learning_identity(auth_app):
    from sqlalchemy import delete

    from app.auth.service import create_account

    parent = await provision_parent(auth_app, {**ACCOUNT, "nickname": "家长"})
    async with auth_app.state.database.sessions() as db:
        students = [
            Student(family_id=UUID(parent["family"]["id"]), nickname=n) for n in ["姐姐", "弟弟"]
        ]
        db.add_all(students)
        await db.flush()
        for index, student in enumerate(students):
            user = await create_account(
                db,
                login_name=f"delete-child-{index}",
                password=INITIAL,
                nickname=student.nickname,
                role="student",
                must_change_password=False,
            )
            db.add(
                StudentAccount(user_id=user.id, family_id=student.family_id, student_id=student.id)
            )
        await db.commit()
        removed_id = students[0].id
    async with client_for(auth_app) as first, client_for(auth_app) as second:
        for index, client in enumerate([first, second]):
            assert (
                await client.post(
                    "/api/v1/auth/login",
                    json={"login": f"delete-child-{index}", "password": INITIAL},
                )
            ).status_code == 200
        async with auth_app.state.database.sessions() as db:
            await db.execute(delete(Student).where(Student.id == removed_id))
            await db.commit()
        assert (await first.get("/api/v1/learning/profile")).status_code == 401
        assert (
            await first.post(
                "/api/v1/auth/login", json={"login": "delete-child-0", "password": INITIAL}
            )
        ).status_code == 401
        assert (await second.get("/api/v1/learning/profile")).json()["nickname"] == "弟弟"
