"""知识点目录与学生掌握度诊断 API 路由。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Identity, identity, session
from app.diagnostics.schemas import (
    KnowledgePointDetailView,
    StudentDiagnosticsView,
    TextbookKnowledgeCatalogView,
)
from app.diagnostics.service import (
    get_knowledge_point_detail,
    get_student_diagnostics,
    get_textbook_knowledge_catalog,
)
from app.learning.authorization import learning_identity
from app.learning.router import read_student

router = APIRouter(prefix="/api/v1")
DB = Annotated[AsyncSession, Depends(session)]
Auth = Annotated[Identity, Depends(learning_identity)]


@router.get(
    "/textbooks/{book_id}/knowledge-points",
    response_model=TextbookKnowledgeCatalogView,
)
async def textbook_knowledge_points(
    book_id: str,
    db: DB,
    who: Annotated[Identity, Depends(identity)],
):
    return await get_textbook_knowledge_catalog(db, book_id)


@router.get(
    "/students/{student_id}/diagnostics",
    response_model=StudentDiagnosticsView,
)
async def student_diagnostics(
    student_id: UUID,
    request: Request,
    db: DB,
    who: Auth,
    subject_code: str | None = Query(default=None),
    book_id: str | None = Query(default=None),
):
    student = await read_student(student_id, request, db, who)
    return await get_student_diagnostics(
        db, student, subject_code=subject_code, book_id=book_id
    )


@router.get(
    "/students/{student_id}/diagnostics/knowledge-points/{kp_id}",
    response_model=KnowledgePointDetailView,
)
async def student_knowledge_point_detail(
    student_id: UUID,
    kp_id: str,
    request: Request,
    db: DB,
    who: Auth,
):
    student = await read_student(student_id, request, db, who)
    return await get_knowledge_point_detail(db, student, kp_id)
