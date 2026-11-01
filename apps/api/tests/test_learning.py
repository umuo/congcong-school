import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.auth.models import StudentAccount, User
from app.auth.service import create_account
from app.content.import_content import import_content
from app.learning.models import Attempt, LearningEvent
from app.students.models import Student
from tests import test_content as content_fixtures
from tests.test_auth import ACCOUNT, client_for, provision_parent
from tests.test_child_mode import csrf
from tests.test_content import seed_catalog


@pytest.fixture
def source_tree(tmp_path):
    return content_fixtures.source_tree.__wrapped__(tmp_path)


async def prepare(app, root):
    await seed_catalog(app)
    async with app.state.database.sessions() as db:
        await import_content(db, root)
    parent = await provision_parent(app, {**ACCOUNT, "nickname": "家长"})
    students = []
    async with app.state.database.sessions() as db:
        for index in range(2):
            student = Student(family_id=UUID(parent["family"]["id"]), nickname=f"孩子{index}")
            db.add(student)
            await db.flush()
            user = await create_account(
                db,
                login_name=f"learning-child-{index}",
                password=ACCOUNT["password"],
                nickname=student.nickname,
                role="student",
            )
            db.add(
                StudentAccount(user_id=user.id, family_id=student.family_id, student_id=student.id)
            )
            students.append(student.id)
        await db.commit()
    async with client_for(app) as client:
        await client.post("/api/v1/auth/login", json=ACCOUNT)
        csrf(client)
        for student_id in students:
            result = await client.put(
                f"/api/v1/students/{student_id}/curriculum",
                headers={"If-Match": "1"},
                json={"subjects": [{"subject_code": "math", "enabled": True, "book_id": "g1up"}]},
            )
            assert result.status_code == 200, result.text
    return students


def now():
    return datetime.now(UTC).isoformat()


async def post(client, path, body, key=None):
    return await client.post(
        "/api/v1" + path, json=body, headers={"Idempotency-Key": str(key or uuid4())}
    )


async def login_child(client, index=0):
    result = await client.post(
        "/api/v1/auth/login",
        json={"login": f"learning-child-{index}", "password": ACCOUNT["password"]},
    )
    assert result.status_code == 200
    csrf(client)


