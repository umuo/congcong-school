import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.learning import economy_service
from app.learning.models import Attempt, RewardClaim, RewardLedger
from tests import test_content as content_fixtures
from tests.test_auth import ACCOUNT, client_for
from tests.test_child_mode import csrf
from tests.test_learning import login_child, now, post, prepare


@pytest.fixture
def source_tree(tmp_path):
    root = content_fixtures.source_tree.__wrapped__(tmp_path)
    prefix = root / "apps/web/public/data/books/g1up"
    for source in ["g1up-u1-kp1", "g1up-u2-kp1"]:
        path = prefix / "lessons" / f"{source}.json"
        raw = json.loads(path.read_text())
        raw["questions"] = [content_fixtures.question(i + 1) for i in range(3)]
        path.write_text(json.dumps(raw))
    return root


async def finish_questions(client, session):
    while session["question"]:
        q = session["question"]
        response = await post(
            client,
            f"/learning-sessions/{session['id']}/attempts",
            {
                "revision": session["revision"],
                "client_at": now(),
                "question_uid": q["uid"],
                "question_version": q["version"],
                "answer": "1/2",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["feedback"]["correct"]
        response = await post(
            client,
            f"/learning-sessions/{session['id']}/advance",
            {
                "revision": response.json()["revision"],
                "client_at": now(),
            },
        )
        assert response.status_code == 200, response.text
        session = response.json()
    return session


@pytest.mark.asyncio
async def test_concurrent_first_rewards_retries_and_goal_changes(
    auth_app, source_tree, monkeypatch
):
    monkeypatch.setattr(economy_service, "now_utc", lambda: datetime(2026, 11, 4, 4, tzinfo=UTC))
    first, _ = await prepare(auth_app, source_tree)
    async with client_for(auth_app) as a, client_for(auth_app) as b:
        await login_child(a)
        await login_child(b)
        starts = []
        for client in [a, b]:
            response = await post(
                client,
                f"/students/{first}/learning-sessions",
                {
                    "kind": "lesson",
                    "book_id": "g1up",
                    "source_id": "g1up-u1-kp1",
                    "client_at": now(),
                },
            )
            assert response.status_code == 200, response.text
            starts.append(await finish_questions(client, response.json()))
        keys = [uuid4(), uuid4()]
        bodies = [{"revision": s["revision"], "client_at": now()} for s in starts]
        results = await asyncio.gather(
            *[
                post(client, f"/learning-sessions/{s['id']}/complete", body, key)
                for client, s, body, key in zip([a, b], starts, bodies, keys, strict=True)
            ]
        )
        assert all(r.status_code == 200 for r in results), [r.text for r in results]
        assert sum(r.json()["first_perfect"] for r in results) == 1
        assert sorted(r.json()["xp_gained"] for r in results) == [35, 40]
        response = await post(
            a, f"/learning-sessions/{starts[0]['id']}/complete", bodies[0], keys[0]
        )
        assert response.json() == results[0].json()
        assert (
            await post(a, f"/learning-sessions/{starts[0]['id']}/complete", bodies[0])
        ).json() == results[0].json()
        progress = (await a.get(f"/api/v1/students/{first}/progress")).json()
        assert progress["state"]["xp"] == 75
        assert progress["state"]["gems"] == 101
        assert len(progress["state"]["perfectedLessons"]) == 1
        assert progress["state"]["completedLessons"]["g1up-u1-kp1"]["stars"] == 3
        path = f"/students/{first}/economy/actions"
        changed = await post(
            a,
            path,
            {
                "kind": "set_daily_goal",
                "daily_goal": 100,
                "revision": progress["revision"],
                "client_at": now(),
            },
        )
        assert changed.status_code == 200, changed.text
        assert (
            await post(
                b,
                path,
                {
                    "kind": "set_daily_goal",
                    "daily_goal": 200,
                    "revision": progress["revision"],
                    "client_at": now(),
                },
            )
        ).status_code == 409
        response = await post(
            a,
            f"/students/{first}/learning-sessions",
            {"kind": "lesson", "book_id": "g1up", "source_id": "g1up-u1-kp1", "client_at": now()},
        )
        third = await finish_questions(a, response.json())
        settled = await post(
            a,
            f"/learning-sessions/{third['id']}/complete",
            {"revision": third["revision"], "client_at": now()},
        )
        assert settled.status_code == 200, settled.text
        # 更改每日目标后再次跨线，不重复发当日目标宝石。
        assert settled.json()["gems_gained"] == 33  # 13 课程宝石 + 20 XP-100 成就
        async with auth_app.state.database.sessions() as db:
            claims = (
                await db.scalars(select(RewardClaim.key).where(RewardClaim.student_id == first))
            ).all()
            assert claims.count("first-perfect:g1up-u1-kp1") == 1
            assert claims.count("goal:2026-11-04") == 1
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(RewardLedger)
                    .where(RewardLedger.claim_key.like("session:%"))
                )
                == 3
            )


