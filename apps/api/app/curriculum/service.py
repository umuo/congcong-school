from datetime import UTC, datetime

from sqlalchemy import select, update

from app.curriculum.models import StudentSubject, Subject, Textbook, TextbookSelection
from app.curriculum.schemas import CurriculumView, SelectionView, SubjectChoice, TextbookView
from app.errors import APIError
from app.students.models import Student


async def get_curriculum(db, student):
    subjects = (
        await db.scalars(
            select(StudentSubject)
            .where(
                StudentSubject.student_id == student.id,
                StudentSubject.family_id == student.family_id,
            )
            .order_by(StudentSubject.subject_code)
        )
    ).all()
    history = (
        await db.scalars(
            select(TextbookSelection)
            .where(
                TextbookSelection.student_id == student.id,
                TextbookSelection.family_id == student.family_id,
            )
            .order_by(TextbookSelection.started_at, TextbookSelection.id)
        )
    ).all()
    active = {h.subject_code: h for h in history if h.ended_at is None}
    return CurriculumView(
        revision=student.revision,
        subjects=[
            SubjectChoice(
                subject_code=s.subject_code,
                enabled=s.enabled,
                book_id=active[s.subject_code].book_id if s.subject_code in active else None,
                current_unit_number=active[s.subject_code].current_unit_number
                if s.subject_code in active
                else None,
            )
            for s in subjects
        ],
        history=[SelectionView.model_validate(h) for h in history],
    )


async def update_curriculum(db, student, choices, revision):
    if student.archived_at:
        raise APIError(409, "STUDENT_ARCHIVED", "归档学生不能更新学习配置")
    # 先锁定学生的全局配置版本，再修改学科及生效历史，避免并发覆盖。
    changed = await db.scalar(
        update(Student)
        .where(
            Student.id == student.id,
            Student.family_id == student.family_id,
            Student.revision == revision,
        )
        .values(revision=revision + 1)
        .returning(Student.id)
        .execution_options(synchronize_session=False)
    )
    if changed is None:
        raise APIError(409, "REVISION_CONFLICT", "配置已被修改，请刷新后重试")
    now = datetime.now(UTC)
    for choice in choices:
        if await db.get(Subject, choice.subject_code) is None:
            raise APIError(422, "SUBJECT_NOT_FOUND", "学科不在目录中")
        selection = await db.scalar(
            select(TextbookSelection).where(
                TextbookSelection.student_id == student.id,
                TextbookSelection.subject_code == choice.subject_code,
                TextbookSelection.ended_at.is_(None),
            )
        )
        book_id = choice.book_id or (selection.book_id if selection else None)
        if book_id:
            book = await db.get(Textbook, book_id)
            if book is None or book.subject_code != choice.subject_code:
                raise APIError(422, "TEXTBOOK_NOT_FOUND", "教材与学科不匹配")
            unit = choice.current_unit_number
            if unit is None and selection and selection.book_id == book_id:
                unit = selection.current_unit_number
            if unit is not None and unit not in {u["number"] for u in book.units}:
                raise APIError(422, "UNIT_NOT_FOUND", "教材单元不存在")
            if (
                selection is None
                or selection.book_id != book_id
                or selection.current_unit_number != unit
                or selection.snapshot["content_revision"] != book.content_revision
            ):
                if selection:
                    selection.ended_at = now
                    await db.flush()
                db.add(
                    TextbookSelection(
                        student_id=student.id,
                        family_id=student.family_id,
                        subject_code=choice.subject_code,
                        book_id=book_id,
                        current_unit_number=unit,
                        started_at=now,
                        snapshot=TextbookView.model_validate(book).model_dump(mode="json"),
                    )
                )
        elif choice.current_unit_number is not None:
            raise APIError(422, "TEXTBOOK_REQUIRED", "请先选择教材")
        setting = await db.get(StudentSubject, (student.id, choice.subject_code))
        if setting:
            setting.enabled = choice.enabled
        else:
            db.add(
                StudentSubject(
                    student_id=student.id,
                    family_id=student.family_id,
                    subject_code=choice.subject_code,
                    enabled=choice.enabled,
                )
            )
    await db.commit()
    await db.refresh(student)
    return await get_curriculum(db, student)
