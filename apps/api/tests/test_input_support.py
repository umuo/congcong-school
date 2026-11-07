import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.learning.input_support import keyboard
from app.learning.models import Attempt, LearningEvent, RewardLedger
from tests import test_content as content_fixtures
from tests.test_auth import client_for
from tests.test_content import write
from tests.test_learning import login_child, now, post, prepare


@pytest.fixture
def source_tree(tmp_path):
    return content_fixtures.source_tree.__wrapped__(tmp_path)


def test_keyboard_matches_original_shared_vectors():
    cases = json.loads((Path(__file__).parent / "fixtures/keyboard-vectors.json").read_text())
    for case in cases:
        result = keyboard(case)
        assert result["candidates"] == case["candidates"]
        assert set(result) == {"candidates", "language", "max_length"}


@pytest.mark.parametrize("answer", ["I'm Tom.", "Hello!", "What's your name?"])
def test_english_sentence_keyboard_uses_letters(answer):
    result = keyboard({"answer": answer, "id": 77})
    assert result["language"] == "letters"
    assert all(char.isascii() and not char.isspace() for char in result["candidates"])
    needed = {char for char in answer.lower() if char.isalpha()}
    assert needed <= set(result["candidates"])


@pytest.mark.asyncio
async def test_pair_feedback_is_scoped_idempotent_and_not_a_whole_attempt(auth_app, source_tree):
    path = source_tree / "apps/web/public/data/books/g1up/lessons/g1up-u1-kp1.json"
    lesson = json.loads(path.read_text())
    lesson["questions"] = [
        {
            "id": 1,
            "type": "matching",
            "question": "配对",
            "options": ["一", "二", "三", "四", "1", "2", "3", "4"],
            "answer": "A-1,B-2,C-3,D-4",
            "explanation": "配对解释",
        },
        {"id": 2, "type": "fill_blank_text", "question": "太阳", "options": [], "answer": "太阳"},
    ]
    write(source_tree, path.relative_to(source_tree), lesson)
    students = await prepare(auth_app, source_tree)
    async with client_for(auth_app) as client, client_for(auth_app) as sibling:
        await login_child(client)
        await login_child(sibling, 1)
        session = (
            await post(
                client,
                f"/students/{students[0]}/learning-sessions",
                {
                    "kind": "lesson",
                    "book_id": "g1up",
                    "source_id": "g1up-u1-kp1",
                    "client_at": now(),
                },
            )
        ).json()
        endpoint = f"/learning-sessions/{session['id']}/matching-pairs"
        body = {
            "revision": session["revision"],
            "client_at": now(),
            "question_uid": session["question"]["uid"],
            "question_version": session["question"]["version"],
            "left": "A",
            "right": "2",
        }
        assert (await post(sibling, endpoint, body)).status_code == 404
        wrong = await post(client, endpoint, body)
        assert wrong.status_code == 200, wrong.text
        assert wrong.json()["correct"] is False
        session = wrong.json()["session"]
        assert not session["checkpoint"].get("matching_pairs")
        assert session["feedback"] is None
        assert (await post(client, endpoint, body)).status_code == 409
        body.update(revision=session["revision"], right="1")
        key = uuid4()
        correct = await post(client, endpoint, body, key)
        assert correct.status_code == 200, correct.text
        assert correct.json()["correct"] is True
        assert (await post(client, endpoint, body, key)).json() == correct.json()
        assert (await post(client, endpoint, {**body, "right": "3"}, key)).status_code == 409
        session = correct.json()["session"]
        assert session["checkpoint"]["matching_pairs"] == {"A": "1"}
        assert session["checkpoint"]["draft"]["answer"] == "A-1"
        restored = (await client.get(f"/api/v1/learning-sessions/{session['id']}")).json()
        assert restored["checkpoint"]["matching_pairs"] == {"A": "1"}
        assert "answer" not in restored["question"]
        forged = {**body, "revision": session["revision"], "question_uid": "f" * 64}
        assert (await post(client, endpoint, forged)).status_code == 409
        async with auth_app.state.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Attempt)) == 0
            assert await db.scalar(select(func.count()).select_from(RewardLedger)) == 0
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(LearningEvent)
                    .where(LearningEvent.kind == "matching_pair_checked")
                )
                == 2
            )
        attempt = await post(
            client,
            f"/learning-sessions/{session['id']}/attempts",
            {
                "revision": session["revision"],
                "client_at": now(),
                "question_uid": body["question_uid"],
                "question_version": body["question_version"],
                "answer": "A-1,B-2,C-3,D-4",
            },
        )
        assert attempt.status_code == 200, attempt.text
        assert (
            await post(client, endpoint, {**body, "revision": attempt.json()["revision"]})
        ).status_code == 409
        next_question = await post(
            client,
            f"/learning-sessions/{session['id']}/advance",
            {
                "revision": attempt.json()["revision"],
                "client_at": now(),
            },
        )
        assert next_question.status_code == 200, next_question.text
        public = next_question.json()["question"]
        assert public["input_keyboard"] == keyboard({"answer": "太阳", "id": 2})
        assert "answer" not in public and "explanation" not in public
        assert next_question.json()["checkpoint"]["matching_pairs"] == {}


@pytest.mark.asyncio
async def test_session_media_blocks_early_explanation_traversal_and_sibling(auth_app, source_tree):
    auth_app.state.settings.content_root = source_tree
    public = source_tree / "apps/web/public/audio"
    public.mkdir(parents=True)
    (public / "prompt.mp3").write_bytes(b"prompt-audio")
    (public / "secret-explanation.mp3").write_bytes(b"explanation-audio")
    students = await prepare(auth_app, source_tree)
    async with client_for(auth_app) as client, client_for(auth_app) as sibling:
        await login_child(client)
        await login_child(sibling, 1)
        session = (
            await post(
                client,
                f"/students/{students[0]}/learning-sessions",
                {
                    "kind": "lesson",
                    "book_id": "g1up",
                    "source_id": "g1up-u1-kp1",
                    "client_at": now(),
                },
            )
        ).json()
        endpoint = f"/api/v1/learning-sessions/{session['id']}/media"
        assert (
            await client.get(endpoint, params={"path": "/audio/prompt.mp3"})
        ).content == b"prompt-audio"
        assert (
            await client.get(endpoint, params={"path": "/audio/secret-explanation.mp3"})
        ).status_code == 404
        assert (
            await sibling.get(endpoint, params={"path": "/audio/prompt.mp3"})
        ).status_code == 404
        assert (await client.get(endpoint, params={"path": "/audio/../../.env"})).status_code == 404
        answered = await post(
            client,
            f"/learning-sessions/{session['id']}/attempts",
            {
                "revision": session["revision"],
                "client_at": now(),
                "question_uid": session["question"]["uid"],
                "question_version": session["question"]["version"],
                "answer": "1/2",
            },
        )
        assert answered.status_code == 200, answered.text
        response = await client.get(endpoint, params={"path": "/audio/secret-explanation.mp3"})
        assert response.content == b"explanation-audio"
        assert response.headers["cache-control"] == "no-store"
