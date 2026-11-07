"""知识点目录查询、学生掌握度诊断聚合与家庭导出快照服务。"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.models import QuestionVersion
from app.curriculum.models import StudentSubject, Subject, Textbook, TextbookSelection
from app.diagnostics.catalog_builder import MAPPING_VERSION, clean_text
from app.diagnostics.engine import (
    DIAGNOSTIC_RULE_VERSION,
    AttemptEvidence,
    evaluate_knowledge_point,
    resolve_zone,
    study_day_of,
)
from app.diagnostics.models import (
    KnowledgePoint,
    KnowledgePointRelation,
    QuestionKnowledgeLink,
)
from app.errors import APIError
from app.families.models import Family
from app.learning.models import Attempt, LearningSession
from app.portability.models import LegacyImport
from app.students.models import Student

SUBJECT_SORT_ORDER = {"math": 0, "chinese": 1, "english": 2, "science": 3}


def _subject_rank(code: str) -> tuple[int, str]:
    return (SUBJECT_SORT_ORDER.get(code, 99), code)


async def get_textbook_knowledge_catalog(db: AsyncSession, book_id: str) -> dict:
    book = await db.get(Textbook, book_id)
    if book is None:
        raise APIError(404, "TEXTBOOK_NOT_FOUND", "找不到指定教材")

    kps = (
        await db.scalars(
            select(KnowledgePoint)
            .where(KnowledgePoint.book_id == book_id)
            .order_by(
                KnowledgePoint.unit_number,
                KnowledgePoint.sort_order,
                KnowledgePoint.id,
            )
        )
    ).all()
    kp_ids = [kp.id for kp in kps]
    q_counts: dict[str, set[str]] = defaultdict(set)
    related_map: dict[str, list[dict]] = defaultdict(list)

    if kp_ids:
        link_rows = (
            await db.execute(
                select(
                    QuestionKnowledgeLink.kp_id,
                    QuestionKnowledgeLink.question_uid,
                ).where(QuestionKnowledgeLink.kp_id.in_(kp_ids))
            )
        ).all()
        for kp_id, q_uid in link_rows:
            q_counts[kp_id].add(q_uid)

        rel_rows = (
            await db.execute(
                select(KnowledgePointRelation, KnowledgePoint)
                .join(
                    KnowledgePoint,
                    KnowledgePoint.id == KnowledgePointRelation.target_kp_id,
                )
                .where(KnowledgePointRelation.source_kp_id.in_(kp_ids))
            )
        ).all()
        for rel, target_kp in rel_rows:
            related_map[rel.source_kp_id].append(
                {
                    "kp_id": target_kp.id,
                    "book_id": target_kp.book_id,
                    "lesson_id": target_kp.lesson_id,
                    "title": target_kp.title,
                    "relation_kind": rel.relation_kind,
                    "status": None,
                    "status_label": None,
                }
            )

    units_dict: dict[int, dict] = {}
    for kp in kps:
        unit_group = units_dict.setdefault(
            kp.unit_number,
            {
                "unit_number": kp.unit_number,
                "unit_title": kp.unit_title,
                "knowledge_points": [],
            },
        )
        unit_group["knowledge_points"].append(
            {
                "id": kp.id,
                "code": kp.code,
                "scope_kind": kp.scope_kind,
                "unit_number": kp.unit_number,
                "unit_title": kp.unit_title,
                "lesson_id": kp.lesson_id,
                "title": kp.title,
                "description": kp.description,
                "sort_order": kp.sort_order,
                "total_questions_available": len(q_counts.get(kp.id, set())),
                "related_points": related_map.get(kp.id, []),
            }
        )

    return {
        "book_id": book.id,
        "subject_code": book.subject_code,
        "title": book.title,
        "grade": book.grade,
        "semester": book.semester,
        "school_system": book.school_system,
        "edition_label": book.edition_label,
        "publisher_label": book.publisher_label,
        "mapping_version": MAPPING_VERSION,
        "total_knowledge_points": len(kps),
        "units": [units_dict[u] for u in sorted(units_dict)],
    }


async def _student_book_context(db: AsyncSession, student: Student):
    subjects_all = (await db.scalars(select(Subject))).all()
    subject_names = {s.code: s.name for s in subjects_all}

    student_subjects = (
        await db.scalars(
            select(StudentSubject).where(StudentSubject.student_id == student.id)
        )
    ).all()
    enabled_map = {s.subject_code: s.enabled for s in student_subjects}

    selections = (
        await db.scalars(
            select(TextbookSelection)
            .where(TextbookSelection.student_id == student.id)
            .order_by(
                TextbookSelection.ended_at.is_not(None),
                TextbookSelection.started_at.desc(),
                TextbookSelection.id,
            )
        )
    ).all()

    practiced_books = set(
        (
            await db.scalars(
                select(LearningSession.book_id)
                .where(
                    LearningSession.student_id == student.id,
                    LearningSession.book_id.is_not(None),
                )
                .distinct()
            )
        ).all()
    )

    book_ids = list(
        dict.fromkeys([*(s.book_id for s in selections), *sorted(practiced_books)])
    )
    books_by_id: dict[str, Textbook] = {}
    if book_ids:
        rows = (
            await db.scalars(select(Textbook).where(Textbook.id.in_(book_ids)))
        ).all()
        books_by_id = {b.id: b for b in rows}

    active_by_subject: dict[str, TextbookSelection] = {}
    for sel in selections:
        if sel.ended_at is None and sel.subject_code not in active_by_subject:
            active_by_subject[sel.subject_code] = sel

    all_subject_codes = sorted(
        set(subject_names) | set(enabled_map) | {b.subject_code for b in books_by_id.values()},
        key=_subject_rank,
    )
    subject_options = [
        {
            "subject_code": code,
            "subject_name": subject_names.get(code, code),
            "enabled": bool(enabled_map.get(code, False)),
            "active_book_id": active_by_subject[code].book_id
            if code in active_by_subject
            else None,
        }
        for code in all_subject_codes
    ]

    seen_books: set[str] = set()
    available_books: list[dict] = []
    for sel in selections:
        if sel.book_id in seen_books or sel.book_id not in books_by_id:
            continue
        seen_books.add(sel.book_id)
        book = books_by_id[sel.book_id]
        is_current = (
            sel.ended_at is None
            and active_by_subject.get(book.subject_code) is not None
            and active_by_subject[book.subject_code].book_id == book.id
        )
        available_books.append(
            {
                "book_id": book.id,
                "subject_code": book.subject_code,
                "subject_name": subject_names.get(book.subject_code, book.subject_code),
                "title": book.title,
                "grade": book.grade,
                "semester": book.semester,
                "school_system": book.school_system,
                "edition_label": book.edition_label,
                "publisher_label": book.publisher_label,
                "is_current": is_current,
                "current_unit_number": sel.current_unit_number if is_current else None,
            }
        )
    for b_id in sorted(practiced_books):
        if b_id in seen_books or b_id not in books_by_id:
            continue
        seen_books.add(b_id)
        book = books_by_id[b_id]
        available_books.append(
            {
                "book_id": book.id,
                "subject_code": book.subject_code,
                "subject_name": subject_names.get(book.subject_code, book.subject_code),
                "title": book.title,
                "grade": book.grade,
                "semester": book.semester,
                "school_system": book.school_system,
                "edition_label": book.edition_label,
                "publisher_label": book.publisher_label,
                "is_current": False,
                "current_unit_number": None,
            }
        )

    available_books.sort(
        key=lambda item: (
            0 if item["is_current"] else 1,
            _subject_rank(item["subject_code"]),
            item["book_id"],
        )
    )
    return subject_names, subject_options, available_books


async def _evaluate_book_for_student(
    db: AsyncSession,
    student: Student,
    book_id: str,
    timezone: str,
) -> tuple[list[dict], list[dict], dict]:
    kps = (
        await db.scalars(
            select(KnowledgePoint)
            .where(KnowledgePoint.book_id == book_id)
            .order_by(
                KnowledgePoint.unit_number,
                KnowledgePoint.sort_order,
                KnowledgePoint.id,
            )
        )
    ).all()
    kp_ids = [kp.id for kp in kps]
    q_uids_by_kp: dict[str, set[str]] = defaultdict(set)
    kps_by_qver: dict[tuple[str, str], list[str]] = defaultdict(list)

    if kp_ids:
        links = (
            await db.scalars(
                select(QuestionKnowledgeLink).where(
                    QuestionKnowledgeLink.kp_id.in_(kp_ids)
                )
            )
        ).all()
        for link in links:
            q_uids_by_kp[link.kp_id].add(link.question_uid)
            kps_by_qver[link.question_uid, link.question_version].append(link.kp_id)

    attempts_by_kp: dict[str, list[AttemptEvidence]] = defaultdict(list)
    if kp_ids:
        attempt_rows = (
            await db.execute(
                select(Attempt, LearningSession.kind, QuestionKnowledgeLink.kp_id)
                .join(
                    LearningSession,
                    (LearningSession.id == Attempt.session_id)
                    & (LearningSession.student_id == Attempt.student_id),
                )
                .join(
                    QuestionKnowledgeLink,
                    (QuestionKnowledgeLink.question_uid == Attempt.question_uid)
                    & (QuestionKnowledgeLink.question_version == Attempt.question_version),
                )
                .where(
                    Attempt.student_id == student.id,
                    QuestionKnowledgeLink.kp_id.in_(kp_ids),
                )
            )
        ).all()
        for att, session_kind, kp_id in attempt_rows:
            ev = att.evidence or {}
            attempts_by_kp[kp_id].append(
                AttemptEvidence(
                    attempt_id=str(att.id),
                    session_id=str(att.session_id),
                    session_kind=session_kind,
                    ordinal=att.ordinal,
                    question_uid=att.question_uid,
                    question_version=att.question_version,
                    correct=bool(att.correct),
                    first_attempt=bool(att.first_attempt),
                    hint_level=int(ev.get("hint_level") or 0),
                    received_at=att.received_at,
                    client_at=att.client_at,
                    declared_duration_ms=att.declared_duration_ms,
                )
            )

    related_map: dict[str, list[dict]] = defaultdict(list)
    if kp_ids:
        rel_rows = (
            await db.execute(
                select(KnowledgePointRelation, KnowledgePoint)
                .join(
                    KnowledgePoint,
                    KnowledgePoint.id == KnowledgePointRelation.target_kp_id,
                )
                .where(KnowledgePointRelation.source_kp_id.in_(kp_ids))
            )
        ).all()
        for rel, target_kp in rel_rows:
            related_map[rel.source_kp_id].append(
                {
                    "kp_id": target_kp.id,
                    "book_id": target_kp.book_id,
                    "lesson_id": target_kp.lesson_id,
                    "title": target_kp.title,
                    "relation_kind": rel.relation_kind,
                    "status": None,
                    "status_label": None,
                }
            )

    units_dict: dict[int, dict] = {}
    all_items: list[dict] = []
    status_totals = {
        "mastered": 0,
        "developing": 0,
        "needs_review": 0,
        "insufficient_evidence": 0,
        "unassessed": 0,
    }
    total_attempts_sum = 0

    for kp in kps:
        diag = evaluate_knowledge_point(
            attempts_by_kp.get(kp.id, []),
            total_questions_available=len(q_uids_by_kp.get(kp.id, set())),
            timezone=timezone,
        )
        status = diag["status"]
        status_totals[status] += 1
        total_attempts_sum += diag["total_attempts"]
        item = {
            "id": kp.id,
            "code": kp.code,
            "scope_kind": kp.scope_kind,
            "unit_number": kp.unit_number,
            "unit_title": kp.unit_title,
            "lesson_id": kp.lesson_id,
            "title": kp.title,
            "description": kp.description,
            "sort_order": kp.sort_order,
            **diag,
            "related_points": related_map.get(kp.id, []),
        }
        all_items.append(item)
        unit_group = units_dict.setdefault(
            kp.unit_number,
            {
                "unit_number": kp.unit_number,
                "unit_title": kp.unit_title,
                "counts": {
                    "mastered": 0,
                    "developing": 0,
                    "needs_review": 0,
                    "insufficient_evidence": 0,
                    "unassessed": 0,
                },
                "knowledge_points": [],
            },
        )
        unit_group["counts"][status] += 1
        unit_group["knowledge_points"].append(item)

    priority_review = [
        item
        for item in all_items
        if item["status"] in ("needs_review", "developing")
    ]
    priority_review.sort(
        key=lambda x: (
            0 if x["status"] == "needs_review" else 1,
            x["unassisted_first_accuracy"]
            if x["unassisted_first_accuracy"] is not None
            else 1.0,
            x["unit_number"],
            x["sort_order"],
        )
    )

    units = [units_dict[u] for u in sorted(units_dict)]
    totals = {
        **status_totals,
        "total_attempts": total_attempts_sum,
        "total_kps": len(kps),
    }
    return units, priority_review, totals


async def get_student_diagnostics(
    db: AsyncSession,
    student: Student,
    *,
    subject_code: str | None = None,
    book_id: str | None = None,
) -> dict:
    family = await db.get(Family, student.family_id)
    timezone = family.timezone if family else "Asia/Shanghai"
    subject_names, subject_options, available_books = await _student_book_context(
        db, student
    )

    legacy_rows = (
        await db.scalars(
            select(LegacyImport.id).where(
                LegacyImport.student_id == student.id,
                LegacyImport.confirmed_at.is_not(None),
            )
        )
    ).all()
    legacy_count = len(legacy_rows)
    legacy_note = (
        "已导入的旧本地档案仅含完成摘要，不计入云端逐题诊断证据。"
        if legacy_count > 0
        else "诊断仅依据云端权威逐题作答计算；经验值、通关标记与纯听读完成不计入掌握度。"
    )

    selected_book_option: dict | None = None
    resolved_subject = subject_code

    if book_id is not None:
        book = await db.get(Textbook, book_id)
        if book is None:
            raise APIError(404, "TEXTBOOK_NOT_FOUND", "找不到指定教材")
        if subject_code is not None and book.subject_code != subject_code:
            raise APIError(422, "TEXTBOOK_SUBJECT_MISMATCH", "教材与所选学科不匹配")
        resolved_subject = book.subject_code
        existing_opt = next(
            (b for b in available_books if b["book_id"] == book.id), None
        )
        selected_book_option = existing_opt or {
            "book_id": book.id,
            "subject_code": book.subject_code,
            "subject_name": subject_names.get(book.subject_code, book.subject_code),
            "title": book.title,
            "grade": book.grade,
            "semester": book.semester,
            "school_system": book.school_system,
            "edition_label": book.edition_label,
            "publisher_label": book.publisher_label,
            "is_current": False,
            "current_unit_number": None,
        }
    elif subject_code is not None:
        if subject_code not in subject_names:
            raise APIError(422, "SUBJECT_NOT_FOUND", "学科不在目录中")
        candidates = [
            b for b in available_books if b["subject_code"] == subject_code
        ]
        selected_book_option = candidates[0] if candidates else None
    else:
        enabled_Current = [
            b
            for b in available_books
            if b["is_current"]
            and any(
                s["subject_code"] == b["subject_code"] and s["enabled"]
                for s in subject_options
            )
        ]
        if enabled_Current:
            selected_book_option = enabled_Current[0]
        elif available_books:
            selected_book_option = available_books[0]
        if selected_book_option:
            resolved_subject = selected_book_option["subject_code"]
        elif subject_options:
            enabled_subj = next(
                (s["subject_code"] for s in subject_options if s["enabled"]),
                subject_options[0]["subject_code"],
            )
            resolved_subject = enabled_subj

    if selected_book_option is None:
        return {
            "student_id": student.id,
            "timezone": timezone,
            "diagnostic_rule_version": DIAGNOSTIC_RULE_VERSION,
            "mapping_version": MAPPING_VERSION,
            "selected_subject_code": resolved_subject,
            "selected_book": None,
            "subjects": subject_options,
            "available_books": available_books,
            "summary": {
                "total_knowledge_points": 0,
                "assessed_count": 0,
                "mastered_count": 0,
                "developing_count": 0,
                "needs_review_count": 0,
                "insufficient_evidence_count": 0,
                "unassessed_count": 0,
                "total_attempts": 0,
                "legacy_imports_count": legacy_count,
                "legacy_exclusion_note": legacy_note,
            },
            "priority_review": [],
            "units": [],
        }

    units, priority_review, stats = await _evaluate_book_for_student(
        db, student, selected_book_option["book_id"], timezone
    )
    total_kps = stats["total_kps"]
    unassessed = stats["unassessed"]
    return {
        "student_id": student.id,
        "timezone": timezone,
        "diagnostic_rule_version": DIAGNOSTIC_RULE_VERSION,
        "mapping_version": MAPPING_VERSION,
        "selected_subject_code": resolved_subject,
        "selected_book": selected_book_option,
        "subjects": subject_options,
        "available_books": available_books,
        "summary": {
            "total_knowledge_points": total_kps,
            "assessed_count": total_kps - unassessed,
            "mastered_count": stats["mastered"],
            "developing_count": stats["developing"],
            "needs_review_count": stats["needs_review"],
            "insufficient_evidence_count": stats["insufficient_evidence"],
            "unassessed_count": unassessed,
            "total_attempts": stats["total_attempts"],
            "legacy_imports_count": legacy_count,
            "legacy_exclusion_note": legacy_note,
        },
        "priority_review": priority_review,
        "units": units,
    }


async def get_knowledge_point_detail(
    db: AsyncSession,
    student: Student,
    kp_id: str,
) -> dict:
    kp = await db.get(KnowledgePoint, kp_id)
    if kp is None:
        raise APIError(404, "KNOWLEDGE_POINT_NOT_FOUND", "找不到指定知识点")

    family = await db.get(Family, student.family_id)
    timezone = family.timezone if family else "Asia/Shanghai"
    zone = resolve_zone(timezone)

    q_uids = set(
        (
            await db.scalars(
                select(QuestionKnowledgeLink.question_uid).where(
                    QuestionKnowledgeLink.kp_id == kp_id
                )
            )
        ).all()
    )

    rows = (
        await db.execute(
            select(Attempt, LearningSession.kind, QuestionVersion.private_payload)
            .join(
                LearningSession,
                (LearningSession.id == Attempt.session_id)
                & (LearningSession.student_id == Attempt.student_id),
            )
            .join(
                QuestionKnowledgeLink,
                (QuestionKnowledgeLink.question_uid == Attempt.question_uid)
                & (QuestionKnowledgeLink.question_version == Attempt.question_version),
            )
            .join(
                QuestionVersion,
                (QuestionVersion.uid == Attempt.question_uid)
                & (QuestionVersion.version == Attempt.question_version),
            )
            .where(
                Attempt.student_id == student.id,
                QuestionKnowledgeLink.kp_id == kp_id,
            )
            .order_by(Attempt.received_at, Attempt.ordinal)
        )
    ).all()

    evidences: list[AttemptEvidence] = []
    recent_items: list[dict] = []
    for att, session_kind, private_payload in rows:
        ev = att.evidence or {}
        hint_level = int(ev.get("hint_level") or 0)
        evidences.append(
            AttemptEvidence(
                attempt_id=str(att.id),
                session_id=str(att.session_id),
                session_kind=session_kind,
                ordinal=att.ordinal,
                question_uid=att.question_uid,
                question_version=att.question_version,
                correct=bool(att.correct),
                first_attempt=bool(att.first_attempt),
                hint_level=hint_level,
                received_at=att.received_at,
                client_at=att.client_at,
                declared_duration_ms=att.declared_duration_ms,
            )
        )
        recent_items.append(
            {
                "attempt_id": str(att.id),
                "session_id": str(att.session_id),
                "session_kind": session_kind,
                "question_uid": att.question_uid,
                "question_version": att.question_version,
                "question_type": str((private_payload or {}).get("type") or "choice"),
                "question_stem": clean_text(
                    (private_payload or {}).get("question"), "练习题", 200
                ),
                "correct": bool(att.correct),
                "first_attempt": bool(att.first_attempt),
                "hint_level": hint_level,
                "study_day": study_day_of(att.received_at, zone),
                "received_at": att.received_at.isoformat(),
                "declared_duration_ms": att.declared_duration_ms,
            }
        )

    diag = evaluate_knowledge_point(
        evidences,
        total_questions_available=len(q_uids),
        timezone=timezone,
    )

    rel_rows = (
        await db.execute(
            select(KnowledgePointRelation, KnowledgePoint)
            .join(
                KnowledgePoint,
                KnowledgePoint.id == KnowledgePointRelation.target_kp_id,
            )
            .where(KnowledgePointRelation.source_kp_id == kp_id)
        )
    ).all()
    related_points: list[dict] = []
    for rel, target_kp in rel_rows:
        target_q_uids = set(
            (
                await db.scalars(
                    select(QuestionKnowledgeLink.question_uid).where(
                        QuestionKnowledgeLink.kp_id == target_kp.id
                    )
                )
            ).all()
        )
        target_att_rows = (
            await db.execute(
                select(Attempt, LearningSession.kind)
                .join(
                    LearningSession,
                    (LearningSession.id == Attempt.session_id)
                    & (LearningSession.student_id == Attempt.student_id),
                )
                .join(
                    QuestionKnowledgeLink,
                    (QuestionKnowledgeLink.question_uid == Attempt.question_uid)
                    & (QuestionKnowledgeLink.question_version == Attempt.question_version),
                )
                .where(
                    Attempt.student_id == student.id,
                    QuestionKnowledgeLink.kp_id == target_kp.id,
                )
            )
        ).all()
        target_ev = [
            AttemptEvidence(
                attempt_id=str(a.id),
                session_id=str(a.session_id),
                session_kind=sk,
                ordinal=a.ordinal,
                question_uid=a.question_uid,
                question_version=a.question_version,
                correct=bool(a.correct),
                first_attempt=bool(a.first_attempt),
                hint_level=int((a.evidence or {}).get("hint_level") or 0),
                received_at=a.received_at,
                client_at=a.client_at,
                declared_duration_ms=a.declared_duration_ms,
            )
            for a, sk in target_att_rows
        ]
        target_diag = evaluate_knowledge_point(
            target_ev,
            total_questions_available=len(target_q_uids),
            timezone=timezone,
        )
        related_points.append(
            {
                "kp_id": target_kp.id,
                "book_id": target_kp.book_id,
                "lesson_id": target_kp.lesson_id,
                "title": target_kp.title,
                "relation_kind": rel.relation_kind,
                "status": target_diag["status"],
                "status_label": target_diag["status_label"],
            }
        )

    kp_item = {
        "id": kp.id,
        "code": kp.code,
        "scope_kind": kp.scope_kind,
        "unit_number": kp.unit_number,
        "unit_title": kp.unit_title,
        "lesson_id": kp.lesson_id,
        "title": kp.title,
        "description": kp.description,
        "sort_order": kp.sort_order,
        **diag,
        "related_points": related_points,
    }
    return {
        "student_id": student.id,
        "timezone": timezone,
        "diagnostic_rule_version": DIAGNOSTIC_RULE_VERSION,
        "mapping_version": MAPPING_VERSION,
        "book_id": kp.book_id,
        "subject_code": kp.subject_code,
        "knowledge_point": kp_item,
        "recent_attempts": list(reversed(recent_items[-20:])),
    }


async def export_family_diagnostics(
    db: AsyncSession, family: Family, students: list[Student]
) -> dict:
    timezone = family.timezone if family else "Asia/Shanghai"
    student_snapshots = []
    for student in students:
        _, _, available_books = await _student_book_context(db, student)
        legacy_rows = (
            await db.scalars(
                select(LegacyImport.id).where(
                    LegacyImport.student_id == student.id,
                    LegacyImport.confirmed_at.is_not(None),
                )
            )
        ).all()
        books_export = []
        for b_opt in available_books:
            units, priority_review, stats = await _evaluate_book_for_student(
                db, student, b_opt["book_id"], timezone
            )
            total_kps = stats["total_kps"]
            unassessed = stats["unassessed"]
            books_export.append(
                {
                    "book_id": b_opt["book_id"],
                    "subject_code": b_opt["subject_code"],
                    "title": b_opt["title"],
                    "is_current": b_opt["is_current"],
                    "summary": {
                        "total_knowledge_points": total_kps,
                        "assessed_count": total_kps - unassessed,
                        "mastered_count": stats["mastered"],
                        "developing_count": stats["developing"],
                        "needs_review_count": stats["needs_review"],
                        "insufficient_evidence_count": stats["insufficient_evidence"],
                        "unassessed_count": unassessed,
                        "total_attempts": stats["total_attempts"],
                    },
                    "priority_review_kp_ids": [p["id"] for p in priority_review],
                    "knowledge_points": [
                        kp
                        for u in units
                        for kp in u["knowledge_points"]
                        if kp["status"] != "unassessed"
                    ],
                }
            )
        student_snapshots.append(
            {
                "student_id": str(student.id),
                "legacy_imports_excluded": len(legacy_rows),
                "books": books_export,
            }
        )
    return {
        "diagnostic_rule_version": DIAGNOSTIC_RULE_VERSION,
        "mapping_version": MAPPING_VERSION,
        "evidence_policy": (
            "authoritative_attempts_only_excluding_xp_completion_and_legacy_summaries"
        ),
        "students": student_snapshots,
    }
