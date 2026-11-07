from uuid import uuid4

from sqlalchemy import select

from app.content.models import ContentRevision
from app.content.schemas import public_question
from app.content.service import content_revision, fixed_question, jump_pool
from app.curriculum.models import StudentSubject, Textbook, TextbookSelection
from app.errors import APIError
from app.learning.economy_service import (
    check_hearts,
    check_number_due,
    clock,
    record_attempt_effects,
)
from app.learning.grading import GRADING_RULE_VERSION, grade_answer, matching
from app.learning.input_support import keyboard
from app.learning.models import (
    Attempt,
    LearningCursor,
    LearningSession,
    RewardLedger,
)
from app.learning.review import due_review_refs
from app.learning.sampling import sample_jump
from app.learning.schemas import SessionView
from app.learning.transactions import append_event, receipt, save_receipt
from app.students.service import authorized_student


async def learning_student(db, who, student_id):
    if who.auth_session.mode != "child":
        raise APIError(403, "LEARNING_MODE_REQUIRED", "请先进入学生学习模式")
    return await authorized_student(db, who, student_id, for_learning=True, lock=True)


async def ensure_book(db, student, book_id):
    selected = await db.scalar(
        select(TextbookSelection.id)
        .join(
            StudentSubject,
            (StudentSubject.student_id == TextbookSelection.student_id)
            & (StudentSubject.subject_code == TextbookSelection.subject_code),
        )
        .where(
            TextbookSelection.student_id == student.id,
            TextbookSelection.book_id == book_id,
            TextbookSelection.ended_at.is_(None),
            StudentSubject.enabled.is_(True),
        )
    )
    if selected is None:
        raise APIError(409, "BOOK_NOT_SELECTED", "请由家长启用并选择这本教材")


async def view(db, row, student):
    cp = row.checkpoint
    current = cp["pending"][0] if cp["pending"] else None
    question = feedback = None
    if current is not None:
        ref = row.question_refs[current]
        version = await fixed_question(db, ref["uid"], ref["version"])
        question = public_question(version.private_payload, uid=ref["uid"], version=ref["version"])
        if question["type"] == "fill_blank_text":
            question["input_keyboard"] = keyboard(version.private_payload)
        if question.get("numberTask"):
            level = cp.get("hint_levels", {}).get(str(current), 0)
            question["numberTask"]["hints"] = version.private_payload["numberTask"]["hints"][:level]
            question["numberTask"]["hint_count"] = len(
                version.private_payload["numberTask"]["hints"]
            )
    if cp.get("feedback"):
        # 只有本学生已提交的当前作答可以读取答案及解析。
        feedback = cp["feedback"]
    cursor = await db.get(LearningCursor, student.id)
    settlement = None
    if row.status == "completed":
        ledger = await db.scalar(
            select(RewardLedger).where(
                RewardLedger.student_id == student.id, RewardLedger.claim_key == f"session:{row.id}"
            )
        )
        settlement = ledger.result if ledger else None
    return SessionView(
        id=row.id,
        student_id=row.student_id,
        kind=row.kind,
        book_id=row.book_id,
        source_id=row.source_id,
        status=row.status,
        revision=row.revision,
        cursor=cursor.value if cursor else 0,
        sources=row.sources,
        checkpoint={k: v for k, v in cp.items() if k != "feedback"},
        question=question,
        feedback=feedback,
        settlement=settlement,
    ).model_dump(mode="json")


