from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Identity, identity, recently_verified, session, verified_parent
from app.errors import APIError
from app.families.models import Membership
from app.learning.authorization import learning_identity
from app.portability.imports import confirm, import_view, preview, read_backup
from app.portability.models import DeletionReceipt, LegacyImport
from app.portability.privacy import backup_policy, delete_target, export_family
from app.students.service import authorized_student, family_id

router = APIRouter(prefix="/api/v1")
DB = Annotated[AsyncSession, Depends(session)]
Parent = Annotated[Identity, Depends(verified_parent)]
Key = Annotated[UUID, Header(alias="Idempotency-Key")]


class ImportConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: UUID
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision: int = Field(ge=1)


@router.post("/students/{student_id}/imports/preview")
async def preview_import(student_id: UUID, request: Request, who: Parent, db: DB):
    student = await authorized_student(db, who, student_id, for_learning=True, lock=True)
    value, source_hash = await read_backup(request)
    return await preview(db, student, value, source_hash)


@router.post("/students/{student_id}/imports/confirm")
async def confirm_import(student_id: UUID, body: ImportConfirm, who: Parent, db: DB):
    student = await authorized_student(db, who, student_id, for_learning=True, lock=True)
    return await confirm(db, student, body)


@router.get("/students/{student_id}/legacy")
async def legacy_summaries(
    student_id: UUID, request: Request, db: DB, who: Annotated[Identity, Depends(learning_identity)]
):
    if who.user.role == "parent" and who.auth_session.mode == "parent":
        recently_verified(request, who)
    await authorized_student(db, who, student_id, for_learning=who.auth_session.mode == "child")
    rows = (
        await db.scalars(
            select(LegacyImport).where(
                LegacyImport.student_id == student_id, LegacyImport.confirmed_at.is_not(None)
            )
        )
    ).all()
    return [{**import_view(row), "summary": row.payload} for row in rows]


@router.get("/family/export")
async def export(who: Parent, db: DB):
    return await export_family(db, await family_id(db, who))


@router.get("/privacy/policy")
async def policy(request: Request, who: Annotated[Identity, Depends(identity)]):
    return backup_policy(request.app.state.settings)


@router.delete("/students/{student_id}", status_code=204)
async def delete_student(
    student_id: UUID, request: Request, who: Parent, db: DB, key: Key, confirm: str
):
    if confirm != str(student_id):
        raise APIError(422, "DELETE_CONFIRMATION_REQUIRED", "请确认需要删除的学生范围")
    # 相同家长及原键重放可在目标已删除时返回原成功结果。
    if await db.get(DeletionReceipt, (who.user.id, key)) is None:
        await authorized_student(db, who, student_id)
    await delete_target(db, who, "student", student_id, key, request.app.state.settings)
    return Response(status_code=204)


@router.delete("/account", status_code=204)
async def delete_account(request: Request, who: Parent, db: DB, key: Key, confirm: str):
    member = await db.scalar(select(Membership).where(Membership.user_id == who.user.id))
    if member is None or member.role != "owner":
        raise APIError(403, "OWNER_REQUIRED", "只有最近验证的家庭所有者可以删除整个家庭")
    if confirm != str(member.family_id):
        raise APIError(422, "DELETE_CONFIRMATION_REQUIRED", "请确认整个家庭及账号的删除范围")
    await delete_target(db, who, "family", member.family_id, key, request.app.state.settings)
    response = Response(status_code=204)
    response.delete_cookie("csf_session")
    response.delete_cookie("csf_csrf")
    return response
