import asyncio
import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.auth.models import StudentAccount
from app.auth.service import create_account
from app.curriculum.import_catalog import import_catalog, load_catalog
from app.curriculum.models import Subject, Textbook
from tests.test_auth import ACCOUNT, client_for, provision_parent

ROOT = Path(__file__).resolve().parents[3]


def test_catalog_preserves_ids_and_known_source_metadata():
    subjects, books = load_catalog(ROOT)
    source = json.loads((ROOT / "apps/web/public/data/index.json").read_text())
    assert {b["id"] for b in books} == {b["id"] for b in source["books"]}
    assert {s["code"] for s in subjects} == {"math", "chinese", "english", "science"}
    old = next(b for b in books if b["id"] == "g1up")
    assert old["publication_year"] is None
    assert old["isbn"] is None
    assert old["superseded_by"] == "g1up-2026"
    five_four = [b for b in books if b["school_system"] == "5-4"]
    assert len(five_four) == 26
    assert all(b["isbn"] and b["publication_year"] and b["source_edition"] for b in five_four)

    def no_private_fields(value):
        if isinstance(value, dict):
            assert not {"answer", "explanation", "questions"}.intersection(value)
            for item in value.values():
                no_private_fields(item)
        elif isinstance(value, list):
            for item in value:
                no_private_fields(item)

    for book in books:
        no_private_fields(book["units"])


@pytest.mark.asyncio
async def test_curriculum_history_isolation_conflicts_and_subject_extension(auth_app):
    async with auth_app.state.database.sessions() as db:
        seeded = await import_catalog(db, ROOT)
        await import_catalog(db, ROOT)
        assert await db.scalar(select(func.count()).select_from(Textbook)) == seeded["textbooks"]
        db.add(Subject(code="history", name="历史"))
        await db.commit()
    async with client_for(auth_app) as client:
        await provision_parent(auth_app, {**ACCOUNT, "nickname": "家长"})
        await client.post("/api/v1/auth/login", json=ACCOUNT)
        client.headers["X-CSF-CSRF"] = client.cookies["csf_csrf"]
        assert "history" in {s["code"] for s in (await client.get("/api/v1/subjects")).json()}
        children = [
            (await client.post("/api/v1/students", json={"nickname": name, "grade": 1})).json()
            for name in ["姐姐", "弟弟"]
        ]
        child = children[0]
        route = "/api/v1/students/" + child["id"] + "/curriculum"
        other_route = "/api/v1/students/" + children[1]["id"] + "/curriculum"
        books = (
            await client.get("/api/v1/textbooks?subject_code=math&grade=1&province=广东")
        ).json()
        assert books["recommendations"] == []
        assert books["recommendation_reason"] == "NO_VERIFIED_REGIONAL_DATA"
        replacement = next(
            b for b in books["items"] if b["school_system"] == "5-4" and b["semester"] == "up"
        )
        choices = [
            {"subject_code": "math", "enabled": True, "book_id": "g1up", "current_unit_number": 1},
            {"subject_code": "chinese", "enabled": True, "book_id": "chinese-g1up"},
            {"subject_code": "history", "enabled": True},
        ]
        saved = await client.put(route, json={"subjects": choices}, headers={"If-Match": "1"})
        assert saved.status_code == 200, saved.text
        assert saved.json()["revision"] == 2
        assert len(saved.json()["history"]) == 2
        # 为已有教材历史的学生开通独立账号，只增加绑定，不复制档案或历史。
        async with auth_app.state.database.sessions() as db:
            from app.students.models import Student

            profile = await db.get(Student, UUID(child["id"]))
            student_user = await create_account(
                db,
                login_name="curriculum-child",
                password=ACCOUNT["password"],
                nickname="姐姐",
                role="student",
                must_change_password=False,
            )
            db.add(
                StudentAccount(
                    user_id=student_user.id, family_id=profile.family_id, student_id=profile.id
                )
            )
            await db.commit()
        async with client_for(auth_app) as student_client:
            assert (
                await student_client.post(
                    "/api/v1/auth/login",
                    json={"login": "curriculum-child", "password": ACCOUNT["password"]},
                )
            ).status_code == 200
            own = (await student_client.get("/api/v1/learning/curriculum")).json()
            assert own["student_id"] == child["id"]
            assert (
                next(s for s in own["subjects"] if s["subject_code"] == "math")["book_id"] == "g1up"
            )
            assert "history" not in own
            assert (await student_client.get(other_route)).status_code == 403
        assert len((await client.get(route)).json()["history"]) == 2
        assert (await client.get(other_route)).json()["subjects"] == []
        # 一个非法配置使整个请求回滚，包括已处理学科及学生 revision。
        invalid = await client.put(
            route,
            json={
                "subjects": [
                    {"subject_code": "math", "enabled": False},
                    {"subject_code": "not_in_catalog", "enabled": True},
                ]
            },
            headers={"If-Match": "2"},
        )
        assert invalid.status_code == 422
        actual = (await client.get(route)).json()
        assert actual["revision"] == 2
        assert next(s for s in actual["subjects"] if s["subject_code"] == "math")["enabled"]
        changed = await client.put(
            route,
            json={
                "subjects": [
                    {
                        "subject_code": "math",
                        "enabled": True,
                        "book_id": replacement["id"],
                    }
                ]
            },
            headers={"If-Match": "2"},
        )
        assert changed.status_code == 200
        history = changed.json()["history"]
        old = next(h for h in history if h["book_id"] == "g1up")
        assert old["ended_at"] is not None
        assert old["snapshot"]["id"] == "g1up"
        assert old["snapshot"]["publication_year"] is None
        assert any(h["book_id"] == replacement["id"] and h["ended_at"] is None for h in history)
        # 同一版本并发修改只允许一个写入成功。
        result = await asyncio.gather(
            *[
                client.put(
                    route,
                    json={"subjects": [{"subject_code": "math", "enabled": False}]},
                    headers={"If-Match": "3"},
                )
                for _ in range(2)
            ]
        )
        assert sorted(r.status_code for r in result) == [200, 409]
        disabled = (await client.get(route)).json()
        assert len(disabled["history"]) == 3
        assert not next(s for s in disabled["subjects"] if s["subject_code"] == "math")["enabled"]
        # 升年级不改学生身份，也不移除教材快照。
        promoted = await client.patch(
            "/api/v1/students/" + child["id"], json={"grade": 2}, headers={"If-Match": "4"}
        )
        assert promoted.status_code == 200
        assert promoted.json()["id"] == child["id"]
        assert len((await client.get(route)).json()["history"]) == 3
        archived = await client.post(
            "/api/v1/students/" + child["id"] + "/archive", headers={"If-Match": "5"}
        )
        assert archived.status_code == 200
        denied = await client.put(route, json={"subjects": []}, headers={"If-Match": "6"})
        assert denied.status_code == 409
        assert len((await client.get(route)).json()["history"]) == 3
