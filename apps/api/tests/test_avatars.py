import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.engine import make_url

from app.auth.bootstrap import bootstrap
from app.auth.models import AuthSession, StudentAccount, User
from app.auth.service import create_account
from app.avatars.catalog import AVATAR_IDS, CATALOG
from app.learning.models import LearningEvent, RewardLedger
from app.portability.privacy import erase_family, erase_student, export_family
from app.students.models import Student
from app.students.schemas import StudentCreate, StudentUpdate
from tests.test_auth import ACCOUNT, client_for, provision_parent
from tests.test_child_mode import csrf
from tests.test_foundation import migrate


def test_catalog_export_and_validation():
    root = Path(__file__).resolve().parents[3]
    assert json.loads((root / "apps/web/src/lib/avatars/catalog.json").read_text()) == CATALOG
    assert len(AVATAR_IDS) == len(CATALOG["presets"]) == 16
    assert {"panda", "fox", "rabbit", "bear"} <= AVATAR_IDS
    for item in CATALOG["presets"]:
        assert 0 < len(item["id"]) <= 32 and item["name"].strip()
        assert StudentCreate(nickname="孩子", avatar=item["id"]).avatar == item["id"]
        assert StudentUpdate(avatar=item["id"]).avatar == item["id"]
    for value in ["", None, "unknown", "x" * 33, "https://a.test/a.png", "data:image/png;base64,A"]:
        with pytest.raises(ValidationError):
            StudentCreate(nickname="孩子", avatar=value)
        with pytest.raises(ValidationError):
            StudentUpdate(avatar=value)


async def login(client, account=ACCOUNT):
    result = await client.post("/api/v1/auth/login", json=account)
    assert result.status_code == 200, result.text
    csrf(client)
    client.headers["X-CSF-Learning-Context"] = result.json()["context_id"]
    return result.json()


async def save(client, avatar="fox", revision=1, **kwargs):
    return await client.put(
        "/api/v1/me/avatar",
        json={"avatar_id": avatar},
        headers={"If-Match": str(revision), **kwargs},
    )


async def fixture(app):
    owner = await provision_parent(app, {**ACCOUNT, "nickname": "家长"})
    async with app.state.database.sessions() as db:
        kids = []
        for index in range(2):
            kid = Student(family_id=UUID(owner["family"]["id"]), nickname=f"孩子{index}")
            db.add(kid)
            await db.flush()
            user = await create_account(
                db,
                login_name=f"avatar-child-{index}",
                password=ACCOUNT["password"],
                nickname=kid.nickname,
                role="student",
            )
            assert user.avatar is None and user.avatar_revision is None
            db.add(StudentAccount(user_id=user.id, student_id=kid.id, family_id=kid.family_id))
            kids.append(kid.id)
        await db.commit()
    return owner, kids


