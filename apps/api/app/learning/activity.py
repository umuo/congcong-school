"""追加申报用时检查点；不把客户端用时兑换为奖励或专注度。"""

from datetime import UTC, datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.content.import_content import digest
from app.errors import APIError
from app.learning import economy as rules
from app.learning.economy_service import apply_changes, clock
from app.learning.models import LearningEvent, LearningReceipt, LearningSession
from app.learning.transactions import append_event, receipt, save_receipt


async def submit_time(db, student, body, key):
    old, request_hash = await receipt(db, student.id, "events", key, body)
    if old is not None:
        return old
    session = await db.scalar(
        select(LearningSession).where(
            LearningSession.id == body.session_id, LearningSession.student_id == student.id
        )
    )
    if session is None:
        raise APIError(404, "LEARNING_SESSION_NOT_FOUND", "找不到学习会话")
    binding = await db.get(LearningReceipt, (student.id, "activity-bind", body.activity_id))
    binding_hash = digest({"session_id": str(body.session_id)})
    if binding is not None and binding.request_hash != binding_hash:
        raise APIError(409, "ACTIVITY_CONTEXT_CONFLICT", "同一计时活动不能更换学习会话")
    operation = f"time:{body.activity_id}"
    sequence_key = uuid5(NAMESPACE_URL, f"checkpoint:{body.sequence}")
    logical, _ = await receipt(db, student.id, operation, sequence_key, body)
    if logical is not None:
        return await save_receipt(db, student.id, "events", key, request_hash, logical)
    now, _ = await clock(db, student)
    start, end = body.started_at.astimezone(UTC), body.ended_at.astimezone(UTC)
    if start < session.created_at - timedelta(minutes=5) or end > now + timedelta(minutes=5):
        raise APIError(422, "INVALID_ACTIVITY_TIME", "申报时间超出学习会话或服务器允许的时钟偏差")
    if session.status == "completed":
        events = (
            await db.scalars(
                select(LearningEvent).where(
                    LearningEvent.student_id == student.id,
                    LearningEvent.kind == "session_completed",
                )
            )
        ).all()
        completed = next(
            (event for event in events if event.payload.get("session_id") == str(session.id)), None
        )
        if completed is None or end > completed.received_at + timedelta(minutes=5):
            raise APIError(409, "ACTIVITY_CLOSED", "学习会话已结束，不能继续追加新时长")
    payload = {
        "session_id": str(session.id),
        "activity_id": str(body.activity_id),
        "sequence": body.sequence,
        "started_at": start.isoformat(),
        "ended_at": end.isoformat(),
        "declared_duration_ms": int((end - start).total_seconds() * 1000),
    }
    cursor = await append_event(db, student, "time_checkpoint", payload, body.client_at)
    response = {
        "student_id": str(student.id),
        "cursor": cursor,
        "accepted_duration_ms": payload["declared_duration_ms"],
        "time_basis": "client_declared_interval",
    }
    if binding is None:
        db.add(
            LearningReceipt(
                student_id=student.id,
                operation="activity-bind",
                key=body.activity_id,
                request_hash=binding_hash,
                response={"session_id": str(session.id)},
            )
        )
    db.add(
        LearningReceipt(
            student_id=student.id,
            operation=operation,
            key=sequence_key,
            request_hash=request_hash,
            response=response,
        )
    )
    return await save_receipt(db, student.id, "events", key, request_hash, response)


def merged_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged


def time_by_day(intervals, timezone):
    zone = ZoneInfo(timezone)
    daily = {}
    for start, end in merged_intervals(intervals):
        current = start
        while current < end:
            local = current.astimezone(zone)
            day = local.date()
            midnight = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone).astimezone(
                UTC
            )
            stop = min(end, midnight)
            daily[day.isoformat()] = daily.get(day.isoformat(), 0) + int(
                (stop - current).total_seconds() * 1000
            )
            current = stop
    return daily


def rebuild(events, timezone, today):
    projection_revision = 1
    state = rules.initial_state()
    intervals = []
    daily = {}
    stories = {}
    unique_readings = set()
    cursor = 0
    for event in events:
        cursor = event.cursor
        payload = event.payload
        if event.kind == "economy_changed":
            projection_revision += 1
            if payload["rule_version"] != rules.VERSION:
                raise APIError(409, "ECONOMY_VERSION_UNAVAILABLE", "该记录的经济规则版本暂不可用")
            apply_changes(state, payload["changes"])
        elif event.kind == "time_checkpoint":
            intervals.append(
                (
                    datetime.fromisoformat(payload["started_at"]).astimezone(UTC),
                    datetime.fromisoformat(payload["ended_at"]).astimezone(UTC),
                )
            )
        elif event.kind == "session_completed":
            day = (
                payload.get("study_day")
                or event.received_at.astimezone(ZoneInfo(timezone)).date().isoformat()
            )
            entry = daily.setdefault(
                day,
                {
                    "lesson_completions": 0,
                    "reading_completions": 0,
                    "story_completions": 0,
                    "attempts": 0,
                },
            )
            if payload["kind"] in {"lesson", "challenge"}:
                entry["lesson_completions"] += 1
            elif payload["kind"] == "story":
                entry["story_completions"] += 1
                raw = f"{payload['book_id']}:{payload['source_id']}"
                old = stories.get(raw, {})
                stories[raw] = {
                    "book_id": payload["book_id"],
                    "source_id": payload["source_id"],
                    "best_accuracy": max(payload["accuracy"], old.get("best_accuracy", 0)),
                    "latest_accuracy": payload["accuracy"],
                    "last_completed_day": day,
                    "completion_count": old.get("completion_count", 0) + 1,
                }
                unique_readings.add(f"story:{raw}")
            elif payload["kind"] == "reading":
                entry["reading_completions"] += 1
                unique_readings.add(
                    f"{payload['reading_kind']}:{payload['book_id']}:{payload['source_id']}"
                )
        elif event.kind == "answer_submitted":
            day = event.received_at.astimezone(ZoneInfo(timezone)).date().isoformat()
            entry = daily.setdefault(
                day,
                {
                    "lesson_completions": 0,
                    "reading_completions": 0,
                    "story_completions": 0,
                    "attempts": 0,
                },
            )
            entry["attempts"] += 1
    declared = time_by_day(intervals, timezone)
    for day, value in declared.items():
        entry = daily.setdefault(
            day,
            {
                "lesson_completions": 0,
                "reading_completions": 0,
                "story_completions": 0,
                "attempts": 0,
            },
        )
        entry["declared_time_ms"] = value
    for entry in daily.values():
        entry.setdefault("declared_time_ms", 0)
    monday = today - timedelta(days=today.weekday())
    week_time = sum(
        value
        for day, value in declared.items()
        if monday.isoformat() <= day <= (monday + timedelta(days=6)).isoformat()
    )
    return {
        "cursor": cursor,
        "projection_revision": projection_revision,
        "timezone": timezone,
        "state": state,
        "daily": daily,
        "stories": list(stories.values()),
        "unique_readings": len(unique_readings),
        "declared_time_ms": sum(declared.values()),
        "week": {"starts_on": monday.isoformat(), "declared_time_ms": week_time},
        "time_basis": "client_declared_intervals_merged",
        "attention_measured": False,
    }
