from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Identity
from app.auth.models import StudentAccount
from app.errors import APIError
from app.families.models import Membership
from app.students.models import Student


async def family_id(db: AsyncSession, who: Identity) -> UUID:
    if who.user.role != "parent":
        raise APIError(403, "PARENT_REQUIRED", "需要家长权限")
    value = await db.scalar(select(Membership.family_id).where(Membership.user_id == who.user.id))
    if value is None:
        raise APIError(404, "FAMILY_NOT_FOUND", "找不到家庭")
    return value


async def authorized_student(
    db: AsyncSession,
    who: Identity,
    student_id: UUID,
    *,
    for_learning: bool = False,
    lock: bool = False,
) -> Student:
    # 在同一个查询中验证成员与学生归属，不先按裸 student_id 读取私有资料。
    if who.user.role == "student":
        statement = (
            select(Student)
            .join(
                StudentAccount,
                (StudentAccount.student_id == Student.id)
                & (StudentAccount.family_id == Student.family_id),
            )
            .where(Student.id == student_id, StudentAccount.user_id == who.user.id)
        )
    elif who.user.role == "parent":
        statement = select(Student)
        statement = statement.join(Membership, Membership.family_id == Student.family_id).where(
            Student.id == student_id, Membership.user_id == who.user.id
        )
    else:
        raise APIError(403, "PARENT_REQUIRED", "管理员不能直接访问家庭学习资料")
    if lock:
        statement = statement.with_for_update(of=Student).execution_options(populate_existing=True)
    student = await db.scalar(statement)
    if student is None:
        raise APIError(404, "STUDENT_NOT_FOUND", "找不到学生")
    if who.auth_session.mode == "child" and who.auth_session.student_id != student_id:
        raise APIError(404, "STUDENT_NOT_FOUND", "找不到学生")
    if for_learning and student.archived_at:
        raise APIError(409, "STUDENT_ARCHIVED", "该学生档案已归档")
    return student
