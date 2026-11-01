"""受信任本地内容导入；不修改原教材，版本与答案只追加到私有数据库。"""

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.content.models import ContentContainer, ContentRevision, QuestionIdentity, QuestionVersion
from app.content.schemas import PrivateQuestion
from app.database import Database
from app.learning.grading import GRADING_RULE_VERSION

SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,159}$")


class ContentSourceError(ValueError):
    pass


def digest(value):
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def container_id(kind, book_id, source_id):
    return digest(["content-v1", kind, book_id, source_id])


def question_uid(kind, book_id, source_id, question_id):
    return digest(["question-v1", kind, book_id, source_id, question_id])


def read_source(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ContentSourceError(f"Source outside content root: {relative}")
    try:
        raw = path.read_bytes()
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError):
        raise ContentSourceError(f"Missing or invalid content source: {relative}") from None


def check_id(value):
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ContentSourceError("Invalid content identity")
    return value


def public_metadata(raw, kind):
    keys = {
        "id",
        "bookId",
        "title",
        "unitNumber",
        "unitTitle",
        "unitLabel",
        "kpIndex",
        "kpTotal",
        "legacyPracticeLessonId",
        "restoresLessonId",
        "storyIndex",
        "language",
        "image",
        "lessonNumber",
        "kind",
        "curriculumRole",
        "author",
        "pageHint",
        "pdfPage",
        "pageImages",
    }
    result = {key: value for key, value in raw.items() if key in keys}
    if kind in {"story", "reading"}:
        result["sentences"] = [
            {key: value for key, value in sentence.items() if key in {"text", "audio"}}
            for sentence in raw.get("sentences", [])
        ]
    if raw.get("knowledge"):
        allowed = {"point", "core_concept", "key_formula", "common_mistakes", "tips"}
        knowledge = raw["knowledge"]
        result["knowledge"] = {key: value for key, value in knowledge.items() if key in allowed}
        if knowledge.get("audio"):
            result["knowledge"]["audio"] = {
                key: value for key, value in knowledge["audio"].items() if key in allowed
            }
    return result


@dataclass
class ContentBatch:
    containers: dict = field(default_factory=dict)
    revisions: dict = field(default_factory=dict)
    identities: dict = field(default_factory=dict)
    versions: dict = field(default_factory=dict)
    unmapped_files: list = field(default_factory=list)

    def add(self, book, kind, raw, provenance, *, question_source_id=None, extra=None):
        source = check_id(raw.get("id"))
        if raw.get("bookId") != book:
            raise ContentSourceError(f"Book mismatch: {kind}/{book}/{source}")
        cid = container_id(kind, book, source)
        if cid in self.containers:
            raise ContentSourceError(f"Duplicate content identity: {kind}/{book}/{source}")
        seen, refs = set(), []
        for original in raw.get("questions", []):
            try:
                question = PrivateQuestion.model_validate(original).model_dump(exclude_none=True)
            except ValidationError as exc:
                fields = ",".join(
                    ".".join(str(v) for v in e["loc"]) for e in exc.errors(include_input=False)
                )
                raise ContentSourceError(
                    f"Invalid question fields at {kind}/{book}/{source}: {fields}"
                ) from None
            qid = question["id"]
            if qid in seen:
                raise ContentSourceError(f"Duplicate question id: {kind}/{book}/{source}/{qid}")
            seen.add(qid)
            identity_source = question_source_id or source
            uid = question_uid(kind, book, identity_source, qid)
            version = digest({"question": question, "grading_rule_version": GRADING_RULE_VERSION})
            self.identities[uid] = {
                "uid": uid,
                "kind": kind,
                "book_id": book,
                "source_id": identity_source,
                "source_question_id": qid,
            }
            self.versions[uid, version] = {
                "uid": uid,
                "version": version,
                "grading_rule_version": GRADING_RULE_VERSION,
                "private_payload": question,
            }
            refs.append({"uid": uid, "version": version, "source_question_id": qid})
        public = public_metadata(raw, kind)
        if extra:
            public.update(extra)
        revision = digest({"metadata": public, "questions": refs})
        self.containers[cid] = {
            "id": cid,
            "kind": kind,
            "book_id": book,
            "source_id": source,
            "active": True,
            "current_version": revision,
        }
        self.revisions[cid, revision] = {
            "container_id": cid,
            "version": revision,
            "public_payload": public,
            "question_refs": refs,
            "provenance": provenance,
        }

    def summary(self):
        return {
            "containers": len(self.containers),
            "question_identities": len(self.identities),
            "question_versions": len(self.versions),
            "unmapped_files": self.unmapped_files,
        }