@pytest.mark.asyncio
async def test_daily_reward_shop_balances_and_insufficient_funds(
    auth_app, source_tree, monkeypatch
):
    monkeypatch.setattr(economy_service, "now_utc", lambda: datetime(2026, 11, 4, 4, tzinfo=UTC))
    first, _ = await prepare(auth_app, source_tree)
    async with client_for(auth_app) as a, client_for(auth_app) as b:
        await login_child(a)
        await b.post("/api/v1/auth/login", json=ACCOUNT)
        csrf(b)
        await b.post("/api/v1/mode/child", json={"student_id": str(first)})
        csrf(b)
        path = f"/students/{first}/economy/actions"
        body = {"kind": "daily_reward", "client_at": now()}
        key = uuid4()
        results = await asyncio.gather(post(a, path, body, key), post(b, path, body, key))
        assert results[0].status_code == results[1].status_code == 200
        assert results[0].json() == results[1].json()
        assert results[0].json()["progress"]["state"]["gems"] == 5
        assert (await post(a, path, {**body, "kind": "buy_freeze"}, key)).status_code == 409
        assert (
            await post(
                a,
                path,
                {"kind": "purchase_cosmetic", "item_id": "skin_graduate", "client_at": now()},
            )
        ).status_code == 409
        assert (
            await post(a, path, {"kind": "daily_reward", "gems": 500, "client_at": now()})
        ).status_code == 422
        # 仅测试夹具通过私有服务记入资金，生产 API 没有任意加余额入口。
        async with auth_app.state.database.sessions() as db:
            from app.students.models import Student

            student = await db.get(Student, first)
            row, state = await economy_service.load_state(db, student)
            state["gems"] += 500
            state["lifetimeGems"] += 500
            await economy_service.save_state(
                db, student, row, state, "fixture-fund", {"fixture": True}, datetime.now(UTC)
            )
            await db.commit()
        results = await asyncio.gather(
            *[
                post(
                    client, path, {"kind": "purchase_cosmetic", "item_id": item, "client_at": now()}
                )
                for client, item in [(a, "skin_graduate"), (b, "skin_glasses")]
            ]
        )
        assert all(r.status_code == 200 for r in results), [r.text for r in results]
        progress = (await a.get(f"/api/v1/students/{first}/progress")).json()["state"]
        assert progress["gems"] == 395  # 505 - 80 - 100 + 首件20 + 累计宝石50
        assert (
            progress["ownedCosmetics"]["skin_graduate"]
            and progress["ownedCosmetics"]["skin_glasses"]
        )
        assert (
            await post(
                a,
                path,
                {"kind": "purchase_cosmetic", "item_id": "skin_graduate", "client_at": now()},
            )
        ).status_code == 409
        async with auth_app.state.database.sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(RewardClaim)
                    .where(RewardClaim.key == "daily:2026-11-04")
                )
                == 1
            )


@pytest.mark.asyncio
async def test_hearts_gate_regeneration_and_daily_review_cap(auth_app, source_tree, monkeypatch):
    from datetime import timedelta

    current = [datetime(2026, 11, 4, 4, tzinfo=UTC)]
    monkeypatch.setattr(economy_service, "now_utc", lambda: current[0])
    first, _ = await prepare(auth_app, source_tree)
    async with client_for(auth_app) as client:
        await login_child(client)
        response = await post(
            client,
            f"/students/{first}/learning-sessions",
            {
                "kind": "lesson",
                "book_id": "g1up",
                "source_id": "g1up-u2-kp1",
                "client_at": now(),
            },
        )
        assert response.status_code == 200, response.text
        session = response.json()
        for _ in range(5):
            q = session["question"]
            key = uuid4()
            body = {
                "revision": session["revision"],
                "client_at": now(),
                "question_uid": q["uid"],
                "question_version": q["version"],
                "answer": "0",
            }
            checked = await post(client, f"/learning-sessions/{session['id']}/attempts", body, key)
            assert checked.status_code == 200, checked.text
            assert not checked.json()["feedback"]["correct"]
            assert (
                await post(client, f"/learning-sessions/{session['id']}/attempts", body, key)
            ).json() == checked.json()
            response = await post(
                client,
                f"/learning-sessions/{session['id']}/advance",
                {"revision": checked.json()["revision"], "client_at": now()},
            )
            assert response.status_code == 200, response.text
            session = response.json()
        progress = (await client.get(f"/api/v1/students/{first}/progress")).json()
        assert progress["state"]["hearts"] == 0
        q = session["question"]
        blocked = await post(
            client,
            f"/learning-sessions/{session['id']}/attempts",
            {
                "revision": session["revision"],
                "client_at": now(),
                "question_uid": q["uid"],
                "question_version": q["version"],
                "answer": "1/2",
            },
        )
        assert blocked.status_code == 409 and blocked.json()["code"] == "HEARTS_REQUIRED"
        for expected in [1, 0]:
            started = await post(
                client,
                f"/students/{first}/learning-sessions",
                {"kind": "review", "for_hearts": True, "client_at": now()},
            )
            assert started.status_code == 200, started.text
            review = await finish_questions(client, started.json())
            result = await post(
                client,
                f"/learning-sessions/{review['id']}/complete",
                {"revision": review["revision"], "client_at": now()},
            )
            assert result.status_code == 200, result.text
            assert result.json()["hearts_gained"] == expected
        current[0] += timedelta(seconds=300)
        progress = (await client.get(f"/api/v1/students/{first}/progress")).json()
        assert progress["state"]["hearts"] == 2
        async with auth_app.state.database.sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(Attempt)
                    .where(Attempt.session_id == UUID(session["id"]))
                )
                == 5
            )
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(RewardClaim)
                    .where(RewardClaim.key == "review-heart:2026-11-04")
                )
                == 1
            )


