import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.auth.models import StudentAccount, User
from app.auth.service import create_account
from app.families.models import Membership
from app.learning.models import Attempt, RewardLedger
from app.portability.models import LegacyImport
from app.portability.privacy import purge_expired_journal, replay_deletions
from app.students.models import Student
from tests import test_content as content_fixtures
from tests.test_auth import ACCOUNT, client_for, provision_parent
from tests.test_child_mode import csrf
from tests.test_learning import login_child, now, post, prepare


@pytest.fixture
def source_tree(tmp_path):
    return content_fixtures.source_tree.__wrapped__(tmp_path)


def backup():
    return {
        "schema": "cstf-backup",
        "version": 1,
        "platform": "web",
        "data": {
            "completedLessons": {
                "g1up-u1-kp1": {"stars": 3, "accuracy": 1, "completedAt": "2026-10-01"},
                "unknown-book-u1": {"stars": 2, "accuracy": 0.8},
            },
            "mistakesBank": [
                {
                    "lessonId": "g1up-u1-kp1",
                    "questionId": 1,
                    "question": {"answer": "forged-private-answer"},
                }
            ],
            "ownedCosmetics": {"old-costume": True},
            "equipped": {"mascotSkin": "old-costume"},
            "avatar": "fox",
            "xp": 999999,
            "gems": 999999,
        },
    }


async def parent_login(client):
    assert (await client.post("/api/v1/auth/login", json=ACCOUNT)).status_code == 200
    csrf(client)


@pytest.mark.asyncio
async def test_preview_confirm_replay_unknown_sources_no_rewards_or_fake_attempts(
    auth_app, source_tree
):
    students = await prepare(auth_app, source_tree)
    path = f"/api/v1/students/{students[0]}"
    async with client_for(auth_app) as parent, client_for(auth_app) as child:
        await parent_login(parent)
        await login_child(child)
        assert (await child.post(path + "/imports/preview", json=backup())).status_code == 403
        for invalid in [
            {},
            {**backup(), "version": 2},
            {**backup(), "data": []},
            {**backup(), "data": {"mistakesBank": [{"lessonId": {}, "questionId": 1}]}},
        ]:
            assert (await parent.post(path + "/imports/preview", json=invalid)).status_code == 422
        assert (
            await parent.post(path + "/imports/preview", content=b"x" * (5 * 1024 * 1024 + 1))
        ).status_code == 413
        preview = await parent.post(path + "/imports/preview", json=backup())
        assert preview.status_code == 200, preview.text
        value = preview.json()
        assert value["report"]["mapped_lessons"] == 1
        assert value["report"]["unmapped"][0]["source_id"] == "unknown-book-u1"
        assert (await parent.get(path + "/legacy")).json() == []
        body = {k: value[k] for k in ("preview_id", "source_hash", "revision")}
        first = await parent.post(path + "/imports/confirm", json=body)
        assert first.status_code == 200, first.text
        assert first.json()["confirmed"] is True
        assert (await parent.get(path)).json()["avatar"] == "panda"
        assert (await parent.post(path + "/imports/confirm", json=body)).json() == first.json()
        assert (await parent.post(path + "/imports/preview", json=backup())).json()[
            "confirmed"
        ] is True
        legacy = (await child.get(path + "/legacy")).json()
        assert legacy[0]["summary"]["completedLessons"]["g1up-u1-kp1"]["stars"] == 3
        assert legacy[0]["summary"]["legacyCosmetics"] == {"old-costume": True}
        assert "forged-private-answer" not in json.dumps(legacy)
        assert (await child.get(f"/api/v1/students/{students[1]}/legacy")).status_code == 404
        progress = (await child.get(path + "/progress")).json()
        assert progress["state"]["xp"] == progress["state"]["gems"] == 0
        assert progress["state"]["completedLessons"] == {}
        async with auth_app.state.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Attempt)) == 0
            assert await db.scalar(select(func.count()).select_from(RewardLedger)) == 0
            assert await db.scalar(select(func.count()).select_from(LegacyImport)) == 1


