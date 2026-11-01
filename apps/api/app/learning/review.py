"""按追加事件重建复习候选；课程回炉的复答不能抹去首答错题。"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.content.models import QuestionIdentity
from app.families.models import Family
from app.learning.models import Attempt, LearningEvent, LearningSession


def review_entry(entry, correct, day):
    result = dict(entry)
    result["last_reviewed"] = day
    if not correct:
        result.update(box=1, correct_count=0, due=day, graduated=False)
    else:
        box = entry.get("box", 1)
        result.update(
            box=min(3, box + 1),
            correct_count=entry.get("correct_count", 0) + 1,
            due=day + timedelta(days={1: 1, 2: 3, 3: 7}[box]),
        )
        result["graduated"] = result["box"] >= 3 and result["correct_count"] >= 2
    return result


async def review_bank(db, student):
    rows = (
        await db.execute(
            select(
                Attempt,
                LearningSession.kind,
                LearningSession.question_refs,
                QuestionIdentity.book_id,
                QuestionIdentity.source_id,
            )
            .join(LearningSession, LearningSession.id == Attempt.session_id)
            .join(QuestionIdentity, QuestionIdentity.uid == Attempt.question_uid)
            .where(Attempt.student_id == student.id)
        )
    ).all()
    attempts = {str(a.id): (a, kind, refs, book, source) for a, kind, refs, book, source in rows}
    events = (
        await db.scalars(
            select(LearningEvent)
            .where(
                LearningEvent.student_id == student.id,
                LearningEvent.kind.in_(["answer_submitted", "session_completed"]),
            )
            .order_by(LearningEvent.cursor)
        )
    ).all()
    family = await db.get(Family, student.family_id)
    zone = ZoneInfo(family.timezone)
    bank = {}
    for event in events:
        if event.kind == "session_completed":
            payload = event.payload
            if (
                payload.get("kind") in {"lesson", "challenge"}
                and payload.get("accuracy", 0) >= 0.999
            ):
                bank = {
                    uid: entry
                    for uid, entry in bank.items()
                    if not (
                        entry["book_id"] == payload.get("book_id")
                        and entry["source_id"] == payload.get("source_id")
                    )
                }
            continue
        item = attempts.get(event.payload.get("attempt_id"))
        if item is None:
            continue
        attempt, kind, refs, book, source = item
        if not attempt.first_attempt:
            continue
        uid = attempt.question_uid
        at = event.received_at.astimezone(zone).date()
        if kind in {"lesson", "challenge"} and not attempt.correct:
            bank[uid] = {
                "uid": uid,
                "version": attempt.question_version,
                "book_id": book,
                "source_id": source,
                "box": 1,
                "correct_count": 0,
                "due": at,
                "added": at,
                "graduated": False,
                "last_reviewed": at,
                "added_at": event.received_at.isoformat(),
                "last_reviewed_at": event.received_at.isoformat(),
            }
        elif (
            kind == "review"
            and uid in bank
            and any(ref["uid"] == uid and ref.get("scheduled", True) for ref in refs)
        ):
            bank[uid] = review_entry(bank[uid], attempt.correct, at)
            bank[uid]["last_reviewed_at"] = event.received_at.isoformat()
    return bank


async def due_review_refs(db, student, day, book_id=None, for_hearts=False):
    bank = await review_bank(db, student)
    entries = [entry for entry in bank.values() if not book_id or entry["book_id"] == book_id]
    due = [entry for entry in entries if not entry["graduated"] and entry["due"] <= day]
    due.sort(key=lambda entry: (entry["box"], entry["last_reviewed_at"], entry["uid"]))
    chosen = [
        {"uid": entry["uid"], "version": entry["version"], "scheduled": True} for entry in due
    ]
    if for_hearts:
        chosen = chosen[:5]
        seen = {ref["uid"] for ref in chosen}
        for entry in entries:
            if len(chosen) >= 5:
                break
            if entry["uid"] not in seen:
                chosen.append(
                    {"uid": entry["uid"], "version": entry["version"], "scheduled": False}
                )
    return chosen
