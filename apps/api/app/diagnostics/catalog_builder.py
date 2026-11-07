"""从教材源数据构建稳定知识点目录、受控跨版关系与题目版本映射。"""

from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.content.import_content import check_id, digest, question_uid, read_source
from app.content.schemas import PrivateQuestion
from app.curriculum.models import Textbook
from app.diagnostics.models import (
    KnowledgePoint,
    KnowledgePointRelation,
    QuestionKnowledgeLink,
)
from app.learning.grading import GRADING_RULE_VERSION

MAPPING_VERSION = "kp-map-v1"

NUMBER_SKILL_TITLES = {
    "count": "数感·点数与认数",
    "compare": "数感·大小比较",
    "apply": "数感·数量应用",
}

NUMBER_SKILL_DESCRIPTIONS = {
    "count": "点数物品、建立数与量的对应关系并准确认数。",
    "compare": "比较两个或多个数量的大小与多少关系。",
    "apply": "在具体情境中运用数量关系解决基础数感问题。",
}


def clean_text(value: str | None, fallback: str, max_len: int = 240) -> str:
    raw = (value or "").replace("\x00", "").strip()
    if not raw:
        raw = fallback.replace("\x00", "").strip()
    return raw[:max_len]


@dataclass
class KnowledgeCatalogBatch:
    knowledge_points: dict[str, dict] = field(default_factory=dict)
    relations: dict[tuple[str, str, str], dict] = field(default_factory=dict)
    question_links: dict[tuple[str, str, str], dict] = field(default_factory=dict)


def _load_edition_supersedes(root: Path) -> dict[str, str]:
    supersedes_map: dict[str, str] = {}
    rel = Path("content/editions/2026/catalog.json")
    full = root / rel
    if full.is_file():
        data, _ = read_source(root, str(rel))
        for b in data.get("books", []):
            if b.get("id") and b.get("legacyId"):
                supersedes_map[b["id"]] = b["legacyId"]
    return supersedes_map