@pytest.mark.asyncio
async def test_chest_and_quest_claims_are_unique_and_projection_rebuilds(
    auth_app, source_tree, monkeypatch
):
    import copy

    from sqlalchemy import update
    from sqlalchemy.exc import IntegrityError

    from app.curriculum.models import Textbook
    from app.students.models import Student

    current = datetime(2026, 11, 4, 4, tzinfo=UTC)
    monkeypatch.setattr(economy_service, "now_utc", lambda: current)
    prefix = source_tree / "apps/web/public/data/books/g1up"
    template = json.loads((prefix / "lessons/g1up-u1-kp1.json").read_text())
    outline = json.loads((prefix / "outline.json").read_text())
    lessons = [{"id": f"g1up-u1-kp{i}", "title": f"课程{i}"} for i in range(1, 6)]
    for lesson in lessons[1:]:
        raw = copy.deepcopy(template)
        raw["id"] = lesson["id"]
        (prefix / "lessons" / f"{lesson['id']}.json").write_text(json.dumps(raw))
    outline["lessons"] = [*lessons, {"id": "g1up-u2-kp1"}]
    (prefix / "outline.json").write_text(json.dumps(outline))
    first, _ = await prepare(auth_app, source_tree)
    async with auth_app.state.database.sessions() as db:
        await db.execute(
            update(Textbook)
            .where(Textbook.id == "g1up")
            .values(units=[{"number": 1, "title": "单元一", "lessons": lessons}])
        )
        student = await db.get(Student, first)
        row, state = await economy_service.load_state(db, student)
        state.update(
            xp=100,
            todayXp=100,
            lastXpDate="2026-11-04",
            dailyQuestDate="2026-11-04",
            dailyLessons=5,
            dailyReadings=2,
        )
        state["completedLessons"] = {
            lesson["id"]: {
                "lessonId": lesson["id"],
                "stars": 1,
                "accuracy": 0.8,
                "completedAt": current.isoformat(),
            }
            for lesson in lessons
        }
        await economy_service.save_state(
            db, student, row, state, "fixture-progress", {"fixture": True}, current
        )
        await db.commit()
    async with client_for(auth_app) as a, client_for(auth_app) as b:
        await login_child(a)
        await login_child(b)
        path = f"/students/{first}/economy/actions"
        body = {
            "kind": "chest",
            "book_id": "g1up",
            "chest_id": "g1up-u1-chest-0",
            "client_at": now(),
        }
        responses = await asyncio.gather(post(a, path, body), post(b, path, body))
        assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
        assert sum(r.json()["result"]["applied"] for r in responses) == 1
        awarded = next(
            r.json()["result"]["chest"]["gems"] for r in responses if r.json()["result"]["chest"]
        )
        assert 10 <= awarded <= 50
        progress = (await a.get(f"/api/v1/students/{first}/progress")).json()
        assert progress["state"]["gems"] == awarded + 40
        quest = progress["quests"][0]
        body = {"kind": "quest", "quest_id": quest["id"], "client_at": now()}
        responses = await asyncio.gather(post(a, path, body), post(b, path, body))
        assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
        assert sum(r.json()["result"]["applied"] for r in responses) == 1
        summary = (await a.get(f"/api/v1/students/{first}/summary")).json()
        assert (
            summary["projection_matches"]
            and summary["state"]["gems"] == awarded + 40 + quest["reward"]
        )
        async with auth_app.state.database.sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(RewardClaim)
                    .where(RewardClaim.key == "chest:g1up-u1-chest-0")
                )
                == 1
            )
            with pytest.raises(IntegrityError):
                await db.execute(update(RewardLedger).values(gems_delta=9999))
                await db.commit()
            await db.rollback()