@pytest.mark.asyncio
async def test_roles_scope_conflict_and_no_learning_side_effects(auth_app):
    owner, kids = await fixture(auth_app)
    async with (
        client_for(auth_app) as parent,
        client_for(auth_app) as child,
        client_for(auth_app) as other,
    ):
        await login(parent)
        await login(other)
        await login(child, {"login": "avatar-child-0", "password": ACCOUNT["password"]})
        catalog = await child.get("/api/v1/avatar-presets")
        assert catalog.json() == CATALOG
        assert (await parent.get("/api/v1/me/avatar")).json()["scope_kind"] == "user"
        for avatar in AVATAR_IDS:
            current = (await parent.get("/api/v1/me/avatar")).json()
            result = await save(parent, avatar, current["revision"])
            assert result.status_code == 200, result.text
        before = (await parent.get("/api/v1/me/avatar")).json()
        # Two devices, same version: one succeeds; neither can silently overwrite.
        responses = await asyncio.gather(
            save(parent, "robot", before["revision"]), save(other, "star", before["revision"])
        )
        assert sorted(r.status_code for r in responses) == [200, 409]
        own = (await child.get("/api/v1/me/avatar")).json()
        assert set(own) == {"scope_kind", "subject_id", "avatar_id", "revision", "catalog_version"}
        assert own["subject_id"] == str(kids[0]) and own["scope_kind"] == "student"
        switched = await parent.post("/api/v1/mode/child", json={"student_id": str(kids[0])})
        assert switched.status_code == 200
        assert (await save(parent, "lion")).json()["code"] == "LEARNING_CONTEXT_CHANGED"
        parent.headers["X-CSF-Learning-Context"] = (
            await parent.get("/api/v1/auth/session")
        ).json()["context_id"]
        csrf(parent)
        assert (await parent.get("/api/v1/me/avatar")).json() == own
        responses = await asyncio.gather(
            save(parent, "planet", own["revision"]), save(child, "cat", own["revision"])
        )
        assert sorted(r.status_code for r in responses) == [200, 409]
        current = (await child.get("/api/v1/me/avatar")).json()
        assert current["revision"] == own["revision"] + 1
        # Parent's old full form cannot undo the child's new avatar.
        stale = await other.patch(
            f"/api/v1/students/{kids[0]}",
            json={"avatar": "panda"},
            headers={"If-Match": str(own["revision"])},
        )
        assert stale.status_code == 409
        assert (await child.patch("/api/v1/me", json={"nickname": "坏"})).status_code == 403
        assert (
            await child.patch(f"/api/v1/students/{kids[1]}", json={"avatar": "fox"})
        ).status_code == 403
        assert (await other.get(f"/api/v1/students/{kids[1]}")).json()["avatar"] == "panda"
    async with auth_app.state.database.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(LearningEvent)) == 0
        assert await db.scalar(select(func.count()).select_from(RewardLedger)) == 0
        assert (
            await db.scalar(select(User).where(User.login_name == "avatar-child-0"))
        ).avatar is None


