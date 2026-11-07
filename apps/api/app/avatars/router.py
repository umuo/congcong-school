from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Identity, identity, recently_verified, session
from app.auth.models import User
from app.auth.service import client_context
from app.avatars.catalog import CATALOG, AvatarID
from app.errors import APIError
from app.students.models import Student
from app.students.router import expected_revision
from app.students.service import authorized_student

router = APIRouter(prefix="/api/v1")
DB = Annotated[AsyncSession, Depends(session)]
Auth = Annotated[Identity, Depends(identity)]


class AvatarUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    avatar_id: AvatarID


async def subject(db, who, *, lock=False):
    if who.auth_session.mode == "child":
        return await authorized_student(
            db, who, who.auth_session.student_id, for_learning=True, lock=lock
        )
    if who.user.role not in {"parent", "admin"} or who.auth_session.mode != who.user.role:
        raise APIError(403, "AVATAR_FORBIDDEN", "当前身份不能修改头像")
    return who.user


def view(row):
    student = isinstance(row, Student)
    return {
        "scope_kind": "student" if student else "user",
        "subject_id": str(row.id),
        "avatar_id": row.avatar,
        "revision": row.revision if student else row.avatar_revision,
        "catalog_version": CATALOG["version"],
    }


@router.get("/avatar-presets")
async def presets(who: Auth):
    return CATALOG


@router.get("/me/avatar")
async def get_avatar(request: Request, who: Auth, db: DB):
    expected = request.headers.get("x-csf-learning-context")
    if expected is not None and expected != str(client_context(who.user, who.auth_session)):
        raise APIError(409, "LEARNING_CONTEXT_CHANGED", "登录身份已变化，请刷新后继续")
    return view(await subject(db, who))


@router.put("/me/avatar")
async def put_avatar(
    body: AvatarUpdate,
    request: Request,
    who: Auth,
    db: DB,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    expected = request.headers.get("x-csf-learning-context")
    if expected is None:
        raise APIError(428, "CONTEXT_REQUIRED", "请先读取当前身份")
    if expected != str(client_context(who.user, who.auth_session)):
        raise APIError(409, "LEARNING_CONTEXT_CHANGED", "登录身份已变化，请刷新后继续")
    revision = expected_revision(if_match)
    row = await subject(db, who, lock=True)
    student = isinstance(row, Student)
    if not student:
        recently_verified(request, who)
    model = Student if student else User
    version = model.revision if student else model.avatar_revision
    values = {"avatar": body.avatar_id, "revision" if student else "avatar_revision": revision + 1}
    result = await db.scalar(
        update(model)
        .where(model.id == row.id, version == revision)
        .values(**values)
        .returning(model.id)
        .execution_options(synchronize_session=False)
    )
    if result is None:
        raise APIError(409, "REVISION_CONFLICT", "头像已被修改，请读取最新头像后重试")
    await db.commit()
    await db.refresh(row)
    return view(row)
