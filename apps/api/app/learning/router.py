from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Identity, recently_verified, session
from app.content.schemas import public_question
from app.content.service import fixed_question
from app.families.models import Family
from app.learning import economy as economy_rules
from app.learning.activity import rebuild, submit_time
from app.learning.authorization import learning_identity
from app.learning.economy_service import action, clock, complete, load_state, progress_view
from app.learning.models import EconomyState, LearningEvent
from app.learning.review import review_bank
from app.learning.schemas import (
    AnswerBody,
    CompleteBody,
    DraftBody,
    EconomyAction,
    PublicQuestion,
    RevisionBody,
    SessionView,
    StartSession,
    TimeCheckpoint,
)
from app.learning.service import (
    authorized_session,
    change_checkpoint,
    learning_student,
    start,
    submit,
    view,
)
from app.students.service import authorized_student

router = APIRouter(prefix="/api/v1")
DB = Annotated[AsyncSession, Depends(session)]
Auth = Annotated[Identity, Depends(learning_identity)]
Key = Annotated[UUID, Header(alias="Idempotency-Key")]


@router.post("/students/{student_id}/learning-sessions", response_model=SessionView)
async def start_session(student_id: UUID, body: StartSession, key: Key, db: DB, who: Auth):
    return await start(db, who, student_id, body, key)


@router.get("/learning-sessions/{session_id}", response_model=SessionView)
async def get_session(session_id: UUID, db: DB, who: Auth):
    student, row = await authorized_session(db, who, session_id)
    return await view(db, row, student)


@router.post("/learning-sessions/{session_id}/attempts", response_model=SessionView)
async def answer(session_id: UUID, body: AnswerBody, key: Key, db: DB, who: Auth):
    return await submit(db, who, session_id, body, key)


@router.post("/learning-sessions/{session_id}/advance", response_model=SessionView)
async def advance(session_id: UUID, body: RevisionBody, key: Key, db: DB, who: Auth):
    return await change_checkpoint(db, who, session_id, body, key, "advance")


@router.put("/learning-sessions/{session_id}/checkpoint", response_model=SessionView)
async def checkpoint(session_id: UUID, body: DraftBody, key: Key, db: DB, who: Auth):
    return await change_checkpoint(db, who, session_id, body, key, "draft")


@router.get("/students/{student_id}/changes")
async def changes(
    student_id: UUID,
    request: Request,
    db: DB,
    who: Auth,
    after: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    await read_student(student_id, request, db, who)
    rows = (
        await db.scalars(
            select(LearningEvent)
            .where(LearningEvent.student_id == student_id, LearningEvent.cursor > after)
            .order_by(LearningEvent.cursor)
            .limit(limit)
        )
    ).all()
    return {
        "student_id": student_id,
        "after": after,
        "next_cursor": rows[-1].cursor if rows else after,
        "events": [
            {
                "cursor": row.cursor,
                "kind": row.kind,
                "payload": row.payload,
                "client_at": row.client_at,
                "received_at": row.received_at,
            }
            for row in rows
        ],
    }


@router.post("/learning-sessions/{session_id}/complete")
async def finish(session_id: UUID, body: CompleteBody, key: Key, db: DB, who: Auth):
    student, row = await authorized_session(db, who, session_id)
    return await complete(db, student, row, body, key)


@router.post("/students/{student_id}/economy/actions")
async def economy_action(student_id: UUID, body: EconomyAction, key: Key, db: DB, who: Auth):
    student = await learning_student(db, who, student_id)
    return await action(db, student, body, key)


@router.get("/students/{student_id}/progress")
async def get_progress(student_id: UUID, request: Request, db: DB, who: Auth):
    if who.user.role == "parent" and who.auth_session.mode == "parent":
        recently_verified(request, who)
        student = await authorized_student(db, who, student_id, lock=True)
    else:
        student = await learning_student(db, who, student_id)
    row, state = await load_state(db, student)
    now, _ = await clock(db, student)
    economy_rules.refresh_hearts(state, int(now.timestamp() * 1000))
    return await progress_view(db, student, row, state)


@router.get("/learning/shop")
async def shop(who: Auth):
    return {"version": economy_rules.VERSION, "items": economy_rules.POLICY["cosmetics"]}


async def read_student(student_id, request, db, who):
    if who.user.role == "parent" and who.auth_session.mode == "parent":
        recently_verified(request, who)
        return await authorized_student(db, who, student_id, lock=True)
    return await learning_student(db, who, student_id)


@router.post("/learning-sessions/{session_id}/hint", response_model=SessionView)
async def hint(session_id: UUID, body: RevisionBody, key: Key, db: DB, who: Auth):
    return await change_checkpoint(db, who, session_id, body, key, "hint")


@router.post("/students/{student_id}/events")
async def events(student_id: UUID, body: TimeCheckpoint, key: Key, db: DB, who: Auth):
    student = await learning_student(db, who, student_id)
    return await submit_time(db, student, body, key)


@router.get("/students/{student_id}/summary")
async def summary(student_id: UUID, request: Request, db: DB, who: Auth):
    student = await read_student(student_id, request, db, who)
    family = await db.get(Family, student.family_id)
    _, today = await clock(db, student)
    rows = (
        await db.scalars(
            select(LearningEvent)
            .where(LearningEvent.student_id == student.id)
            .order_by(LearningEvent.cursor)
        )
    ).all()
    result = rebuild(rows, family.timezone, today)
    row = await db.get(EconomyState, student.id)
    result["projection_matches"] = (
        (row.payload == result["state"] and row.revision == result["projection_revision"])
        if row
        else result["state"] == economy_rules.initial_state()
    )
    result["student_id"] = str(student.id)
    return result


@router.get("/students/{student_id}/mistakes")
async def mistakes(student_id: UUID, request: Request, db: DB, who: Auth):
    student = await read_student(student_id, request, db, who)
    bank = await review_bank(db, student)
    result = []
    for entry in bank.values():
        version = await fixed_question(db, entry["uid"], entry["version"])
        question = PublicQuestion.model_validate(
            public_question(version.private_payload, uid=entry["uid"], version=entry["version"])
        )
        result.append({**entry, "question": question.model_dump()})
    return result