@pytest.mark.asyncio
async def test_attempt_versions_order_idempotency_and_cross_device_checkpoint(
    auth_app, source_tree
):
    first, second = await prepare(auth_app, source_tree)
    async with client_for(auth_app) as a, client_for(auth_app) as b:
        await login_child(a)
        await login_child(b)
        body = {"kind": "lesson", "book_id": "g1up", "source_id": "g1up-u1-kp1", "client_at": now()}
        key = uuid4()
        started = await post(a, f"/students/{first}/learning-sessions", body, key)
        assert started.status_code == 200, started.text
        session = started.json()
        sid = session["id"]
        assert "answer" not in session["question"] and session["feedback"] is None
        assert "explanation" not in session["question"].get("audio", {})
        assert (await post(a, f"/students/{first}/learning-sessions", body, key)).json() == session
        assert (
            await post(
                a, f"/students/{first}/learning-sessions", {**body, "source_id": "g1up-u2-kp1"}, key
            )
        ).status_code == 409
        draft = {
            "revision": 1,
            "client_at": now(),
            "answer": "草稿",
            "intro_page": 1,
            "visual_draft": [1, 2],
        }
        result = await a.put(
            f"/api/v1/learning-sessions/{sid}/checkpoint",
            json=draft,
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert result.status_code == 200, result.text
        session = (await b.get(f"/api/v1/learning-sessions/{sid}")).json()
        assert session["checkpoint"]["draft"]["answer"] == "草稿"
        q = session["question"]
        answer = {
            "revision": session["revision"],
            "client_at": now(),
            "question_uid": q["uid"],
            "question_version": q["version"],
            "answer": "1/3",
            "declared_duration_ms": 1234,
        }
        path = f"/learning-sessions/{sid}/attempts"
        assert (await post(a, path, {**answer, "isCorrect": True, "xp": 100})).status_code == 422
        assert (await post(a, path, {**answer, "question_uid": "f" * 64})).status_code == 409
        assert (await post(a, path, {**answer, "question_version": "f" * 64})).status_code == 409
        key = uuid4()
        result = await post(a, path, answer, key)
        assert result.status_code == 200, result.text
        session = result.json()
        assert session["feedback"]["correct"] is False
        assert session["feedback"]["answer"] == "1/2"
        assert (await post(b, path, answer, key)).json() == session
        assert (await post(a, path, {**answer, "answer": "1/2"}, key)).status_code == 409
        assert (await post(a, path, answer)).status_code == 409
        assert (await b.get(f"/api/v1/learning-sessions/{sid}")).json()["feedback"] == session[
            "feedback"
        ]
        lesson_path = source_tree / "apps/web/public/data/books/g1up/lessons/g1up-u1-kp1.json"
        raw = json.loads(lesson_path.read_text())
        raw["questions"][0]["answer"] = "1/3"
        lesson_path.write_text(json.dumps(raw))
        async with auth_app.state.database.sessions() as db:
            await import_content(db, source_tree)
        advanced = await post(
            a,
            f"/learning-sessions/{sid}/advance",
            {"revision": session["revision"], "client_at": now()},
        )
        assert advanced.status_code == 200, advanced.text
        session = advanced.json()
        assert session["question"]["version"] == q["version"]
        # 连续答错也追加独立历史，不能被错题汇总覆盖。
        answer.update(revision=session["revision"], client_at=now(), answer="1/3")
        repeated = await post(b, path, answer)
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["feedback"]["correct"] is False
        moved = await post(
            b,
            f"/learning-sessions/{sid}/advance",
            {
                "revision": repeated.json()["revision"],
                "client_at": now(),
            },
        )
        assert moved.status_code == 200, moved.text
        session = moved.json()
        answer.update(revision=session["revision"], client_at=now(), answer="1/2")
        result = await post(b, path, answer)
        assert result.status_code == 200, result.text
        session = result.json()
        assert session["feedback"]["correct"] is True and not session["feedback"]["first_attempt"]
        assert session["checkpoint"]["first_correct"] == 0
        advanced = await post(
            b,
            f"/learning-sessions/{sid}/advance",
            {"revision": session["revision"], "client_at": now()},
        )
        assert advanced.json()["question"] is None
        assert (await post(a, path, answer)).status_code == 409
        events = (await a.get(f"/api/v1/students/{first}/changes?after=0&limit=2")).json()
        assert [e["cursor"] for e in events["events"]] == [1, 2]
        rest = (await a.get(f"/api/v1/students/{first}/changes?after=2")).json()
        assert [e["cursor"] for e in rest["events"]] == [3, 4, 5, 6, 7, 8]
        assert (await a.get(f"/api/v1/students/{second}/changes")).status_code == 404
        async with auth_app.state.database.sessions() as db:
            attempts = (await db.scalars(select(Attempt).order_by(Attempt.ordinal))).all()
            assert len(attempts) == 3
            assert [r.answer for r in attempts] == ["1/3", "1/3", "1/2"]
            assert all(
                r.question_version == q["version"] and r.declared_duration_ms == 1234
                for r in attempts
            )
            assert all(r.received_at and r.client_at for r in attempts)
            assert await db.scalar(select(func.count()).select_from(LearningEvent)) == 8
            with pytest.raises(IntegrityError):
                await db.execute(update(Attempt).values(correct=True))
                await db.commit()
            await db.rollback()


@pytest.mark.asyncio
async def test_learning_identity_scope_archive_and_disabled_account(auth_app, source_tree):
    first, second = await prepare(auth_app, source_tree)
    other = await provision_parent(
        auth_app,
        {
            "email": "other-learning@example.com",
            "password": ACCOUNT["password"],
            "nickname": "其他家庭",
        },
    )
    async with auth_app.state.database.sessions() as db:
        outsider = Student(family_id=UUID(other["family"]["id"]), nickname="其他学生")
        db.add(outsider)
        await create_account(
            db,
            login_name="learning-admin",
            password=ACCOUNT["password"],
            nickname="管理员",
            role="admin",
            must_change_password=False,
        )
        await db.commit()
        outside_id = outsider.id
    async with client_for(auth_app) as admin:
        assert (
            await admin.post(
                "/api/v1/auth/login",
                json={
                    "login": "learning-admin",
                    "password": ACCOUNT["password"],
                },
            )
        ).status_code == 200
        csrf(admin)
        assert (
            await post(
                admin,
                f"/students/{first}/learning-sessions",
                {
                    "kind": "lesson",
                    "book_id": "g1up",
                    "source_id": "g1up-u1-kp1",
                    "client_at": now(),
                },
            )
        ).status_code == 403
    async with (
        client_for(auth_app) as child,
        client_for(auth_app) as sibling,
        client_for(auth_app) as parent,
    ):
        await login_child(child)
        await login_child(sibling, 1)
        await parent.post("/api/v1/auth/login", json=ACCOUNT)
        csrf(parent)
        body = {"kind": "lesson", "book_id": "g1up", "source_id": "g1up-u1-kp1", "client_at": now()}
        assert (await post(parent, f"/students/{first}/learning-sessions", body)).status_code == 403
        for forbidden in [second, outside_id, uuid4()]:
            assert (
                await post(child, f"/students/{forbidden}/learning-sessions", body)
            ).status_code == 404
        session = (await post(child, f"/students/{first}/learning-sessions", body)).json()
        sid = session["id"]
        q = session["question"]
        attempt = {
            "revision": 1,
            "client_at": now(),
            "question_uid": q["uid"],
            "question_version": q["version"],
            "answer": "1/2",
        }
        assert (await sibling.get(f"/api/v1/learning-sessions/{sid}")).status_code == 404
        missing = await sibling.get(f"/api/v1/learning-sessions/{uuid4()}")
        foreign = await sibling.get(f"/api/v1/learning-sessions/{sid}")
        assert missing.json()["code"] == foreign.json()["code"]
        assert (
            await post(sibling, f"/learning-sessions/{sid}/attempts", attempt)
        ).status_code == 404
        assert (
            await parent.post("/api/v1/mode/child", json={"student_id": str(first)})
        ).status_code == 200
        csrf(parent)
        assert (await parent.get(f"/api/v1/learning-sessions/{sid}")).status_code == 200
        async with auth_app.state.database.sessions() as db:
            await db.execute(
                update(Student).where(Student.id == first).values(archived_at=datetime.now(UTC))
            )
            await db.commit()
        assert (await post(child, f"/learning-sessions/{sid}/attempts", attempt)).status_code == 409
        async with auth_app.state.database.sessions() as db:
            await db.execute(update(Student).where(Student.id == first).values(archived_at=None))
            await db.execute(
                update(User).where(User.login_name == "learning-child-0").values(is_active=False)
            )
            await db.commit()
        assert (await post(child, f"/learning-sessions/{sid}/attempts", attempt)).status_code == 401
        async with auth_app.state.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Attempt)) == 0


