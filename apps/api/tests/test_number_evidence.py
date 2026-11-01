import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.learning import economy_service
from app.learning.grading import choice_letter
from tests import test_content as content_fixtures
from tests.test_auth import client_for
from tests.test_learning import login_child, now, post, prepare


@pytest.fixture
def source_tree(tmp_path):
    root = content_fixtures.source_tree.__wrapped__(tmp_path)
    original = (
        Path(__file__).resolve().parents[3]
        / "apps/web/public/data/books/g1up/lessons/g1up-u1-kp1.json"
    )
    source = root / "apps/web/public/data/books/g1up/lessons/g1up-u1-kp1.json"
    raw = json.loads(source.read_text())
    raw["questions"] = json.loads(original.read_text())["questions"]
    source.write_text(json.dumps(raw))
    return root


async def finish_all(client, session, questions, hint_one=False):
    requested = False
    while session["question"]:
        public = session["question"]
        original = questions[public["id"]]
        if public["numberTask"]:
            assert public["numberTask"]["hints"] == []
        if (
            hint_one
            and not requested
            and (public["numberTask"] or {}).get("stage") == "independent"
        ):
            response = await post(
                client,
                f"/learning-sessions/{session['id']}/hint",
                {"revision": session["revision"], "client_at": now()},
            )
            assert response.status_code == 200, response.text
            session = response.json()
            requested = True
            assert len(session["question"]["numberTask"]["hints"]) == 1
        answer = choice_letter(original) if original["type"] == "choice" else original["answer"]
        checked = await post(
            client,
            f"/learning-sessions/{session['id']}/attempts",
            {
                "revision": session["revision"],
                "client_at": now(),
                "question_uid": public["uid"],
                "question_version": public["version"],
                "answer": answer,
                "hint_level": 0,
            },
        )
        assert checked.status_code == 200, checked.text
        assert checked.json()["feedback"]["correct"]
        advanced = await post(
            client,
            f"/learning-sessions/{session['id']}/advance",
            {"revision": checked.json()["revision"], "client_at": now()},
        )
        assert advanced.status_code == 200, advanced.text
        session = advanced.json()
    return session


@pytest.mark.asyncio
async def test_hint_evidence_and_next_day_review_are_server_derived(
    auth_app, source_tree, monkeypatch
):
    current = [datetime(2026, 11, 4, 4, tzinfo=UTC)]
    monkeypatch.setattr(economy_service, "now_utc", lambda: current[0])
    first, _ = await prepare(auth_app, source_tree)
    raw = json.loads(
        (source_tree / "apps/web/public/data/books/g1up/lessons/g1up-u1-kp1.json").read_text()
    )
    questions = {q["id"]: q for q in raw["questions"]}
    async with client_for(auth_app) as a, client_for(auth_app) as b:
        await login_child(a)
        await login_child(b)
        path = f"/students/{first}/learning-sessions"
        response = await post(
            a,
            path,
            {"kind": "lesson", "book_id": "g1up", "source_id": "g1up-u1-kp1", "client_at": now()},
        )
        assert response.status_code == 200, response.text
        session = await finish_all(a, response.json(), questions, True)
        completed = await post(
            a,
            f"/learning-sessions/{session['id']}/complete",
            {"revision": session["revision"], "client_at": now()},
        )
        assert completed.status_code == 200, completed.text
        evidence = completed.json()["number_evidence"]
        independent = [q for q in raw["questions"] if q["numberTask"]["stage"] == "independent"]
        transfer = [q for q in raw["questions"] if q["numberTask"]["stage"] == "transfer"]
        assert evidence["independentTotal"] == len(independent)
        assert evidence["independentCorrect"] == len(independent) - 1
        assert evidence["transferCorrect"] == len(transfer)
        assert evidence["hintsUsed"] == 1
        assert (
            await post(
                a, path, {"kind": "number_review", "number_skill": "count", "client_at": now()}
            )
        ).status_code == 409
        current[0] += timedelta(days=1)
        starts = []
        banks = json.loads(
            (source_tree / "apps/api/private-content/number-review.json").read_text()
        )["banks"]
        for client in [a, b]:
            started = await post(
                client, path, {"kind": "number_review", "number_skill": "count", "client_at": now()}
            )
            assert started.status_code == 200, started.text
            session = started.json()
            variant = session["source_id"].split("-")[-1]
            bank = next(
                bank for bank in banks if bank["skill"] == "count" and bank["variant"] == variant
            )
            starts.append(
                await finish_all(client, session, {q["id"]: q for q in bank["questions"]})
            )
        results = await asyncio.gather(
            *[
                post(
                    client,
                    f"/learning-sessions/{session['id']}/complete",
                    {"revision": session["revision"], "client_at": now()},
                )
                for client, session in zip([a, b], starts, strict=True)
            ]
        )
        assert all(result.status_code == 200 for result in results), [
            result.text for result in results
        ]
        assert sum(result.json()["number_review_eligible"] for result in results) == 1
        assert sorted(result.json()["xp_gained"] for result in results) == [0, 10]
        summary = (await a.get(f"/api/v1/students/{first}/summary")).json()
        assert summary["projection_matches"]
        entry = summary["state"]["numberSenseProgress"]["count"]
        assert entry["verifiedOn"] == "2026-11-05" and entry["nextReviewOn"] == "2026-11-12"
        assert entry["evidence"] == evidence
