from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.learning import economy as rules
from app.learning.activity import rebuild, time_by_day
from app.learning.economy_service import state_changes


def at(value):
    return datetime.fromisoformat(value).astimezone(UTC)


def test_overlap_midnight_and_monday_week_boundary():
    intervals = [
        (at("2026-11-01T15:50:00+00:00"), at("2026-11-01T16:10:00+00:00")),
        (at("2026-11-01T15:55:00+00:00"), at("2026-11-01T16:15:00+00:00")),
    ]
    daily = time_by_day(intervals, "Asia/Shanghai")
    assert daily == {"2026-11-01": 600000, "2026-11-02": 900000}
    events = [
        SimpleNamespace(
            kind="time_checkpoint",
            cursor=i + 1,
            payload={"started_at": s.isoformat(), "ended_at": e.isoformat()},
        )
        for i, (s, e) in enumerate(intervals)
    ]
    summary = rebuild(events, "Asia/Shanghai", date(2026, 11, 2))
    assert summary["declared_time_ms"] == 1500000
    assert summary["week"] == {"starts_on": "2026-11-02", "declared_time_ms": 900000}
    assert not summary["attention_measured"]


def test_daylight_saving_repeated_hour_uses_elapsed_time():
    daily = time_by_day(
        [(at("2026-11-01T05:30:00+00:00"), at("2026-11-01T06:30:00+00:00"))], "America/New_York"
    )
    assert daily == {"2026-11-01": 3600000}


def test_projection_rebuild_and_repeated_reading_counts_are_distinct():
    state = rules.initial_state()
    updated = rules.initial_state()
    updated["xp"] = 5
    updated["completedReadings"]["reading:listen:p1"] = "2026-11-01"
    events = []
    for _ in range(2):
        events.append(
            SimpleNamespace(
                kind="session_completed",
                cursor=len(events) + 1,
                received_at=at("2026-11-01T02:00:00+00:00"),
                payload={
                    "kind": "reading",
                    "book_id": "book",
                    "source_id": "p1",
                    "reading_kind": "listen",
                    "study_day": "2026-11-01",
                },
            )
        )
    events.append(
        SimpleNamespace(
            kind="economy_changed",
            cursor=3,
            payload={"rule_version": rules.VERSION, "changes": state_changes(state, updated)},
        )
    )
    summary = rebuild(events, "Asia/Shanghai", date(2026, 11, 1))
    assert summary["state"] == updated
    assert summary["projection_revision"] == 2
    assert summary["unique_readings"] == 1
    assert summary["daily"]["2026-11-01"]["reading_completions"] == 2
