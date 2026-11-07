from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Identity, identity, session
from app.content.media import media_paths, resolve_media_path
from app.content.models import ContentContainer, ContentRevision
from app.content.schemas import ContentKind, ContentView
from app.content.service import content_revision, content_view, jump_pool, resolve_question
from app.learning.authorization import learning_identity
from app.students.service import authorized_student

DB = Annotated[AsyncSession, Depends(session)]
Auth = Annotated[Identity, Depends(identity)]


async def content_identity(db: DB, who: Annotated[Identity, Depends(learning_identity)]):
    if who.auth_session.mode == "child":
        await authorized_student(db, who, who.auth_session.student_id, for_learning=True)
    return who


router = APIRouter(prefix="/api/v1/content", dependencies=[Depends(content_identity)])


@router.get("/books/{book_id}")
async def list_content(book_id: str, db: DB):
    rows = (
        await db.execute(
            select(ContentContainer, ContentRevision)
            .join(
                ContentRevision,
                (ContentRevision.container_id == ContentContainer.id)
                & (ContentRevision.version == ContentContainer.current_version),
            )
            .where(ContentContainer.book_id == book_id, ContentContainer.active.is_(True))
            .order_by(ContentContainer.kind, ContentContainer.source_id)
        )
    ).all()
    return [
        {
            "kind": c.kind,
            "source_id": c.source_id,
            "version": r.version,
            "title": r.public_payload.get("title"),
            "unit_number": r.public_payload.get("unitNumber"),
            "question_count": len(r.question_refs),
        }
        for c, r in rows
    ]


@router.get("/books/{book_id}/jump-pool")
async def get_jump_pool(book_id: str, db: DB, target_unit: int = Query(ge=2)):
    return await jump_pool(db, book_id, target_unit)


@router.get("/question-mapping")
async def mapping(
    db: DB, kind: ContentKind, book_id: str, source_id: str, question_id: int = Query(gt=0)
):
    value = await resolve_question(db, kind, book_id, source_id, question_id)
    return {
        "uid": value.uid,
        "kind": value.kind,
        "book_id": value.book_id,
        "source_id": value.source_id,
        "source_question_id": value.source_question_id,
    }


@router.get("/books/{book_id}/{kind}/{source_id}", response_model=ContentView)
async def get_content(
    book_id: str,
    kind: ContentKind,
    source_id: str,
    db: DB,
    version: str | None = Query(default=None, pattern=r"^[a-f0-9]{64}$"),
):
    head, revision = await content_revision(db, book_id, kind, source_id, version)
    return content_view(head, revision)


@router.get("/books/{book_id}/{kind}/{source_id}/media")
async def get_content_media(
    book_id: str, kind: ContentKind, source_id: str, path: str, request: Request, db: DB
):
    _, revision = await content_revision(db, book_id, kind, source_id)
    target = resolve_media_path(
        request.app.state.settings.content_root / "apps/web/public",
        path,
        media_paths(revision.public_payload),
    )
    return FileResponse(
        target, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    )