def build_knowledge_catalog(
    root: Path, allowed_books: set[str] | None = None
) -> KnowledgeCatalogBatch:
    index, index_hash = read_source(root, "apps/web/public/data/index.json")
    review_path = "apps/api/private-content/number-review.json"
    review, review_hash = read_source(root, review_path)
    edition_supersedes = _load_edition_supersedes(root)

    batch = KnowledgeCatalogBatch()
    book_lesson_kps: dict[str, dict[str, str]] = {}
    book_unit_title_kps: dict[str, dict[tuple[int, str], list[str]]] = {}
    book_title_kps: dict[str, dict[str, list[str]]] = {}
    book_supersedes: dict[str, str] = {}
    pending_restores: list[tuple[str, str, str, str]] = []

    for item in index.get("books", []):
        book_id = check_id(item["id"])
        if allowed_books is not None and book_id not in allowed_books:
            continue
        subject_code = item.get("subject") or "math"
        sup = item.get("supersedes") or edition_supersedes.get(book_id)
        if isinstance(sup, str) and sup:
            book_supersedes[book_id] = sup

        prefix = f"apps/web/public/data/books/{book_id}"
        outline, outline_hash = read_source(root, f"{prefix}/outline.json")
        unit_titles: dict[int, str] = {}
        challenges: list[tuple[int, str]] = []
        for u in outline.get("units", []):
            u_num = int(u.get("unit_number") or 1)
            unit_titles[u_num] = clean_text(u.get("title"), f"第{u_num}单元", 200)
            if u.get("examLessonId"):
                challenges.append((u_num, check_id(u["examLessonId"])))

        lesson_kps: dict[str, str] = {}
        unit_title_map: dict[tuple[int, str], list[str]] = {}
        title_map: dict[str, list[str]] = {}
        sort_order = 0

        for lesson_meta in outline.get("lessons", []):
            lesson_id = check_id(lesson_meta["id"])
            rel_path = f"{prefix}/lessons/{lesson_id}.json"
            raw, source_hash = read_source(root, rel_path)
            u_num = int(raw.get("unitNumber") or lesson_meta.get("unitNumber") or 1)
            u_title = clean_text(
                raw.get("unitTitle") or unit_titles.get(u_num), f"第{u_num}单元", 200
            )
            unit_titles.setdefault(u_num, u_title)

            knowledge = raw.get("knowledge") or {}
            kp_title = clean_text(
                knowledge.get("point") or raw.get("title") or lesson_meta.get("title"),
                lesson_id,
                240,
            )
            desc_raw = (knowledge.get("core_concept") or "").replace("\x00", "").strip()
            description = desc_raw[:1200] if desc_raw else None

            kp_id = "kp-" + digest(["kp-v1", "lesson", book_id, lesson_id])[:36]
            code = f"lesson:{lesson_id}"
            sort_order += 1

            batch.knowledge_points[kp_id] = {
                "id": kp_id,
                "subject_code": subject_code,
                "book_id": book_id,
                "unit_number": u_num,
                "unit_title": u_title,
                "lesson_id": lesson_id,
                "scope_kind": "lesson",
                "code": code,
                "title": kp_title,
                "description": description,
                "sort_order": sort_order,
                "provenance": {
                    "kind": "lesson",
                    "path": rel_path,
                    "sha256": source_hash,
                    "outline_sha256": outline_hash,
                    "index_sha256": index_hash,
                },
            }
            lesson_kps[lesson_id] = kp_id
            unit_title_map.setdefault((u_num, kp_title), []).append(kp_id)
            title_map.setdefault(kp_title, []).append(kp_id)

            for rel_field in ("restoresLessonId", "legacyPracticeLessonId"):
                target_lesson = raw.get(rel_field)
                if isinstance(target_lesson, str) and target_lesson.strip():
                    pending_restores.append((book_id, lesson_id, target_lesson.strip(), rel_field))

            for original in raw.get("questions", []):
                q = PrivateQuestion.model_validate(original).model_dump(exclude_none=True)
                qid = q["id"]
                uid = question_uid("lesson", book_id, lesson_id, qid)
                q_ver = digest({"question": q, "grading_rule_version": GRADING_RULE_VERSION})
                batch.question_links[uid, q_ver, kp_id] = {
                    "question_uid": uid,
                    "question_version": q_ver,
                    "kp_id": kp_id,
                    "mapping_role": "primary",
                    "mapping_source": "lesson_primary",
                    "mapping_version": MAPPING_VERSION,
                    "provenance": {
                        "book_id": book_id,
                        "source_id": lesson_id,
                        "source_question_id": qid,
                        "question_kp_label": clean_text(q.get("knowledge_point"), kp_title, 240),
                    },
                }

        for u_num_default, challenge_id in sorted(challenges, key=lambda x: (x[0], x[1])):
            rel_path = f"{prefix}/lessons/{challenge_id}.json"
            raw, source_hash = read_source(root, rel_path)
            u_num = int(raw.get("unitNumber") or u_num_default or 1)
            u_title = clean_text(
                raw.get("unitTitle") or unit_titles.get(u_num), f"第{u_num}单元", 200
            )
            for original in raw.get("questions", []):
                q = PrivateQuestion.model_validate(original).model_dump(exclude_none=True)
                qid = q["id"]
                uid = question_uid("challenge", book_id, challenge_id, qid)
                q_ver = digest({"question": q, "grading_rule_version": GRADING_RULE_VERSION})
                q_kp_title = clean_text(
                    q.get("knowledge_point") or raw.get("title"), f"{u_title}综合挑战", 240
                )

                unit_matches = unit_title_map.get((u_num, q_kp_title), [])
                book_matches = title_map.get(q_kp_title, [])
                if unit_matches:
                    target_kp_id = unit_matches[0]
                    mapping_source = "challenge_unit_match"
                elif len(book_matches) == 1:
                    target_kp_id = book_matches[0]
                    mapping_source = "challenge_book_match"
                else:
                    target_kp_id = (
                        "kp-"
                        + digest(["kp-v1", "unit_challenge", book_id, str(u_num), q_kp_title])[:36]
                    )
                    mapping_source = "challenge_unit_topic"
                    if target_kp_id not in batch.knowledge_points:
                        sort_order += 1
                        topic_code_hash = digest(
                            ["kp-v1", "unit_challenge_code", book_id, str(u_num), q_kp_title]
                        )[:16]
                        batch.knowledge_points[target_kp_id] = {
                            "id": target_kp_id,
                            "subject_code": subject_code,
                            "book_id": book_id,
                            "unit_number": u_num,
                            "unit_title": u_title,
                            "lesson_id": challenge_id,
                            "scope_kind": "unit_challenge",
                            "code": f"unit-challenge:{u_num}:{topic_code_hash}",
                            "title": q_kp_title,
                            "description": f"{u_title}单元综合考查：{q_kp_title}",
                            "sort_order": sort_order,
                            "provenance": {
                                "kind": "challenge",
                                "path": rel_path,
                                "sha256": source_hash,
                                "challenge_id": challenge_id,
                            },
                        }

                batch.question_links[uid, q_ver, target_kp_id] = {
                    "question_uid": uid,
                    "question_version": q_ver,
                    "kp_id": target_kp_id,
                    "mapping_role": "primary",
                    "mapping_source": mapping_source,
                    "mapping_version": MAPPING_VERSION,
                    "provenance": {
                        "book_id": book_id,
                        "source_id": challenge_id,
                        "source_question_id": qid,
                        "question_kp_label": q_kp_title,
                    },
                }

        stories_rel = f"{prefix}/stories.json"
        if item.get("hasStories") or (root / stories_rel).is_file():
            if (root / stories_rel).is_file():
                s_raw, s_hash = read_source(root, stories_rel)
                for part in s_raw.get("stories", []):
                    story_id = check_id(part.get("id"))
                    u_num = int(part.get("unitNumber") or 1)
                    u_title = clean_text(
                        part.get("unitTitle") or unit_titles.get(u_num), f"第{u_num}单元", 200
                    )
                    for original in part.get("questions", []):
                        q = PrivateQuestion.model_validate(original).model_dump(exclude_none=True)
                        qid = q["id"]
                        uid = question_uid("story", book_id, story_id, qid)
                        q_ver = digest(
                            {"question": q, "grading_rule_version": GRADING_RULE_VERSION}
                        )
                        skill_label = clean_text(
                            original.get("skill") or q.get("knowledge_point"),
                            "阅读理解综合",
                            120,
                        )
                        display_title = (
                            skill_label
                            if skill_label.startswith("阅读")
                            else f"阅读理解·{skill_label}"
                        )[:240]
                        target_kp_id = (
                            "kp-"
                            + digest(["kp-v1", "story_skill", book_id, str(u_num), skill_label])[
                                :36
                            ]
                        )
                        if target_kp_id not in batch.knowledge_points:
                            sort_order += 1
                            skill_code_hash = digest(
                                ["kp-v1", "story_skill_code", book_id, str(u_num), skill_label]
                            )[:16]
                            story_desc = (
                                f"{u_title}阅读故事理解与文本证据定位（{skill_label}）。"
                            )
                            batch.knowledge_points[target_kp_id] = {
                                "id": target_kp_id,
                                "subject_code": subject_code,
                                "book_id": book_id,
                                "unit_number": u_num,
                                "unit_title": u_title,
                                "lesson_id": story_id,
                                "scope_kind": "story_skill",
                                "code": f"story-skill:{u_num}:{skill_code_hash}",
                                "title": display_title,
                                "description": story_desc,
                                "sort_order": sort_order,
                                "provenance": {
                                    "kind": "story",
                                    "path": stories_rel,
                                    "sha256": s_hash,
                                    "story_id": story_id,
                                    "skill": skill_label,
                                },
                            }
                        batch.question_links[uid, q_ver, target_kp_id] = {
                            "question_uid": uid,
                            "question_version": q_ver,
                            "kp_id": target_kp_id,
                            "mapping_role": "primary",
                            "mapping_source": "story_skill",
                            "mapping_version": MAPPING_VERSION,
                            "provenance": {
                                "book_id": book_id,
                                "source_id": story_id,
                                "source_question_id": qid,
                                "skill": skill_label,
                            },
                        }

        book_lesson_kps[book_id] = lesson_kps
        book_unit_title_kps[book_id] = unit_title_map
        book_title_kps[book_id] = title_map

    if allowed_books is None or "g1up" in allowed_books:
        base_order = sum(
            1 for kp in batch.knowledge_points.values() if kp["book_id"] == "g1up"
        )
        for bank in sorted(
            review.get("banks", []), key=lambda b: (b["skill"], b["variant"])
        ):
            skill = bank["skill"]
            kp_id = "kp-" + digest(["kp-v1", "number_skill", "g1up", skill])[:36]
            if kp_id not in batch.knowledge_points:
                base_order += 1
                batch.knowledge_points[kp_id] = {
                    "id": kp_id,
                    "subject_code": "math",
                    "book_id": "g1up",
                    "unit_number": 1,
                    "unit_title": "第一单元",
                    "lesson_id": f"number-review-{skill}",
                    "scope_kind": "number_skill",
                    "code": f"number-skill:{skill}",
                    "title": NUMBER_SKILL_TITLES.get(skill, f"数感·{skill}"),
                    "description": NUMBER_SKILL_DESCRIPTIONS.get(skill),
                    "sort_order": base_order,
                    "provenance": {
                        "kind": "number_review",
                        "path": review_path,
                        "sha256": review_hash,
                        "skill": skill,
                    },
                }
            identity_source = f"number-review-{skill}"
            for original in bank.get("questions", []):
                q = PrivateQuestion.model_validate(original).model_dump(exclude_none=True)
                qid = q["id"]
                uid = question_uid("number_review", "g1up", identity_source, qid)
                q_ver = digest({"question": q, "grading_rule_version": GRADING_RULE_VERSION})
                batch.question_links[uid, q_ver, kp_id] = {
                    "question_uid": uid,
                    "question_version": q_ver,
                    "kp_id": kp_id,
                    "mapping_role": "primary",
                    "mapping_source": "number_skill",
                    "mapping_version": MAPPING_VERSION,
                    "provenance": {
                        "book_id": "g1up",
                        "source_id": identity_source,
                        "variant": bank["variant"],
                        "source_question_id": qid,
                        "skill": skill,
                    },
                }

    for book_id, src_lesson, dst_lesson, field_name in pending_restores:
        lesson_map = book_lesson_kps.get(book_id, {})
        src_kp = lesson_map.get(src_lesson)
        dst_kp = lesson_map.get(dst_lesson)
        if src_kp and dst_kp and src_kp != dst_kp:
            rel_key = (src_kp, dst_kp, "restores_lesson")
            batch.relations[rel_key] = {
                "source_kp_id": src_kp,
                "target_kp_id": dst_kp,
                "relation_kind": "restores_lesson",
                "provenance": {
                    "book_id": book_id,
                    "source_lesson_id": src_lesson,
                    "target_lesson_id": dst_lesson,
                    "field": field_name,
                },
            }

    for new_book, old_book in sorted(book_supersedes.items()):
        if new_book not in book_lesson_kps or old_book not in book_lesson_kps:
            continue
        old_unit_map = book_unit_title_kps[old_book]
        old_title_map = book_title_kps[old_book]
        for kp_id in book_lesson_kps[new_book].values():
            kp = batch.knowledge_points[kp_id]
            title = kp["title"]
            u_num = kp["unit_number"]
            candidates = old_unit_map.get((u_num, title), [])
            match_scope = "same_unit_exact_title"
            if len(candidates) != 1:
                candidates = old_title_map.get(title, [])
                match_scope = "book_unique_exact_title"
            if len(candidates) == 1:
                target_kp_id = candidates[0]
                rel_key = (kp_id, target_kp_id, "supersedes_exact_title")
                batch.relations[rel_key] = {
                    "source_kp_id": kp_id,
                    "target_kp_id": target_kp_id,
                    "relation_kind": "supersedes_exact_title",
                    "provenance": {
                        "source_book_id": new_book,
                        "target_book_id": old_book,
                        "title": title,
                        "match_scope": match_scope,
                    },
                }

    return batch