@pytest.mark.asyncio
async def test_learning_kinds_do_not_mix_sources_or_current_versions(auth_app, source_tree):
    first, _ = await prepare(auth_app, source_tree)
    from datetime import timedelta

    from app.learning import economy as rules
    from app.learning.economy_service import clock, load_state
    from app.students.models import Student

    async with auth_app.state.database.sessions() as db:
        student = await db.get(Student, first)
        row, state = await load_state(db, student)
        _, day = await clock(db, student)
        state["numberSenseProgress"]["count"] = {
            "version": rules.POLICY["number_version"],
            "practicedOn": (day - timedelta(days=1)).isoformat(),
            "nextReviewOn": day.isoformat(),
            "evidence": {},
        }
        row.payload = state
        await db.commit()
    async with client_for(auth_app) as client:
        await login_child(client)
        path = f"/students/{first}/learning-sessions"
        cases = [
            {"kind": "challenge", "book_id": "g1up", "source_id": "g1up-u1-exam"},
            {"kind": "story", "book_id": "g1up", "source_id": "g1up-s1"},
            {"kind": "jump", "book_id": "g1up", "target_unit": 2},
            {"kind": "number_review", "number_skill": "count"},
        ]
        for source in cases:
            result = await post(client, path, {**source, "client_at": now()})
            assert result.status_code == 200, result.text
            row = result.json()
            q = row["question"]
            assert q and "answer" not in q and row["feedback"] is None
            checked = await post(
                client,
                f"/learning-sessions/{row['id']}/attempts",
                {
                    "revision": row["revision"],
                    "client_at": now(),
                    "question_uid": q["uid"],
                    "question_version": q["version"],
                    "answer": "wrong",
                },
            )
            assert checked.status_code == 200, checked.text
            row = checked.json()
            moved = await post(
                client,
                f"/learning-sessions/{row['id']}/advance",
                {
                    "revision": row["revision"],
                    "client_at": now(),
                },
            )
            assert moved.status_code == 200, moved.text
            pending = moved.json()["checkpoint"]["pending"]
            if source["kind"] in {"story", "jump"}:
                assert pending == []
            else:
                assert pending[-1] == 0
        review = await post(client, path, {"kind": "review", "client_at": now()})
        assert review.status_code == 200, review.text
        assert review.json()["question"] and review.json()["sources"] == []
        for bad in [
            {"kind": "lesson", "book_id": "g1up", "source_id": "g1up-u1-exam"},
            {"kind": "story", "book_id": "g1up", "source_id": "g1up-u1-kp1"},
        ]:
            assert (await post(client, path, {**bad, "client_at": now()})).status_code == 404
        assert (
            await post(
                client,
                path,
                {"kind": "jump", "book_id": "g1up", "target_unit": 99, "client_at": now()},
            )
        ).status_code == 404
        assert (
            await post(
                client,
                path,
                {
                    "kind": "lesson",
                    "book_id": "g1up",
                    "source_id": "g1up-u1-kp1",
                    "revision": 1,
                    "client_at": now(),
                },
            )
        ).status_code == 422


