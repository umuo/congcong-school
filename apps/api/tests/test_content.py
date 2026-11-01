import copy
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from app.content.import_content import ContentSourceError, import_content, load_content
from app.content.models import ContentContainer, ContentRevision, QuestionIdentity, QuestionVersion
from app.content.schemas import public_question
from app.content.service import content_revision, fixed_question, jump_pool, resolve_question
from app.curriculum.models import Subject, Textbook
from app.errors import APIError
from tests.test_auth import ACCOUNT, client_for, provision_parent

ROOT = Path(__file__).resolve().parents[3]


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


def question(qid=1, answer="1/2"):
    return {
        "id": qid,
        "type": "fill_blank",
        "question": "测试题\u0000保留原文",
        "options": [],
        "answer": answer,
        "explanation": "仅作答后返回",
        "difficulty": 1,
        "score": 5,
        "knowledge_point": "同名原标签",
        "audio": {"question": "/audio/prompt.mp3", "explanation": "/audio/secret-explanation.mp3"},
    }


@pytest.fixture
def source_tree(tmp_path):
    write(
        tmp_path,
        "apps/web/public/data/index.json",
        {"books": [{"id": "g1up", "hasStories": True, "hasPassages": True}, {"id": "g1up-2026"}]},
    )
    for book in ["g1up", "g1up-2026"]:
        prefix = f"apps/web/public/data/books/{book}"
        write(
            tmp_path,
            f"{prefix}/outline.json",
            {
                "bookId": book,
                "lessons": [{"id": f"{book}-u1-kp1"}, {"id": f"{book}-u2-kp1"}],
                "units": [
                    {"unit_number": 1, "examLessonId": f"{book}-u1-exam"},
                    {"unit_number": 2},
                ],
            },
        )
        for suffix, unit in [("u1-kp1", 1), ("u2-kp1", 2), ("u1-exam", 1)]:
            source = f"{book}-{suffix}"
            write(
                tmp_path,
                f"{prefix}/lessons/{source}.json",
                {
                    "id": source,
                    "bookId": book,
                    "title": "同名课程\u0000保留原文",
                    "unitNumber": unit,
                    "questions": [question()],
                },
            )
    write(
        tmp_path,
        "apps/web/public/data/books/g1up/stories.json",
        {
            "bookId": "g1up",
            "stories": [
                {
                    "id": "g1up-s1",
                    "bookId": "g1up",
                    "title": "测试故事",
                    "unitNumber": 1,
                    "sentences": [{"text": "故事正文", "audio": "/audio/story.mp3"}],
                    "questions": [question()],
                }
            ],
        },
    )
    write(
        tmp_path,
        "apps/web/public/data/books/g1up/passages.json",
        {
            "bookId": "g1up",
            "passages": [
                {
                    "id": "g1up-p1",
                    "bookId": "g1up",
                    "title": "测试听读",
                    "unitNumber": 1,
                    "sentences": [{"text": "听读正文"}],
                }
            ],
        },
    )
    generator = b"fixture number review generator v1"
    path = tmp_path / "packages/core/src/numberSense.ts"
    path.parent.mkdir(parents=True)
    path.write_bytes(generator)
    banks = []
    for skill in ["count", "compare", "apply"]:
        for variant in ["even", "odd"]:
            banks.append(
                {
                    "skill": skill,
                    "variant": variant,
                    "questions": [
                        question(2001, "7" if variant == "odd" else "9"),
                        question(2002, "4" if variant == "odd" else "7"),
                    ],
                }
            )
    write(
        tmp_path,
        "apps/api/private-content/number-review.json",
        {
            "generator_version": 1,
            "source_hash": hashlib.sha256(generator).hexdigest(),
            "banks": banks,
        },
    )
    return tmp_path


def test_source_identity_variants_missing_and_invalid_content(source_tree):
    batch = load_content(source_tree)
    assert batch.summary() == {
        "containers": 14,
        "question_identities": 13,
        "question_versions": 19,
        "unmapped_files": [],
    }
    repeated = [i for i in batch.identities.values() if i["source_question_id"] == 1]
    assert len({i["uid"] for i in repeated}) == 7
    # 同名课程/知识点不构成跨课、跨教材或课程/挑战/故事的同一身份。
    assert len({i["source_id"] for i in repeated}) >= 5
    path = source_tree / "apps/web/public/data/books/g1up/lessons/g1up-u1-kp1.json"
    original = path.read_text()
    raw = json.loads(original)
    raw["questions"].append(copy.deepcopy(raw["questions"][0]))
    path.write_text(json.dumps(raw))
    with pytest.raises(ContentSourceError, match="Duplicate question"):
        load_content(source_tree)
    path.write_text(original)
    path.unlink()
    with pytest.raises(ContentSourceError, match="Missing or invalid"):
        load_content(source_tree)


def test_stale_generator_and_unmapped_files_are_explicit(source_tree):
    extra = "apps/web/public/data/books/g1up/lessons/g1up-unmapped.json"
    write(source_tree, extra, {"id": "g1up-unmapped"})
    assert load_content(source_tree).unmapped_files == [extra]
    path = source_tree / "packages/core/src/numberSense.ts"
    path.write_text("changed generator")
    with pytest.raises(ContentSourceError, match="Stale number-review"):
        load_content(source_tree)


