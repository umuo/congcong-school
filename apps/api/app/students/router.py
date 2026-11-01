from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Identity, session, verified_parent
from app.errors import APIError
from app.students.models import Student
from app.students.schemas import StudentCreate, StudentUpdate, StudentView
from app.students.service import authorized_student, family_id

router = APIRouter(prefix="/api/v1/students")
DB = Annotated[AsyncSession, Depends(session)]
Parent = Annotated[Identity, Depends(verified_parent)]
Revision = Annotated[str | None, Header(alias="If-Match")]


def expected_revision(value: str | None) -> int:
    if value is None:
        raise APIError(428, "REVISION_REQUIRED", "请先读取最新资料")
    raw = value.strip('"')
    if not raw.isdecimal() or int(raw) < 1:
        raise APIError(422, "INVALID_REVISION", "资料版本无效")
    return int(raw)


@router.get("", response_model=list[StudentView])
async def list_students(who: Parent, db: DB, include_archived: bool = False):
    query = select(Student).where(Student.family_id == await family_id(db, who))
    if not include_archived:
        query = query.where(Student.archived_at.is_(None))
    return (await db.scalars(query.order_by(Student.id))).all()


@router.post("", status_code=201, response_model=StudentView)
async def create_student(body: StudentCreate, who: Parent, db: DB):
    student = Student(family_id=await family_id(db, who), **body.model_dump())
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentView)
async def get_student(student_id: UUID, who: Parent, db: DB):
    return await authorized_student(db, who, student_id)


@router.patch("/{student_id}", response_model=StudentView)
async def update_student(
    student_id: UUID, body: StudentUpdate, who: Parent, db: DB, if_match: Revision = None
):
    student = await authorized_student(db, who, student_id)
    revision = expected_revision(if_match)
    result = await db.execute(
        update(Student)
        .where(
            Student.id == student.id,
            Student.family_id == student.family_id,
            Student.revision == revision,
        )
        .values(**body.model_dump(exclude_unset=True), revision=revision + 1)
        .returning(Student.id)
        .execution_options(synchronize_session=False)
    )
    if result.scalar_one_or_none() is None:
        raise APIError(409, "REVISION_CONFLICT", "资料已被修改，请刷新后重试")
    await db.commit()
    await db.refresh(student)
    return student


@router.post("/{student_id}/archive", response_model=StudentView)
async def archive_student(student_id: UUID, who: Parent, db: DB, if_match: Revision = None):
    student = await authorized_student(db, who, student_id)
    revision = expected_revision(if_match)
    result = await db.execute(
        update(Student)
        .where(
            Student.id == student.id,
            Student.family_id == student.family_id,
            Student.revision == revision,
        )
        .values(archived_at=datetime.now(UTC), revision=revision + 1)
        .returning(Student.id)
        .execution_options(synchronize_session=False)
    )
    if result.scalar_one_or_none() is None:
        raise APIError(409, "REVISION_CONFLICT", "资料已被修改，请刷新后重试")
    await db.commit()
    await db.refresh(student)
    return student
