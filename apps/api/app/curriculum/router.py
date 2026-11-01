from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Identity, identity, session, verified_parent
from app.curriculum.models import Subject, Textbook
from app.curriculum.schemas import CurriculumUpdate, CurriculumView, SubjectView, TextbookList
from app.curriculum.service import get_curriculum, update_curriculum
from app.students.router import Revision, expected_revision
from app.students.service import authorized_student

router = APIRouter(prefix="/api/v1")
DB = Annotated[AsyncSession, Depends(session)]
Parent = Annotated[Identity, Depends(verified_parent)]


@router.get("/subjects", response_model=list[SubjectView])
async def subjects(db: DB, who: Annotated[Identity, Depends(identity)]):
    return (await db.scalars(select(Subject).order_by(Subject.code))).all()


@router.get("/textbooks", response_model=TextbookList)
async def textbooks(
    db: DB,
    who: Annotated[Identity, Depends(identity)],
    subject_code: str | None = None,
    grade: int | None = None,
    publisher_label: str | None = None,
    province: str | None = None,
):
    query = select(Textbook)
    if subject_code:
        query = query.where(Textbook.subject_code == subject_code)
    if grade is not None:
        query = query.where(Textbook.grade == grade)
    if publisher_label:
        query = query.where(Textbook.publisher_label == publisher_label)
    # 当前没有可信地区推荐数据，不按地区限制可选教材。
    return TextbookList(items=(await db.scalars(query.order_by(Textbook.id))).all())


@router.get("/students/{student_id}/curriculum", response_model=CurriculumView)
async def curriculum(student_id: UUID, who: Parent, db: DB):
    student = await authorized_student(db, who, student_id)
    return await get_curriculum(db, student)


@router.get("/learning/curriculum")
async def learning_curriculum(db: DB, who: Annotated[Identity, Depends(identity)]):
    if who.auth_session.mode != "child":
        from app.errors import APIError

        raise APIError(403, "CHILD_MODE_REQUIRED", "请先选择孩子学习档案")
    student = await authorized_student(db, who, who.auth_session.student_id, for_learning=True)
    config = await get_curriculum(db, student)
    # 学习端只读取本人当前启用配置，不返回历史快照、家长备注或家庭资料。
    return {
        "student_id": student.id,
        "revision": config.revision,
        "subjects": [s.model_dump() for s in config.subjects if s.enabled],
    }


@router.put("/students/{student_id}/curriculum", response_model=CurriculumView)
async def save_curriculum(
    student_id: UUID,
    body: CurriculumUpdate,
    who: Parent,
    db: DB,
    if_match: Revision = None,
):
    student = await authorized_student(db, who, student_id)
    return await update_curriculum(db, student, body.subjects, expected_revision(if_match))