async def seed_catalog(app):
    async with app.state.database.sessions() as db:
        db.add(Subject(code="math", name="数学"))
        await db.flush()
        for book in ["g1up", "g1up-2026"]:
            db.add(
                Textbook(
                    id=book,
                    subject_code="math",
                    title=book,
                    grade=1,
                    school_system="6-3",
                    semester="up",
                    units=[],
                    provenance={},
                    content_revision="a" * 64,
                )
            )
        await db.commit()


@pytest.mark.asyncio
async def test_immutable_versions_reimport_retirement_and_no_answer_metadata(auth_app, source_tree):
    await seed_catalog(auth_app)
    async with auth_app.state.database.sessions() as db:
        summary = await import_content(db, source_tree)
        await import_content(db, source_tree)
        assert await db.scalar(select(func.count()).select_from(QuestionIdentity)) == 13
        assert await db.scalar(select(func.count()).select_from(QuestionVersion)) == 19
        head, old = await content_revision(db, "g1up", "lesson", "g1up-u1-kp1")
        original_ref = old.question_refs[0]
        original_version = old.version
        original_uid = original_ref["uid"]
        old_question = await fixed_question(db, original_uid, original_ref["version"])
        assert old_question.private_payload["answer"] == "1/2"
        assert old_question.private_payload["question"] == "测试题\u0000保留原文"
        assert old.public_payload["title"] == "同名课程\u0000保留原文"
        public = public_question(
            old_question.private_payload, uid=original_uid, version=original_ref["version"]
        )
        assert "answer" not in public and "explanation" not in public
        assert public["audio"] == {"question": "/audio/prompt.mp3"}
        pool = await jump_pool(db, "g1up", 2)
        assert len(pool) == 1 and pool[0]["question_refs"][0]["uid"] == original_uid
        with pytest.raises(APIError) as missing:
            await resolve_question(db, "lesson", "g1up", "not-mapped", 1)
        assert missing.value.status_code == 404
        path = source_tree / "apps/web/public/data/books/g1up/lessons/g1up-u1-kp1.json"
        raw = json.loads(path.read_text())
        raw["questions"][0]["answer"] = "1/3"
        path.write_text(json.dumps(raw))
        await import_content(db, source_tree)
        current_head, current = await content_revision(db, "g1up", "lesson", "g1up-u1-kp1")
        assert current.version != original_version
        assert current.question_refs[0]["uid"] == original_uid
        assert current.question_refs[0]["version"] != original_ref["version"]
        assert (await fixed_question(db, original_uid, original_ref["version"])).private_payload[
            "answer"
        ] == "1/2"
        assert (await content_revision(db, "g1up", "lesson", "g1up-u1-kp1", original_version))[
            1
        ].version == original_version
        assert await db.scalar(select(func.count()).select_from(QuestionVersion)) == 20
        assert (
            await db.scalar(select(func.count()).select_from(ContentRevision))
            == summary["containers"] + 1
        )
        # 数据库拒绝修改/删除内容版本和改写身份，包括绕过 ORM 的 SQL。
        for statement in [
            update(QuestionVersion)
            .where(QuestionVersion.uid == original_uid)
            .values(private_payload={}),
            delete(QuestionVersion).where(QuestionVersion.uid == original_uid),
            update(QuestionIdentity)
            .where(QuestionIdentity.uid == original_uid)
            .values(source_id="other"),
            update(ContentRevision)
            .where(ContentRevision.container_id == head.id)
            .values(public_payload={}),
            update(ContentContainer)
            .where(ContentContainer.id == head.id)
            .values(source_id="other"),
        ]:
            await db.commit()
            with pytest.raises(IntegrityError):
                await db.execute(statement)
                await db.commit()
            await db.rollback()
        # 完整发布不再列出旧课时：停用入口，保留版本供既有会话追溯。
        outline_path = source_tree / "apps/web/public/data/books/g1up/outline.json"
        outline = json.loads(outline_path.read_text())
        outline["lessons"] = outline["lessons"][1:]
        outline_path.write_text(json.dumps(outline))
        result = await import_content(db, source_tree)
        assert result["unmapped_files"]
        with pytest.raises(APIError) as retired:
            await content_revision(db, "g1up", "lesson", "g1up-u1-kp1")
        assert retired.value.status_code == 404
        assert (await fixed_question(db, original_uid, original_ref["version"])).private_payload[
            "answer"
        ] == "1/2"
    await provision_parent(auth_app, {**ACCOUNT, "nickname": "家长"})
    async with client_for(auth_app) as client:
        assert (await client.get("/api/v1/content/books/g1up")).status_code == 401
        await client.post("/api/v1/auth/login", json=ACCOUNT)
        listed = (await client.get("/api/v1/content/books/g1up")).json()
        assert len(listed) == 10
        body = (await client.get("/api/v1/content/books/g1up/challenge/g1up-u1-exam")).json()
        assert body["question_refs"] and "questions" not in body["metadata"]
        assert "secret-explanation" not in json.dumps(body)
        assert (await client.get("/api/v1/content/books/g1up/lesson/unknown")).status_code == 404
        assert (
            await client.get(
                "/api/v1/content/question-mapping",
                params={
                    "kind": "lesson",
                    "book_id": "g1up",
                    "source_id": "unknown",
                    "question_id": 1,
                },
            )
        ).status_code == 404
