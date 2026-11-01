from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.learning.models import LearningEvent
from tests import test_content as content_fixtures
from tests.test_auth import client_for
from tests.test_learning import login_child, now, post, prepare


@pytest.fixture
def source_tree(tmp_path):
    return content_fixtures.source_tree.__wrapped__(tmp_path)


async def start(client, student, kind, source, **fields):
    response = await post(
        client,
        f"/students/{student}/learning-sessions",
        {
            "kind": kind,
            "book_id": "g1up",
            "source_id": source,
            "client_at": now(),
            **fields,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def finish(client, session):
    response = await post(
        client,
        f"/learning-sessions/{session['id']}/complete",
        {"revision": session["revision"], "client_at": now()},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_reading_story_duplicates_time_dedup_and_projection_rebuild(auth_app, source_tree):
    first, second = await prepare(auth_app, source_tree)
    async with client_for(auth_app) as a, client_for(auth_app) as b:
        await login_child(a)
        await login_child(b)
        reading = await start(a, first, "reading", "g1up-p1", reading_kind="listen")
        assert reading["question"] is None
        duplicate = await start(b, first, "reading", "g1up-p1", reading_kind="listen")
        instant = datetime.now(UTC)
        activity = uuid4()
        body = {
            "kind": "time_checkpoint",
            "session_id": reading["id"],
            "activity_id": str(activity),
            "sequence": 1,
            "client_at": now(),
            "started_at": (instant - timedelta(seconds=30)).isoformat(),
            "ended_at": (instant + timedelta(seconds=30)).isoformat(),
        }
        path = f"/students/{first}/events"
        key = uuid4()
        response = await post(a, path, body, key)
        assert response.status_code == 200, response.text
        assert (await post(b, path, body, key)).json() == response.json()
        assert (await post(b, path, body)).json() == response.json()
        assert (
            await post(b, path, {**body, "ended_at": (instant + timedelta(seconds=31)).isoformat()})
        ).status_code == 409
        assert (await post(a, path, {**body, "session_id": duplicate["id"]})).status_code == 409
        overlap = {
            **body,
            "session_id": duplicate["id"],
            "activity_id": str(uuid4()),
            "started_at": instant.isoformat(),
            "ended_at": (instant + timedelta(seconds=60)).isoformat(),
        }
        assert (await post(b, path, overlap)).status_code == 200
        assert (await post(a, f"/students/{second}/events", body)).status_code == 404
        assert (
            await post(
                a,
                path,
                {**body, "sequence": 2, "ended_at": (instant + timedelta(hours=2)).isoformat()},
            )
        ).status_code == 422
        result = await finish(a, reading)
        assert result["xp_gained"] == 5
        result = await finish(b, duplicate)
        assert result["xp_gained"] == 0
        followup = await start(a, first, "reading", "g1up-p1", reading_kind="followup")
        assert (await finish(a, followup))["xp_gained"] == 10
        for answer in ["0", "1/2"]:
            story = await start(a, first, "story", "g1up-s1")
            q = story["question"]
            checked = await post(
                a,
                f"/learning-sessions/{story['id']}/attempts",
                {
                    "revision": story["revision"],
                    "client_at": now(),
                    "question_uid": q["uid"],
                    "question_version": q["version"],
                    "answer": answer,
                },
            )
            assert checked.status_code == 200, checked.text
            moved = await post(
                a,
                f"/learning-sessions/{story['id']}/advance",
                {"revision": checked.json()["revision"], "client_at": now()},
            )
            assert moved.status_code == 200, moved.text
            result = await finish(a, moved.json())
            assert result["xp_gained"] == (5 if answer == "0" else 0)
        summary = (await b.get(f"/api/v1/students/{first}/summary")).json()
        assert summary["projection_matches"] is True
        assert summary["state"]["xp"] == 20
        assert summary["declared_time_ms"] == 90000
        assert summary["unique_readings"] == 3
        assert summary["stories"][0]["best_accuracy"] == 1
        assert summary["stories"][0]["completion_count"] == 2
        assert sum(day["reading_completions"] for day in summary["daily"].values()) == 3
        assert sum(day["story_completions"] for day in summary["daily"].values()) == 2
        async with auth_app.state.database.sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(LearningEvent)
                    .where(LearningEvent.kind == "time_checkpoint")
                )
                == 2
            )