async def start(db, who, student_id, body, key):
    student = await learning_student(db, who, student_id)
    old, request_hash = await receipt(db, student.id, "start", key, body)
    if old is not None:
        return old
    session_id = uuid4()
    sources, refs = [], []
    book_id, source_id = body.book_id, body.source_id
    if body.kind == "review":
        _, day = await clock(db, student)
        refs = await due_review_refs(db, student, day, book_id, body.for_hearts)
        if not refs and body.for_hearts:
            if not book_id:
                book_id = await db.scalar(
                    select(TextbookSelection.book_id)
                    .join(
                        StudentSubject,
                        (StudentSubject.student_id == TextbookSelection.student_id)
                        & (StudentSubject.subject_code == TextbookSelection.subject_code),
                    )
                    .where(
                        TextbookSelection.student_id == student.id,
                        TextbookSelection.ended_at.is_(None),
                        StudentSubject.enabled.is_(True),
                    )
                    .order_by(TextbookSelection.started_at.desc())
                    .limit(1)
                )
            if book_id:
                await ensure_book(db, student, book_id)
                book = await db.get(Textbook, book_id)
                first = next((lesson for unit in book.units for lesson in unit["lessons"]), None)
                if first:
                    head, revision = await content_revision(db, book_id, "lesson", first["id"])
                    refs = [{**ref, "scheduled": False} for ref in revision.question_refs[:5]]
                    sources = [{"container_id": head.id, "version": revision.version}]
    elif body.kind == "jump":
        await ensure_book(db, student, book_id)
        sources = await jump_pool(db, book_id, body.target_unit)
        refs = sample_jump(sources, str(session_id))
    else:
        if body.kind == "number_review":
            await check_number_due(db, student, body.number_skill)
            _, today = await clock(db, student)
            variant = "odd" if today.day % 2 else "even"
            book_id = "g1up"
            source_id = f"number-review-{body.number_skill}-{variant}"
        if body.kind != "number_review":
            await ensure_book(db, student, book_id)
        head, revision = await content_revision(db, book_id, body.kind, source_id)
        refs = revision.question_refs
        sources = [
            {"container_id": head.id, "version": revision.version, "source_id": head.source_id}
        ]
    await check_hearts(db, student, body.kind, source_id)
    if not refs and body.kind != "reading":
        raise APIError(409, "NO_QUESTIONS", "当前没有可练习的题目")
    row = LearningSession(
        id=session_id,
        family_id=student.family_id,
        student_id=student.id,
        kind=body.kind,
        book_id=book_id,
        source_id=source_id,
        sources=sources,
        question_refs=refs,
        revision=1,
        status="active",
        checkpoint={
            "pending": list(range(len(refs))),
            "attempted": [],
            "solved": [],
            "first_correct": 0,
            "attempt_count": 0,
            "feedback": None,
            "draft": {},
            "target_unit": body.target_unit,
            "reading_kind": body.reading_kind,
            "number_skill": body.number_skill,
            "for_hearts": body.for_hearts,
            "hint_levels": {},
        },
    )
    db.add(row)
    await db.flush()
    await append_event(
        db,
        student,
        "session_started",
        {"session_id": str(row.id), "kind": row.kind},
        body.client_at,
    )
    response = await view(db, row, student)
    return await save_receipt(db, student.id, "start", key, request_hash, response)