@pytest.mark.asyncio
async def test_preview_revision_conflict_and_family_export_scopes(auth_app, source_tree):
    students = await prepare(auth_app, source_tree)
    async with (
        client_for(auth_app) as parent,
        client_for(auth_app) as child,
        client_for(auth_app) as other,
    ):
        await parent_login(parent)
        await login_child(child)
        await provision_parent(
            auth_app, {**ACCOUNT, "email": "other@example.com", "nickname": "另一个家庭"}
        )
        assert (
            await other.post("/api/v1/auth/login", json={**ACCOUNT, "email": "other@example.com"})
        ).status_code == 200
        csrf(other)
        path = f"/api/v1/students/{students[0]}"
        value = (await parent.post(path + "/imports/preview", json=backup())).json()
        edited = await parent.patch(
            path, headers={"If-Match": str(value["revision"])}, json={"grade": 4}
        )
        assert edited.status_code == 200
        assert (
            await parent.post(
                path + "/imports/confirm",
                json={k: value[k] for k in ("preview_id", "source_hash", "revision")},
            )
        ).status_code == 409
        assert (await other.get(path + "/legacy")).status_code == 404
        assert (await child.get("/api/v1/family/export")).status_code == 403
        exported = await parent.get("/api/v1/family/export")
        assert exported.status_code == 200, exported.text
        data = exported.json()
        assert {s["id"] for s in data["data"]["students"]} == {str(s) for s in students}
        assert len(data["data"]["student_accounts"]) == 2
        serialized = json.dumps(data)
        for secret in (
            "hashed_password",
            "csrf_hash",
            "must_change_password",
            "token",
            "other@example.com",
        ):
            assert secret not in serialized


@pytest.mark.asyncio
async def test_delete_student_replay_and_restore_journal(auth_app, source_tree, tmp_path):
    auth_app.state.settings.deletion_journal = tmp_path / "deletions.jsonl"
    auth_app.state.settings.backup_retention_days = 7
    students = await prepare(auth_app, source_tree)
    async with auth_app.state.database.sessions() as db:
        student = await db.get(Student, students[0])
        fields = {column.key: getattr(student, column.key) for column in Student.__table__.columns}
    async with (
        client_for(auth_app) as parent,
        client_for(auth_app) as child,
        client_for(auth_app) as sibling,
    ):
        await parent_login(parent)
        await login_child(child)
        await login_child(sibling, 1)
        path = f"/api/v1/students/{students[0]}?confirm={students[0]}"
        key = str(uuid4())
        assert (await child.delete(path, headers={"Idempotency-Key": key})).status_code == 403
        deleted = await parent.delete(path, headers={"Idempotency-Key": key})
        assert deleted.status_code == 204, deleted.text
        assert (await parent.delete(path, headers={"Idempotency-Key": key})).status_code == 204
        assert (await child.get("/api/v1/auth/session")).status_code == 401
        assert (await sibling.get("/api/v1/learning/profile")).status_code == 200
        assert (await parent.get(f"/api/v1/students/{students[1]}")).status_code == 200
        assert (
            await parent.delete(
                f"/api/v1/students/{students[1]}?confirm={students[1]}",
                headers={"Idempotency-Key": key},
            )
        ).status_code == 409
    async with auth_app.state.database.sessions() as db:
        assert await db.scalar(select(User).where(User.login_name == "learning-child-0")) is None
        db.add(Student(**fields))  # 模拟从删除前备份恢复目标档案。
        await db.commit()
        assert await replay_deletions(db, auth_app.state.settings) == 1
        assert await db.get(Student, students[0]) is None
        assert await db.get(Student, students[1]) is not None
    record = json.loads(auth_app.state.settings.deletion_journal.read_text())
    assert set(record) == {"kind", "id", "requested_at", "expires_at"}


