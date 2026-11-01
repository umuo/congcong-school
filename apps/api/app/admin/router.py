from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import ParentCreate, ResetPassword, StudentAccountCreate
from app.auth import service
from app.auth.adapters import user_manager
from app.auth.dependencies import Identity, administrator, session
from app.auth.models import StudentAccount, User
from app.auth.schemas import normalize_login
from app.errors import APIError
from app.families.models import Family, Membership
from app.students.models import Student

router = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(administrator)])
DB = Annotated[AsyncSession, Depends(session)]
Admin = Annotated[Identity, Depends(administrator)]


def account_summary(user, *, family_id=None, student_id=None):
    return {
        **service.user_view(user),
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
        "family_id": family_id,
        "student_id": student_id,
    }


async def commit(db):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise APIError(409, "ACCOUNT_CONFLICT", "账号或学生绑定已存在，请刷新后重试") from None


@router.get("/families")
async def families(db: DB):
    return [
        {"id": f.id, "name": f.name}
        for f in (await db.scalars(select(Family).order_by(Family.name))).all()
    ]


@router.get("/login-availability")
async def login_availability(db: DB, login_name: str = Query(min_length=3, max_length=320)):
    try:
        normalized = normalize_login(login_name)
    except ValueError:
        raise APIError(422, "INVALID_LOGIN_NAME", "账号格式无效") from None
    exists = await db.scalar(select(User.id).where(User.login_name == normalized))
    return {"login_name": normalized, "available": exists is None}


@router.get("/student-profiles")
async def profiles(db: DB, family_id: UUID):
    return [
        {
            "id": s.id,
            "nickname": s.nickname,
            "family_id": s.family_id,
            "archived": bool(s.archived_at),
        }
        for s in (
            await db.scalars(
                select(Student).where(Student.family_id == family_id).order_by(Student.nickname)
            )
        ).all()
    ]


@router.get("/parents")
async def parents(db: DB):
    rows = (
        await db.execute(
            select(User, Membership.family_id)
            .join(Membership, Membership.user_id == User.id)
            .where(User.role == "parent")
            .order_by(User.login_name)
        )
    ).all()
    return [account_summary(u, family_id=f) for u, f in rows]


@router.get("/students")
async def students(db: DB):
    rows = (
        await db.execute(
            select(User, StudentAccount)
            .join(StudentAccount, StudentAccount.user_id == User.id)
            .where(User.role == "student")
            .order_by(User.login_name)
        )
    ).all()
    return [account_summary(u, family_id=b.family_id, student_id=b.student_id) for u, b in rows]


async def new_user(db, body, role):
    if await db.scalar(select(User.id).where(User.login_name == body.login_name)):
        raise APIError(409, "LOGIN_NAME_TAKEN", "该账号已存在，请换一个账号")
    return await service.create_account(
        db,
        login_name=body.login_name,
        password=body.password.get_secret_value(),
        nickname=body.nickname,
        role=role,
        email=str(body.email) if body.email else None,
    )


@router.post("/parents", status_code=201)
async def create_parent(body: ParentCreate, db: DB):
    try:
        if body.family_id:
            family = await db.get(Family, body.family_id)
            if family is None:
                raise APIError(404, "FAMILY_NOT_FOUND", "找不到家庭")
            member_role = "guardian"
        else:
            family = Family(name=body.family_name.strip())
            db.add(family)
            await db.flush()
            member_role = "owner"
        user = await new_user(db, body, "parent")
        db.add(Membership(user_id=user.id, family_id=family.id, role=member_role))
        await commit(db)
    except IntegrityError:
        await db.rollback()
        raise APIError(409, "ACCOUNT_CONFLICT", "账号已存在") from None
    return account_summary(user, family_id=family.id)


@router.post("/students", status_code=201)
async def create_student(body: StudentAccountCreate, db: DB):
    try:
        if await db.get(Family, body.family_id) is None:
            raise APIError(404, "FAMILY_NOT_FOUND", "找不到家庭")
        if body.student_id:
            student = await db.scalar(
                select(Student)
                .where(Student.id == body.student_id, Student.family_id == body.family_id)
                .with_for_update()
            )
            if student is None:
                raise APIError(404, "STUDENT_NOT_FOUND", "找不到学生")
            if student.archived_at:
                raise APIError(409, "STUDENT_ARCHIVED", "该学生档案已归档")
        else:
            student = Student(family_id=body.family_id, **body.profile.model_dump())
            db.add(student)
            await db.flush()
        user = await new_user(db, body, "student")
        db.add(StudentAccount(user_id=user.id, family_id=student.family_id, student_id=student.id))
        await commit(db)
    except IntegrityError:
        await db.rollback()
        raise APIError(409, "ACCOUNT_CONFLICT", "账号或学生绑定已存在") from None
    return account_summary(user, family_id=student.family_id, student_id=student.id)


async def managed_user(db, user_id):
    user = await db.scalar(
        select(User)
        .where(User.id == user_id, User.role.in_(["parent", "student"]))
        .with_for_update()
    )
    if user is None:
        raise APIError(404, "ACCOUNT_NOT_FOUND", "找不到可管理的账号")
    return user


@router.post("/users/{user_id}/disable", status_code=204)
async def disable(user_id: UUID, db: DB):
    user = await managed_user(db, user_id)
    user.is_active = False
    await service.revoke_sessions(db, user.id)
    await db.commit()


@router.post("/users/{user_id}/reset-password", status_code=204)
async def reset_password(user_id: UUID, body: ResetPassword, db: DB):
    user = await managed_user(db, user_id)
    user.hashed_password = user_manager(db).password_helper.hash(body.password.get_secret_value())
    user.must_change_password = False
    await service.revoke_sessions(db, user.id)
    await db.commit()