async def authorized_session(db, who, session_id):
    if who.auth_session.mode != "child":
        raise APIError(403, "LEARNING_MODE_REQUIRED", "请先进入学生学习模式")
    student_id = await db.scalar(
        select(LearningSession.student_id).where(LearningSession.id == session_id)
    )
    if student_id is None:
        raise APIError(404, "LEARNING_SESSION_NOT_FOUND", "找不到学习会话")
    try:
        student = await learning_student(db, who, student_id)
    except APIError as error:
        if error.status_code == 404:
            raise APIError(404, "LEARNING_SESSION_NOT_FOUND", "找不到学习会话") from None
        raise
    row = await db.scalar(
        select(LearningSession)
        .where(LearningSession.id == session_id)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise APIError(404, "LEARNING_SESSION_NOT_FOUND", "找不到学习会话")
    return student, row


def check_revision(row, revision):
    if row.revision != revision:
        raise APIError(409, "LEARNING_REVISION_CONFLICT", "学习进度已变化，请刷新后继续")
    if row.status != "active":
        raise APIError(409, "SESSION_COMPLETED", "学习会话已经结束")


async def submit(db, who, session_id, body, key):
    student, row = await authorized_session(db, who, session_id)
    operation = f"answer:{session_id}"
    old, request_hash = await receipt(db, student.id, operation, key, body)
    if old is not None:
        return old
    check_revision(row, body.revision)
    await validate_evidence(db, row, body.evidence_sentence_indices)
    await check_hearts(db, student, row.kind, row.source_id)
    cp = dict(row.checkpoint)
    if cp["feedback"] or not cp["pending"]:
        raise APIError(409, "INVALID_ANSWER_ORDER", "请先确认当前反馈或刷新进度")
    index = cp["pending"][0]
    ref = row.question_refs[index]
    if ref["uid"] != body.question_uid or ref["version"] != body.question_version:
        raise APIError(409, "QUESTION_MISMATCH", "题目或版本不属于当前作答位置")
    question = await fixed_question(db, ref["uid"], ref["version"])
    if question.grading_rule_version != GRADING_RULE_VERSION:
        raise APIError(409, "GRADING_VERSION_UNAVAILABLE", "该题目的判分规则暂不可用")
    correct = grade_answer(question.private_payload, body.answer)
    first = index not in cp["attempted"]
    cp["attempted"] = list(dict.fromkeys([*cp["attempted"], index]))
    cp["attempt_count"] += 1
    if first and correct:
        cp["first_correct"] += 1
    if correct:
        cp["solved"] = [*cp["solved"], index]
    attempt = Attempt(
        student_id=student.id,
        session_id=row.id,
        ordinal=cp["attempt_count"],
        question_uid=ref["uid"],
        question_version=ref["version"],
        answer=body.answer,
        correct=correct,
        first_attempt=first,
        grading_rule_version=question.grading_rule_version,
        client_at=body.client_at,
        declared_duration_ms=body.declared_duration_ms,
        evidence={
            "hint_level": max(body.hint_level, cp.get("hint_levels", {}).get(str(index), 0)),
            "sentence_indices": body.evidence_sentence_indices,
        },
    )
    db.add(attempt)
    await db.flush()
    private = question.private_payload
    cp["feedback"] = {
        "attempt_id": str(attempt.id),
        "correct": correct,
        "first_attempt": first,
        "answer": private["answer"],
        "explanation": private.get("explanation", ""),
        "explanation_audio": (private.get("audio") or {}).get("explanation"),
        "evidence_sentence_indices": private.get("evidence_sentence_indices", []),
        "grading_rule_version": question.grading_rule_version,
        "submitted_answer": body.answer,
        "submitted_evidence_indices": body.evidence_sentence_indices,
    }
    cp["draft"] = {}
    row.checkpoint, row.revision = cp, row.revision + 1
    await append_event(
        db,
        student,
        "answer_submitted",
        {"session_id": str(row.id), "attempt_id": str(attempt.id)},
        body.client_at,
    )
    await record_attempt_effects(db, student, row.kind, row.source_id, attempt, body.client_at)
    response = await view(db, row, student)
    return await save_receipt(db, student.id, operation, key, request_hash, response)


async def change_checkpoint(db, who, session_id, body, key, action):
    student, row = await authorized_session(db, who, session_id)
    operation = f"{action}:{session_id}"
    old, request_hash = await receipt(db, student.id, operation, key, body)
    if old is not None:
        return old
    check_revision(row, body.revision)
    cp = dict(row.checkpoint)
    if action == "advance":
        if not cp["feedback"] or not cp["pending"]:
            raise APIError(409, "INVALID_ANSWER_ORDER", "当前没有待确认的反馈")
        index, rest = cp["pending"][0], cp["pending"][1:]
        # 普通课/挑战/数感/复习错题回到队尾；故事及跳级只按原顺序答一轮。
        if not cp["feedback"]["correct"] and row.kind not in {"story", "jump"}:
            rest.append(index)
        cp["pending"], cp["feedback"], cp["draft"] = rest, None, {}
        cp["matching_pairs"] = {}
    elif action == "draft":
        if cp["feedback"] or not cp["pending"]:
            raise APIError(409, "INVALID_CHECKPOINT_PHASE", "当前阶段不能保存答题草稿")
        await validate_evidence(db, row, body.evidence_sentence_indices)
        cp["draft"] = {
            "answer": body.answer,
            "intro_page": body.intro_page,
            "visual_draft": body.visual_draft,
            "evidence_sentence_indices": body.evidence_sentence_indices,
        }
    elif action == "hint":
        if cp["feedback"] or not cp["pending"] or row.kind == "number_review":
            raise APIError(409, "HINT_NOT_AVAILABLE", "当前阶段不提供提示")
        index = cp["pending"][0]
        ref = row.question_refs[index]
        question = await fixed_question(db, ref["uid"], ref["version"])
        hints = (question.private_payload.get("numberTask") or {}).get("hints", [])
        levels = dict(cp.get("hint_levels", {}))
        previous = levels.get(str(index), 0)
        if previous >= len(hints):
            raise APIError(409, "HINT_NOT_AVAILABLE", "没有更多提示")
        levels[str(index)] = previous + 1
        cp["hint_levels"] = levels
    row.checkpoint, row.revision = cp, row.revision + 1
    await append_event(
        db,
        student,
        "checkpoint_saved",
        {"session_id": str(row.id), "revision": row.revision},
        body.client_at,
    )
    response = await view(db, row, student)
    return await save_receipt(db, student.id, operation, key, request_hash, response)


async def check_matching_pair(db, who, session_id, body, key):
    student, row = await authorized_session(db, who, session_id)
    operation = f"matching-pair:{session_id}"
    old, request_hash = await receipt(db, student.id, operation, key, body)
    if old is not None:
        return old
    check_revision(row, body.revision)
    cp = dict(row.checkpoint)
    if cp["feedback"] or not cp["pending"]:
        raise APIError(409, "INVALID_ANSWER_ORDER", "当前阶段不能配对")
    ref = row.question_refs[cp["pending"][0]]
    if (ref["uid"], ref["version"]) != (body.question_uid, body.question_version):
        raise APIError(409, "QUESTION_MISMATCH", "题目或版本不属于当前作答位置")
    question = await fixed_question(db, ref["uid"], ref["version"])
    private = question.private_payload
    if private["type"] != "matching":
        raise APIError(409, "MATCHING_REQUIRED", "当前不是连线题")
    if question.grading_rule_version != GRADING_RULE_VERSION:
        raise APIError(409, "GRADING_VERSION_UNAVAILABLE", "该题目的判分规则暂不可用")
    expected = matching(private["answer"])
    size = min(4, len(private.get("options", [])) // 2)
    if not expected or body.left not in "ABCD"[:size] or int(body.right) > size:
        raise APIError(422, "INVALID_MATCHING_PAIR", "配对位置不存在")
    confirmed = dict(cp.get("matching_pairs", {}))
    if body.left in confirmed or body.right in confirmed.values():
        raise APIError(409, "MATCHING_ALREADY_CONFIRMED", "该位置已完成配对，请刷新进度")
    correct = expected.get(body.left) == body.right
    if correct:
        confirmed[body.left] = body.right
        cp["matching_pairs"] = confirmed
        cp["draft"] = {
            **cp.get("draft", {}),
            "answer": ",".join(f"{left}-{right}" for left, right in sorted(confirmed.items())),
        }
    row.checkpoint, row.revision = cp, row.revision + 1
    await append_event(
        db,
        student,
        "matching_pair_checked",
        {
            "session_id": str(row.id),
            "question_uid": ref["uid"],
            "question_version": ref["version"],
            "left": body.left,
            "right": body.right,
            "correct": correct,
        },
        body.client_at,
    )
    # 不写 Attempt、经济投影或奖励；整题仍须经 attempts/complete。
    response = {"correct": correct, "session": await view(db, row, student)}
    return await save_receipt(db, student.id, operation, key, request_hash, response)


async def validate_evidence(db, row, indices):
    if not indices:
        return
    if row.kind != "story" or not row.sources:
        raise APIError(422, "INVALID_EVIDENCE", "只有故事练习可以选择原文证据")
    source = row.sources[0]
    content = await db.get(ContentRevision, (source["container_id"], source["version"]))
    count = len(content.public_payload.get("sentences", [])) if content else 0
    if any(index < 1 or index > count for index in indices):
        raise APIError(422, "INVALID_EVIDENCE", "原文证据位置不存在")
