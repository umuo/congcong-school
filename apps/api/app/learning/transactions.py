from app.content.import_content import digest
from app.errors import APIError
from app.learning.models import LearningCursor, LearningEvent, LearningReceipt


async def cursor_for(db, student):
    cursor = await db.get(LearningCursor, student.id)
    if cursor is None:
        cursor = LearningCursor(student_id=student.id, family_id=student.family_id, value=0)
        db.add(cursor)
        await db.flush()
    return cursor


async def append_event(db, student, kind, payload, client_at):
    cursor = await cursor_for(db, student)
    cursor.value += 1
    db.add(
        LearningEvent(
            student_id=student.id,
            cursor=cursor.value,
            kind=kind,
            payload=payload,
            client_at=client_at,
        )
    )
    await db.flush()
    return cursor.value


async def receipt(db, student_id, operation, key, body):
    old = await db.get(LearningReceipt, (student_id, operation, key))
    request_hash = digest(body.model_dump(mode="json"))
    if old is not None:
        if old.request_hash != request_hash:
            raise APIError(409, "IDEMPOTENCY_CONFLICT", "同一操作标识不能用于不同请求")
        return old.response, request_hash
    return None, request_hash


async def save_receipt(db, student_id, operation, key, request_hash, response):
    db.add(
        LearningReceipt(
            student_id=student_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
            response=response,
        )
    )
    await db.commit()
    return response
