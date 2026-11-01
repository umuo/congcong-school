"""从已有索引及版次核对文件导入目录，不修改教材源文件。"""

import asyncio
import hashlib
import importlib.util
import json
import re
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.curriculum.models import Subject, Textbook
from app.database import Database


def load_catalog(root: Path):
    def read(relative):
        return json.loads((root / relative).read_text(encoding="utf-8"))

    config_path = root / "scripts/quiz/subjects.py"
    spec = importlib.util.spec_from_file_location("curriculum_source_subjects", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = module.SUBJECTS
    subjects = [{"code": code, "name": value["display_name"]} for code, value in config.items()]
    editions = {}
    for relative in [
        "content/editions/2026/catalog.json",
        "content/editions/five-four/catalog.json",
    ]:
        for book in read(relative)["books"]:
            editions[book["id"]] = (book, relative)
    review_path = "docs/five-four-2026-10-27/source-review.json"
    reviews = {b["id"]: b for b in read(review_path)["books"]}
    index_path = "apps/web/public/data/index.json"
    index = read(index_path)
    index_hash = hashlib.sha256((root / index_path).read_bytes()).hexdigest()
    textbooks = []
    for book in index["books"]:
        book_id = book["id"]
        if not re.fullmatch(r"[a-z0-9-]{1,120}", book_id):
            raise ValueError("教材 ID 非法")
        subject = book.get("subject", "math")
        if subject not in config:
            raise ValueError(f"学科 {subject} 尚未在源目录配置")
        outline = read(f"apps/web/public/data/books/{book_id}/outline.json")
        edition, edition_path = editions.get(book_id, ({}, None))
        review = reviews.get(book_id, {})
        source_edition = (
            book.get("sourceEdition") or edition.get("sourceEdition") or review.get("edition")
        )
        year = re.match(r"^(\d{4})年", source_edition or "")
        units = [
            {
                "number": unit["unit_number"],
                "title": unit["title"],
                "label": unit.get("label"),
                "lessons": [
                    {"id": lesson["id"], "title": lesson["title"]}
                    for lesson in outline["lessons"]
                    if lesson["unitNumber"] == unit["unit_number"]
                ],
            }
            for unit in outline["units"]
        ]
        values = {
            "id": book_id,
            "subject_code": subject,
            "title": book["fullName"],
            "grade": book["grade"],
            "school_stage": "primary",
            "school_system": book.get("schoolSystem", "6-3"),
            "semester": book["semester"],
            "publisher_label": book.get("publisherLabel")
            or edition.get("publisherLabel")
            or config[subject].get("publisher_label"),
            "publisher": review.get("publisher"),
            "edition_label": book.get("editionLabel") or edition.get("editionLabel"),
            "source_edition": source_edition,
            "source_printing": book.get("sourcePrinting")
            or edition.get("sourcePrinting")
            or review.get("printing"),
            "publication_year": int(year[1]) if year else None,
            "isbn": review.get("isbn"),
            "supersedes": book.get("supersedes") or edition.get("legacyId"),
            "superseded_by": book.get("supersededBy"),
            "units": units,
        }
        revision = hashlib.sha256(
            json.dumps(values, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        values.update(
            content_revision=revision,
            provenance={
                "index": index_path,
                "index_sha256": index_hash,
                "subject_config": "scripts/quiz/subjects.py",
                "edition_catalog": edition_path,
                "source_review": review_path if review else None,
                "review_kind": review.get("reviewKind"),
            },
        )
        textbooks.append(values)
    if len({b["id"] for b in textbooks}) != len(textbooks):
        raise ValueError("教材 ID 重复")
    return subjects, textbooks


async def import_catalog(db, root: Path):
    subjects, textbooks = load_catalog(root)
    statement = insert(Subject).values(subjects)
    await db.execute(
        statement.on_conflict_do_update(
            index_elements=[Subject.code], set_={"name": statement.excluded.name}
        )
    )
    statement = insert(Textbook).values(textbooks)
    await db.execute(
        statement.on_conflict_do_update(
            index_elements=[Textbook.id],
            set_={key: getattr(statement.excluded, key) for key in textbooks[0] if key != "id"},
        )
    )
    await db.commit()
    return {"subjects": len(subjects), "textbooks": len(textbooks)}


async def main():
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.sessions() as db:
            print(await import_catalog(db, settings.content_root))
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
