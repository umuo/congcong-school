from sqlalchemy import select

from app.content.models import ContentContainer, ContentRevision, QuestionIdentity, QuestionVersion
from app.content.schemas import ContentView
from app.errors import APIError


async def content_revision(db, book_id, kind, source_id, version=None):
    head = await db.scalar(
        select(ContentContainer)
        .execution_options(populate_existing=True)
        .where(
            ContentContainer.book_id == book_id,
            ContentContainer.kind == kind,
            ContentContainer.source_id == source_id,
            ContentContainer.active.is_(True),
        )
    )
    if head is None or head.current_version is None:
        raise APIError(404, "CONTENT_NOT_FOUND", "找不到可用内容")
    revision = await db.get(ContentRevision, (head.id, version or head.current_version))
    if revision is None:
        raise APIError(404, "CONTENT_VERSION_NOT_FOUND", "找不到指定内容版本")
    return head, revision


def content_view(head, revision):
    return ContentView(
        id=head.id,
        kind=head.kind,
        book_id=head.book_id,
        source_id=head.source_id,
        version=revision.version,
        metadata=revision.public_payload,
        question_refs=revision.question_refs,
    )


async def resolve_question(db, kind, book_id, source_id, source_question_id):
    identity = await db.scalar(
        select(QuestionIdentity).where(
            QuestionIdentity.kind == kind,
            QuestionIdentity.book_id == book_id,
            QuestionIdentity.source_id == source_id,
            QuestionIdentity.source_question_id == source_question_id,
        )
    )
    if identity is None:
        raise APIError(404, "QUESTION_NOT_MAPPED", "题目没有精确来源映射")
    return identity


async def fixed_question(db, uid, version):
    value = await db.get(QuestionVersion, (uid, version))
    if value is None:
        raise APIError(404, "QUESTION_VERSION_NOT_FOUND", "找不到题目版本")
    return value


async def jump_pool(db, book_id, target_unit):
    rows = (
        await db.execute(
            select(ContentContainer, ContentRevision)
            .join(
                ContentRevision,
                (ContentRevision.container_id == ContentContainer.id)
                & (ContentRevision.version == ContentContainer.current_version),
            )
            .where(
                ContentContainer.book_id == book_id,
                ContentContainer.kind == "lesson",
                ContentContainer.active.is_(True),
            )
            .execution_options(populate_existing=True)
        )
    ).all()
    sources = []
    target_exists = False
    # 在应用中读取原 JSON；PostgreSQL JSON 路径操作也可能拒绝原文的转义 NUL。
    rows.sort(
        key=lambda row: (
            row[1].public_payload.get("unitNumber", 0),
            row[1].public_payload.get("kpIndex", 0),
            row[0].source_id,
        )
    )
    for head, revision in rows:
        unit = revision.public_payload.get("unitNumber")
        if unit == target_unit:
            target_exists = True
        if isinstance(unit, int) and unit < target_unit:
            sources.append(
                {
                    "lesson_id": head.source_id,
                    "version": head.current_version,
                    "question_refs": revision.question_refs,
                }
            )
    if not target_exists or not sources:
        raise APIError(404, "JUMP_TARGET_NOT_FOUND", "没有可用的跳级目标或前置题库")
    return sources