async def sync_knowledge_catalog(db, root: Path) -> dict:
    existing_books = set((await db.scalars(
         Textbook.__table__.select().with_only_columns(Textbook.id)
    )).all())
    if not existing_books:
        return {"knowledge_points": 0, "relations": 0, "question_links": 0}
    batch = build_knowledge_catalog(root, allowed_books=existing_books)

    kp_rows = list(batch.knowledge_points.values())
    for offset in range(0, len(kp_rows), 250):
        stmt = insert(KnowledgePoint).values(kp_rows[offset : offset + 250])
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[KnowledgePoint.id],
                set_={
                    "subject_code": stmt.excluded.subject_code,
                    "book_id": stmt.excluded.book_id,
                    "unit_number": stmt.excluded.unit_number,
                    "unit_title": stmt.excluded.unit_title,
                    "lesson_id": stmt.excluded.lesson_id,
                    "scope_kind": stmt.excluded.scope_kind,
                    "code": stmt.excluded.code,
                    "title": stmt.excluded.title,
                    "description": stmt.excluded.description,
                    "sort_order": stmt.excluded.sort_order,
                    "provenance": stmt.excluded.provenance,
                },
            )
        )

    rel_rows = list(batch.relations.values())
    for offset in range(0, len(rel_rows), 250):
        stmt = insert(KnowledgePointRelation).values(rel_rows[offset : offset + 250])
        await db.execute(stmt.on_conflict_do_nothing())

    link_rows = list(batch.question_links.values())
    for offset in range(0, len(link_rows), 250):
        stmt = insert(QuestionKnowledgeLink).values(link_rows[offset : offset + 250])
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    QuestionKnowledgeLink.question_uid,
                    QuestionKnowledgeLink.question_version,
                    QuestionKnowledgeLink.kp_id,
                ],
                set_={
                    "mapping_role": stmt.excluded.mapping_role,
                    "mapping_source": stmt.excluded.mapping_source,
                    "mapping_version": stmt.excluded.mapping_version,
                    "provenance": stmt.excluded.provenance,
                },
            )
        )

    return {
        "knowledge_points": len(kp_rows),
        "relations": len(rel_rows),
        "question_links": len(link_rows),
    }