def load_content(root: Path) -> ContentBatch:
    index, _ = read_source(root, "apps/web/public/data/index.json")
    review_path = "apps/api/private-content/number-review.json"
    review, review_hash = read_source(root, review_path)
    _, generator_hash = read_source_bytes(root, "packages/core/src/numberSense.ts")
    if review.get("source_hash") != generator_hash or review.get("generator_version") != 1:
        raise ContentSourceError(
            "Stale number-review export; run scripts/cloud/export-number-review.mts"
        )
    banks = {(bank["skill"], bank["variant"]): bank for bank in review["banks"]}
    if len(review["banks"]) != 6 or set(banks) != {
        (s, v) for s in ["count", "compare", "apply"] for v in ["even", "odd"]
    }:
        raise ContentSourceError("Incomplete number-review variants")
    batch = ContentBatch()
    books = set()
    for item in index["books"]:
        book = check_id(item["id"])
        if book in books:
            raise ContentSourceError("Duplicate book identity")
        books.add(book)
        prefix = f"apps/web/public/data/books/{book}"
        outline, _ = read_source(root, f"{prefix}/outline.json")
        if outline.get("bookId") != book:
            raise ContentSourceError(f"Outline book mismatch: {book}")
        ordinary = {check_id(lesson["id"]) for lesson in outline["lessons"]}
        challenges = {
            check_id(unit["examLessonId"]) for unit in outline["units"] if unit.get("examLessonId")
        }
        if len(ordinary) != len(outline["lessons"]) or ordinary.intersection(challenges):
            raise ContentSourceError(f"Duplicate lesson identity: {book}")
        for source in sorted(ordinary | challenges):
            relative = f"{prefix}/lessons/{source}.json"
            raw, source_hash = read_source(root, relative)
            if raw.get("id") != source or not raw.get("questions"):
                raise ContentSourceError(f"Invalid lesson source: {relative}")
            batch.add(
                book,
                "challenge" if source in challenges else "lesson",
                raw,
                {"path": relative, "sha256": source_hash},
            )
        expected = ordinary | challenges
        actual = {p.stem for p in (root / prefix / "lessons").glob("*.json")}
        batch.unmapped_files.extend(f"{prefix}/lessons/{v}.json" for v in sorted(actual - expected))
        for filename, field_name, kind, required in [
            ("stories.json", "stories", "story", item.get("hasStories")),
            ("passages.json", "passages", "reading", item.get("hasPassages")),
        ]:
            relative = f"{prefix}/{filename}"
            if not required and not (root / relative).is_file():
                continue
            raw, source_hash = read_source(root, relative)
            if raw.get("bookId") != book:
                raise ContentSourceError(f"Book mismatch: {relative}")
            for part in raw[field_name]:
                batch.add(book, kind, part, {"path": relative, "sha256": source_hash})
    if "g1up" not in books:
        raise ContentSourceError("Missing source book for number review")
    for (skill, variant), bank in sorted(banks.items()):
        if len(bank["questions"]) != 2:
            raise ContentSourceError("Incomplete number-review bank")
        source = f"number-review-{skill}-{variant}"
        batch.add(
            "g1up",
            "number_review",
            {
                "id": source,
                "bookId": "g1up",
                "title": source,
                "unitNumber": 1,
                "questions": bank["questions"],
            },
            {"path": review_path, "sha256": review_hash, "generator_source_hash": generator_hash},
            question_source_id=f"number-review-{skill}",
            extra={"number_skill": skill, "variant": variant},
        )
    return batch


def read_source_bytes(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ContentSourceError("Source outside content root")
    try:
        data = path.read_bytes()
        return data, hashlib.sha256(data).hexdigest()
    except OSError:
        raise ContentSourceError(f"Missing generator source: {relative}") from None


async def insert_new(db, model, rows):
    rows = list(rows)
    for offset in range(0, len(rows), 250):
        await db.execute(insert(model).values(rows[offset : offset + 250]).on_conflict_do_nothing())


async def import_content(db, root):
    batch = load_content(root)
    # 与其他内容发布串行；所有题目版本和当前发布指针在一次事务内切换。
    from sqlalchemy import text

    await db.execute(text("SELECT pg_advisory_xact_lock(306637002)"))
    from sqlalchemy import update

    await db.execute(update(ContentContainer).values(active=False))
    bare = [{**row, "current_version": None} for row in batch.containers.values()]
    await insert_new(db, ContentContainer, bare)
    await insert_new(db, QuestionIdentity, batch.identities.values())
    await insert_new(db, QuestionVersion, batch.versions.values())
    await insert_new(db, ContentRevision, batch.revisions.values())
    rows = list(batch.containers.values())
    for offset in range(0, len(rows), 250):
        statement = insert(ContentContainer).values(rows[offset : offset + 250])
        await db.execute(
            statement.on_conflict_do_update(
                index_elements=[ContentContainer.id],
                set_={"current_version": statement.excluded.current_version, "active": True},
            )
        )
    await db.commit()
    return batch.summary()


async def main():
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.sessions() as db:
            print(json.dumps(await import_content(db, settings.content_root), ensure_ascii=False))
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