@pytest.mark.asyncio
async def test_invalid_context_payload_origin_revision_and_revocation(auth_app):
    _, kids = await fixture(auth_app)
    async with client_for(auth_app) as client:
        session = await login(client)
        assert (await save(client, **{"X-CSF-Learning-Context": str(uuid4())})).status_code == 409
        del client.headers["X-CSF-Learning-Context"]
        assert (await save(client)).status_code == 428
        client.headers["X-CSF-Learning-Context"] = session["context_id"]
        assert (await client.put("/api/v1/me/avatar", json={"avatar_id": "fox"})).status_code == 428
        assert (await save(client, revision="bad")).status_code == 422
        assert (await save(client, **{"Origin": "https://foreign.test"})).status_code == 403
        for payload in [
            {"avatar_id": None},
            {"avatar_id": "unknown"},
            {"avatar_id": "fox", "student_id": str(kids[1])},
            {"avatar_id": "robot", "nickname": "坏"},
            {"avatar_id": "https://a.test"},
        ]:
            assert (
                await client.put("/api/v1/me/avatar", json=payload, headers={"If-Match": "1"})
            ).status_code == 422
        assert (await client.get("/api/v1/me/avatar")).json()["revision"] == 1
        del client.headers["X-CSF-CSRF"]
        assert (await save(client)).status_code == 403
        csrf(client)
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(AuthSession).values(
                    parent_verified_at=datetime.now(UTC) - timedelta(minutes=6)
                )
            )
            await db.commit()
        assert (await save(client)).json()["code"] == "PARENT_REAUTH_REQUIRED"
        # Child mode is not gated by the parent's verification age.
        await login(client, {"login": "avatar-child-0", "password": ACCOUNT["password"]})
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(AuthSession).values(
                    parent_verified_at=datetime.now(UTC) - timedelta(minutes=6)
                )
            )
            await db.commit()
        assert (await save(client, "owl")).status_code == 200
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(Student).where(Student.id == kids[0]).values(archived_at=datetime.now(UTC))
            )
            await db.commit()
        assert (await save(client, revision=2)).json()["code"] == "STUDENT_ARCHIVED"
        assert (await client.get("/api/v1/me/avatar")).status_code == 409
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(User).where(User.login_name == "avatar-child-0").values(is_active=False)
            )
            await db.commit()
        assert (await save(client, revision=2)).status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_initial_password_export_and_delete(auth_app):
    settings = auth_app.state.settings.model_copy(
        update={
            "bootstrap_admin_login": "avatar-admin",
            "bootstrap_admin_password": __import__("pydantic").SecretStr(ACCOUNT["password"]),
        }
    )
    assert await bootstrap(settings, auth_app.state.database)
    async with client_for(auth_app) as admin:
        await login(admin, {"login": "avatar-admin", "password": ACCOUNT["password"]})
        assert (await admin.get("/api/v1/avatar-presets")).status_code == 403
        assert (await save(admin)).json()["code"] == "PASSWORD_CHANGE_REQUIRED"
        async with auth_app.state.database.sessions() as db:
            user = await db.scalar(select(User).where(User.role == "admin"))
            password = user.hashed_password
            user.must_change_password = False
            await db.commit()
        assert (await save(admin, "astronaut")).status_code == 200
        assert not await bootstrap(settings, auth_app.state.database)
        async with auth_app.state.database.sessions() as db:
            user = await db.scalar(select(User).where(User.role == "admin"))
            assert user.avatar == "astronaut" and user.hashed_password == password
    owner, kids = await fixture(auth_app)
    foreign = await provision_parent(
        auth_app, {**ACCOUNT, "email": "other-avatar@example.com", "nickname": "其他家庭"}
    )
    async with auth_app.state.database.sessions() as db:
        parent = await db.get(User, UUID(owner["user"]["id"]))
        parent.avatar = "lion"
        kid = await db.get(Student, kids[0])
        kid.avatar = "planet"
        await db.commit()
        exported = await export_family(db, UUID(owner["family"]["id"]))
        data = exported["data"]
        assert data["family_members"][0]["avatar"] == "lion"
        assert (
            next(b for b in data["student_accounts"] if b["student_id"] == str(kids[0]))["avatar"]
            == "planet"
        )
        serialized = json.dumps(exported)
        for secret in ["hashed_password", "csrf_hash", "avatar-admin", foreign["user"]["id"]]:
            assert secret not in serialized
        await erase_student(db, kids[0])
        await db.commit()
        assert await db.get(Student, kids[0]) is None
        assert await db.scalar(select(User).where(User.login_name == "avatar-child-0")) is None
        assert (await db.get(Student, kids[1])).avatar == "panda"
        assert parent.avatar == "lion"
        await erase_family(db, UUID(owner["family"]["id"]))
        await db.commit()
        assert await db.get(User, UUID(owner["user"]["id"])) is None
        assert await db.get(User, UUID(foreign["user"]["id"])) is not None


def test_old_user_and_student_migration_round_trip(postgres_url):
    migrate(postgres_url, "upgrade", "0010_portability")
    dsn = make_url(postgres_url).set(drivername="postgresql").render_as_string(hide_password=False)
    parent, admin, student_user, family = [uuid4() for _ in range(4)]
    kids = [uuid4() for _ in range(4)]
    with psycopg.connect(dsn) as db:
        for uid, role in [(parent, "parent"), (admin, "admin"), (student_user, "student")]:
            db.execute(
                "INSERT INTO users (id,login_name,hashed_password,is_active,"
                "is_superuser,is_verified,"
                "role,must_change_password,nickname) "
                "VALUES (%s,%s,%s,true,false,false,%s,false,%s)",
                (uid, str(uid), "preserved-hash", role, role),
            )
        db.execute(
            "INSERT INTO families (id,name,timezone) VALUES (%s,'家庭','Asia/Shanghai')", (family,)
        )
        for kid, avatar in zip(kids, ["panda", "fox", "rabbit", "bear"], strict=True):
            db.execute(
                "INSERT INTO students (id,family_id,nickname,avatar,school_stage,grade,semester,"
                "daily_goal_minutes,revision) VALUES (%s,%s,'孩子',%s,'primary',1,'up',20,1)",
                (kid, family, avatar),
            )
        db.execute(
            "INSERT INTO student_accounts (user_id,user_role,family_id,student_id) "
            "VALUES (%s,'student',%s,%s)",
            (student_user, family, kids[0]),
        )
        db.execute(
            "INSERT INTO learning_cursors (student_id,family_id,value) VALUES (%s,%s,1)",
            (kids[0], family),
        )
        db.execute(
            "INSERT INTO learning_events (student_id,cursor,kind,payload,client_at) "
            "VALUES (%s,1,'fixture','{}',now())",
            (kids[0],),
        )
        db.commit()
    for operation, revision in [
        ("upgrade", "head"),
        ("downgrade", "0010_portability"),
        ("upgrade", "head"),
    ]:
        migrate(postgres_url, operation, revision)
        with psycopg.connect(dsn) as db:
            assert db.execute("SELECT avatar FROM students ORDER BY avatar").fetchall() == [
                ("bear",),
                ("fox",),
                ("panda",),
                ("rabbit",),
            ]
            assert db.execute("SELECT count(*) FROM student_accounts").fetchone() == (1,)
            assert db.execute(
                "SELECT count(*) FROM users WHERE hashed_password = 'preserved-hash'"
            ).fetchone() == (3,)
            assert db.execute("SELECT kind FROM learning_events").fetchall() == [("fixture",)]
            if operation == "upgrade":
                assert db.execute(
                    "SELECT avatar,avatar_revision FROM users WHERE role='student'"
                ).fetchone() == (None, None)
                assert db.execute(
                    "SELECT avatar,avatar_revision FROM users WHERE role!='student'"
                ).fetchall() == [("panda", 1), ("panda", 1)]