@pytest.mark.asyncio
async def test_family_delete_owner_only_preserves_deployment_admin(auth_app, source_tree, tmp_path):
    auth_app.state.settings.deletion_journal = tmp_path / "deletions.jsonl"
    students = await prepare(auth_app, source_tree)
    async with auth_app.state.database.sessions() as db:
        family = (await db.get(Student, students[0])).family_id
        guardian = await create_account(
            db,
            login_name="guardian",
            password=ACCOUNT["password"],
            nickname="监护人",
            role="parent",
        )
        db.add(Membership(user_id=guardian.id, family_id=family, role="guardian"))
        admin = await create_account(
            db,
            login_name="privacy-admin",
            password=ACCOUNT["password"],
            nickname="管理员",
            role="admin",
        )
        admin_id = admin.id
        await db.commit()
    async with (
        client_for(auth_app) as parent,
        client_for(auth_app) as guardian,
        client_for(auth_app) as admin,
    ):
        await parent_login(parent)
        for client, login in [(guardian, "guardian"), (admin, "privacy-admin")]:
            assert (
                await client.post(
                    "/api/v1/auth/login", json={"login": login, "password": ACCOUNT["password"]}
                )
            ).status_code == 200
            csrf(client)
        endpoint = f"/api/v1/account?confirm={family}"
        for client in [guardian, admin]:
            assert (
                await client.delete(endpoint, headers={"Idempotency-Key": str(uuid4())})
            ).status_code == 403
        assert (await admin.get("/api/v1/family/export")).status_code == 403
        deleted = await parent.delete(endpoint, headers={"Idempotency-Key": str(uuid4())})
        assert deleted.status_code == 204, deleted.text
        assert (await guardian.get("/api/v1/auth/session")).status_code == 401
        assert (await admin.get("/api/v1/auth/session")).status_code == 200
    async with auth_app.state.database.sessions() as db:
        assert await db.get(User, admin_id) is not None
        assert await db.scalar(select(func.count()).select_from(Student)) == 0
        assert await db.scalar(select(func.count()).select_from(StudentAccount)) == 0


@pytest.mark.asyncio
async def test_delete_serializes_with_inflight_attempt_and_preserves_sibling(
    auth_app, source_tree, tmp_path
):
    auth_app.state.settings.deletion_journal = tmp_path / "deletions.jsonl"
    students = await prepare(auth_app, source_tree)
    async with client_for(auth_app) as parent, client_for(auth_app) as child:
        await parent_login(parent)
        await login_child(child)
        started = await post(
            child,
            f"/students/{students[0]}/learning-sessions",
            {"kind": "lesson", "book_id": "g1up", "source_id": "g1up-u1-kp1", "client_at": now()},
        )
        session = started.json()
        attempt, deleted = await asyncio.wait_for(
            asyncio.gather(
                post(
                    child,
                    f"/learning-sessions/{session['id']}/attempts",
                    {
                        "revision": session["revision"],
                        "client_at": now(),
                        "question_uid": session["question"]["uid"],
                        "question_version": session["question"]["version"],
                        "answer": "1/2",
                    },
                ),
                parent.delete(
                    f"/api/v1/students/{students[0]}?confirm={students[0]}",
                    headers={"Idempotency-Key": str(uuid4())},
                ),
            ),
            timeout=15,
        )
        assert attempt.status_code in {200, 401, 404}
        assert deleted.status_code == 204, deleted.text
        assert (await child.get("/api/v1/learning/profile")).status_code == 401
    async with auth_app.state.database.sessions() as db:
        assert await db.get(Student, students[0]) is None
        assert await db.get(Student, students[1]) is not None
        assert await db.scalar(select(func.count()).select_from(Attempt)) == 0
        assert await db.scalar(select(func.count()).select_from(RewardLedger)) == 0


def test_expired_deletion_intents_only_removed_after_explicit_purge(tmp_path):
    from types import SimpleNamespace

    path = tmp_path / "deletions.jsonl"
    now = datetime.now(UTC)
    records = [
        {
            "kind": "student",
            "id": str(uuid4()),
            "requested_at": now.isoformat(),
            "expires_at": (now + timedelta(days=days)).isoformat(),
        }
        for days in [-1, 1]
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in records))
    assert purge_expired_journal(SimpleNamespace(deletion_journal=path)) == 1
    assert [json.loads(line) for line in path.read_text().splitlines()] == records[1:]