def test_jump_sampling_matches_existing_typescript_vectors():
    from pathlib import Path

    from app.learning.sampling import sample_jump

    path = Path(__file__).resolve().parents[3] / "packages/core/spec/jump-vectors.json"
    for case in json.loads(path.read_text()):
        sources = [
            {
                "lesson_id": f"lesson-{i}",
                "question_refs": [
                    {"uid": f"lesson-{i}:{j + 1}", "version": "fixture"} for j in range(n)
                ],
            }
            for i, n in enumerate(case["counts"])
        ]
        result = sample_jump(sources, case["seed"], case["size"])
        assert [r["uid"] for r in result] == case["expected"]


def test_review_intervals_match_existing_golden_vectors():
    from datetime import date
    from pathlib import Path

    from app.learning.review import review_entry

    path = Path(__file__).resolve().parents[3] / "packages/core/spec/golden-vectors.json"
    day = date(2026, 11, 1)
    for case in json.loads(path.read_text())["srsReview"]:
        result = review_entry({"box": case["box"], "correct_count": 0}, case["isCorrect"], day)
        assert result["box"] == case["expBox"]
        assert (result["due"] - day).days == case["expIntervalDays"]


def test_openapi_separates_public_question_and_post_answer_feedback():
    from app.config import Settings
    from app.main import create_app

    spec = create_app(
        Settings(_env_file=None, database_url="postgresql+psycopg://test:test@localhost/test")
    ).openapi()
    schemas = spec["components"]["schemas"]
    assert "answer" not in schemas["PublicQuestion"]["properties"]
    assert "explanation" not in schemas["PublicQuestion"]["properties"]
    assert schemas["PublicQuestion"]["additionalProperties"] is False
    assert schemas["AnswerBody"]["additionalProperties"] is False
    assert "answer" in schemas["AnswerFeedback"]["properties"]