@pytest.mark.asyncio
async def test_foreign_archived_reset_deleted_and_rotated_context(auth_app):
    owner, kids = await fixture(auth_app)
    foreign_account = {**ACCOUNT, "email": "avatar-foreign@example.com"}
    await provision_parent(auth_app, {**foreign_account, "nickname": "外部家长"})
    async with (
        client_for(auth_app) as parent,
        client_for(auth_app) as child,
        client_for(auth_app) as foreign,
    ):
        assert (await parent.get("/api/v1/avatar-presets")).status_code == 401
        await login(parent)
        await login(child, {"login": "avatar-child-0", "password": ACCOUNT["password"]})
        await login(foreign, foreign_account)
        assert (
            await foreign.patch(
                f"/api/v1/students/{kids[0]}", json={"avatar": "star"}, headers={"If-Match": "1"}
            )
        ).status_code == 404
        assert (
            await foreign.put(
                "/api/v1/me/avatar",
                json={"avatar_id": "star", "subject_id": str(kids[0])},
                headers={"If-Match": "1"},
            )
        ).status_code == 422
        # A reauthenticated cookie with an old context cannot relabel an avatar request.
        await parent.post("/api/v1/auth/reauth", json={"password": ACCOUNT["password"]})
        csrf(parent)
        assert (await save(parent, "star")).json()["code"] == "LEARNING_CONTEXT_CHANGED"
        parent.headers["X-CSF-Learning-Context"] = (
            await parent.get("/api/v1/auth/session")
        ).json()["context_id"]
        current = (await parent.get(f"/api/v1/students/{kids[0]}")).json()
        archived = await parent.post(
            f"/api/v1/students/{kids[0]}/archive", headers={"If-Match": str(current["revision"])}
        )
        assert archived.status_code == 200
        assert (
            await parent.patch(
                f"/api/v1/students/{kids[0]}",
                json={"avatar": "star"},
                headers={"If-Match": str(archived.json()["revision"])},
            )
        ).status_code == 409
        async with auth_app.state.database.sessions() as db:
            from app.auth.service import revoke_sessions

            user = await db.scalar(select(User).where(User.login_name == "avatar-child-0"))
            await revoke_sessions(db, user.id)
            await db.commit()
        assert (await save(child, "star")).status_code == 401
        async with auth_app.state.database.sessions() as db:
            await erase_student(db, kids[0])
            await db.commit()
        assert (await child.get("/api/v1/me/avatar")).status_code == 401
        assert (await parent.get("/api/v1/me/avatar")).json()["avatar_id"] == "panda"
        assert (await parent.get(f"/api/v1/students/{kids[1]}")).json()["avatar"] == "panda"
