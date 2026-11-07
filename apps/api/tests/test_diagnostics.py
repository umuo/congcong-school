import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.content.import_content import load_content
from app.diagnostics.catalog_builder import (
    MAPPING_VERSION,
    build_knowledge_catalog,
    sync_knowledge_catalog,
)
from app.diagnostics.engine import (
    DIAGNOSTIC_RULE_VERSION,
    AttemptEvidence,
    evaluate_knowledge_point,
)
from app.diagnostics.models import (
    KnowledgePoint,
    KnowledgePointRelation,
    QuestionKnowledgeLink,
)
from app.learning.models import Attempt, EconomyState, RewardLedger
from app.students.models import Student
from tests import test_content as content_fixtures
from tests.test_admin import init_admin, login_change
from tests.test_auth import client_for, provision_parent
from tests.test_child_mode import csrf
from tests.test_learning import login_child, now, post, prepare
from tests.test_portability import backup, parent_login

ROOT = Path(__file__).resolve().parents[3]
SECOND_ACCOUNT = {"email": "other-parent@example.com", "password": "Test-only-password-2026"}


@pytest.fixture
def source_tree(tmp_path):
    tree = content_fixtures.source_tree.__wrapped__(tmp_path)
    # 补充同书 restoresLessonId 与跨版同名知识点，验证受控关系构建。
    kp1_path = tree / "apps/web/public/data/books/g1up/lessons/g1up-u1-kp1.json"
    kp1 = json.loads(kp1_path.read_text())
    kp1["knowledge"] = {"point": "数一数，认一认", "core_concept": "按顺序点数"}
    kp1["restoresLessonId"] = "g1up-u2-kp1"
    kp1_path.write_text(json.dumps(kp1, ensure_ascii=False))

    kp1_2026_path = (
        tree / "apps/web/public/data/books/g1up-2026/lessons/g1up-2026-u1-kp1.json"
    )
    kp1_2026 = json.loads(kp1_2026_path.read_text())
    kp1_2026["knowledge"] = {"point": "数一数，认一认", "core_concept": "2026版点数"}
    kp1_2026_path.write_text(json.dumps(kp1_2026, ensure_ascii=False))

    idx_path = tree / "apps/web/public/data/index.json"
    idx = json.loads(idx_path.read_text())
    idx["books"][1]["supersedes"] = "g1up"
    idx_path.write_text(json.dumps(idx, ensure_ascii=False))
    return tree


def test_all_84_textbooks_catalog_and_question_mappings():
    content_batch = load_content(ROOT)
    kp_batch = build_knowledge_catalog(ROOT)

    books_with_kps = {kp["book_id"] for kp in kp_batch.knowledge_points.values()}
    subjects_with_kps = {kp["subject_code"] for kp in kp_batch.knowledge_points.values()}
    assert len(books_with_kps) == 84
    assert subjects_with_kps == {"math", "chinese", "english", "science"}

    all_question_versions = set(content_batch.versions.keys())
    linked_question_versions = {
        (link["question_uid"], link["question_version"])
        for link in kp_batch.question_links.values()
    }
    assert all_question_versions == linked_question_versions

    # 不同教材版本与不同学制保持各自独立知识点身份，不自动合并。
    g1up_kps = {
        kp["id"]
        for kp in kp_batch.knowledge_points.values()
        if kp["book_id"] == "g1up"
    }
    g1up_2026_kps = {
        kp["id"]
        for kp in kp_batch.knowledge_points.values()
        if kp["book_id"] == "g1up-2026"
    }
    g1up_54_kps = {
        kp["id"]
        for kp in kp_batch.knowledge_points.values()
        if kp["book_id"] == "g1up-54-qingdao"
    }
    assert g1up_kps and g1up_2026_kps and g1up_54_kps
    assert g1up_kps.isdisjoint(g1up_2026_kps)
    assert g1up_kps.isdisjoint(g1up_54_kps)

    rel_kinds = {r["relation_kind"] for r in kp_batch.relations.values()}
    assert "restores_lesson" in rel_kinds
    assert "supersedes_exact_title" in rel_kinds


def _make_attempt(
    *,
    idx: int,
    q_uid: str = "q-1",
    session_id: str = "s-1",
    correct: bool = True,
    first_attempt: bool = True,
    hint_level: int = 0,
    received_at: datetime | None = None,
) -> AttemptEvidence:
    ts = received_at or datetime(2026, 11, 1, 10, 0, tzinfo=UTC) + timedelta(minutes=idx)
    return AttemptEvidence(
        attempt_id=f"att-{idx}",
        session_id=session_id,
        session_kind="lesson",
        ordinal=idx,
        question_uid=q_uid,
        question_version="v-1",
        correct=correct,
        first_attempt=first_attempt,
        hint_level=hint_level,
        received_at=ts,
        client_at=ts,
        declared_duration_ms=4000,
    )


def test_diagnostic_engine_rules_and_edge_cases():
    # 1. 未练习 -> unassessed
    empty = evaluate_knowledge_point([], total_questions_available=5)
    assert empty["status"] == "unassessed"
    assert empty["diagnostic_rule_version"] == DIAGNOSTIC_RULE_VERSION

    # 2. 同会话首答错误 + 回炉订正答对 -> needs_review（不得虚增为 mastered）
    same_session_retry = evaluate_knowledge_point(
        [
            _make_attempt(idx=1, q_uid="q-1", session_id="s-1", correct=False, first_attempt=True),
            _make_attempt(idx=2, q_uid="q-1", session_id="s-1", correct=True, first_attempt=False),
        ],
        total_questions_available=4,
    )
    assert same_session_retry["status"] == "needs_review"
    assert same_session_retry["reason_code"] == "first_wrong_remediated_same_session"
    assert same_session_retry["first_attempts_correct"] == 0
    assert same_session_retry["retry_attempts_correct"] == 1

    # 3. 仅单次作答正确 -> insufficient_evidence
    single_ok = evaluate_knowledge_point(
        [_make_attempt(idx=1, q_uid="q-1", session_id="s-1", correct=True)],
        total_questions_available=4,
    )
    assert single_ok["status"] == "insufficient_evidence"
    assert single_ok["reason_code"] == "single_attempt_only"

    # 4. 单日反复重开会话刷同一道题 -> insufficient_evidence
    same_day_same_q = evaluate_knowledge_point(
        [
            _make_attempt(idx=1, q_uid="q-1", session_id="s-1", correct=True),
            _make_attempt(idx=2, q_uid="q-1", session_id="s-2", correct=True),
            _make_attempt(idx=3, q_uid="q-1", session_id="s-3", correct=True),
        ],
        total_questions_available=4,
    )
    assert same_day_same_q["status"] == "insufficient_evidence"
    assert same_day_same_q["reason_code"] == "single_question_same_day"

    # 5. 全部依赖提示才答对 -> insufficient_evidence
    hint_only = evaluate_knowledge_point(
        [
            _make_attempt(idx=1, q_uid="q-1", session_id="s-1", correct=True, hint_level=1),
            _make_attempt(idx=2, q_uid="q-2", session_id="s-1", correct=True, hint_level=2),
            _make_attempt(idx=3, q_uid="q-3", session_id="s-1", correct=True, hint_level=1),
        ],
        total_questions_available=4,
    )
    assert hint_only["status"] == "insufficient_evidence"
    assert hint_only["reason_code"] == "hint_dependent"

    # 6. 单日仅 2 道不同题正确 -> developing（等待更多题目或隔天验证）
    two_q_same_day = evaluate_knowledge_point(
        [
            _make_attempt(idx=1, q_uid="q-1", session_id="s-1", correct=True),
            _make_attempt(idx=2, q_uid="q-2", session_id="s-1", correct=True),
        ],
        total_questions_available=4,
    )
    assert two_q_same_day["status"] == "developing"

    # 7. 跨日巩固（2 道不同题 + 跨越家庭时区午夜）-> mastered
    day1_late = datetime(2026, 11, 1, 15, 30, tzinfo=UTC)  # 北京时间 11-01 23:30
    day2_early = datetime(2026, 11, 1, 16, 30, tzinfo=UTC)  # 北京时间 11-02 00:30
    cross_day_mastered = evaluate_knowledge_point(
        [
            _make_attempt(
                idx=1, q_uid="q-1", session_id="s-1", correct=True, received_at=day1_late
            ),
            _make_attempt(
                idx=2, q_uid="q-2", session_id="s-2", correct=True, received_at=day2_early
            ),
        ],
        total_questions_available=4,
        timezone="Asia/Shanghai",
    )
    assert cross_day_mastered["status"] == "mastered"
    assert cross_day_mastered["distinct_days"] == 2

    # 8. 单日 3 道不同题全部无提示首答正确 -> mastered，且乱序输入重算结果一致
    three_q_attempts = [
        _make_attempt(idx=1, q_uid="q-1", session_id="s-1", correct=True),
        _make_attempt(idx=2, q_uid="q-2", session_id="s-1", correct=True),
        _make_attempt(idx=3, q_uid="q-3", session_id="s-1", correct=True),
    ]
    mastered_a = evaluate_knowledge_point(three_q_attempts, total_questions_available=4)
    mastered_b = evaluate_knowledge_point(
        list(reversed(three_q_attempts)), total_questions_available=4
    )
    assert mastered_a["status"] == "mastered"
    assert mastered_a == mastered_b

    # 9. 最近连续 2 次首答错误 -> needs_review
    regressed = evaluate_knowledge_point(
        [
            *three_q_attempts,
            _make_attempt(idx=4, q_uid="q-4", session_id="s-2", correct=False),
            _make_attempt(idx=5, q_uid="q-5", session_id="s-2", correct=False),
        ],
        total_questions_available=5,
    )
    assert regressed["status"] == "needs_review"
    assert regressed["reason_code"] == "recent_consecutive_errors"


@pytest.mark.asyncio
async def test_diagnostics_api_authorization_evidence_portability_and_erasure(
    auth_app, source_tree
):
    first, second = await prepare(auth_app, source_tree)
    other_parent = await provision_parent(
        auth_app, {**SECOND_ACCOUNT, "nickname": "另一家庭家长"}
    )
    async with auth_app.state.database.sessions() as db:
        other_student = Student(
            family_id=UUID(other_parent["family"]["id"]), nickname="他家孩子"
        )
        db.add(other_student)
        await db.commit()
        other_student_id = other_student.id

        # 重复同步知识点目录保持幂等
        first_sync = await sync_knowledge_catalog(db, source_tree)
        second_sync = await sync_knowledge_catalog(db, source_tree)
        await db.commit()
        assert first_sync == second_sync
        assert await db.scalar(select(func.count()).select_from(KnowledgePoint)) == first_sync[
            "knowledge_points"
        ]
        assert await db.scalar(
            select(func.count()).select_from(KnowledgePointRelation)
        ) == first_sync["relations"]
        assert await db.scalar(
            select(func.count()).select_from(QuestionKnowledgeLink)
        ) == first_sync["question_links"]

    await init_admin(auth_app)

    async with (
        client_for(auth_app) as parent_client,
        client_for(auth_app) as child0_client,
        client_for(auth_app) as child1_client,
        client_for(auth_app) as other_parent_client,
        client_for(auth_app) as admin_client,
    ):
        await parent_login(parent_client)
        await login_child(child0_client, 0)
        await login_child(child1_client, 1)
        assert (
            await other_parent_client.post("/api/v1/auth/login", json=SECOND_ACCOUNT)
        ).status_code == 200
        csrf(other_parent_client)
        await login_change(admin_client, "admin")

        # 1. 教材知识点目录查询与受控跨课/跨版关系
        cat_resp = await parent_client.get("/api/v1/textbooks/g1up/knowledge-points")
        assert cat_resp.status_code == 200, cat_resp.text
        catalog = cat_resp.json()
        assert catalog["book_id"] == "g1up"
        assert catalog["mapping_version"] == MAPPING_VERSION
        assert "secret-explanation" not in json.dumps(catalog)
        kp1_item = next(
            kp
            for u in catalog["units"]
            for kp in u["knowledge_points"]
            if kp["lesson_id"] == "g1up-u1-kp1"
        )
        assert any(
            rel["relation_kind"] == "restores_lesson" for rel in kp1_item["related_points"]
        )

        cat_2026 = (
            await parent_client.get("/api/v1/textbooks/g1up-2026/knowledge-points")
        ).json()
        kp1_2026_item = next(
            kp
            for u in cat_2026["units"]
            for kp in u["knowledge_points"]
            if kp["lesson_id"] == "g1up-2026-u1-kp1"
        )
        assert any(
            rel["relation_kind"] == "supersedes_exact_title"
            and rel["kp_id"] == kp1_item["id"]
            for rel in kp1_2026_item["related_points"]
        )

        # 2. 导入 legacy 摘要、完成听读不应产生知识点掌握度证据
        prev = (
            await parent_client.post(
                f"/api/v1/students/{first}/imports/preview", json=backup()
            )
        ).json()
        await parent_client.post(
            f"/api/v1/students/{first}/imports/confirm",
            json={k: prev[k] for k in ("preview_id", "source_hash", "revision")},
        )
        reading_resp = await post(
            child0_client,
            f"/students/{first}/learning-sessions",
            {
                "kind": "reading",
                "book_id": "g1up",
                "source_id": "g1up-p1",
                "reading_kind": "listen",
                "client_at": now(),
            },
        )
        assert reading_resp.status_code == 200, reading_resp.text
        reading_sess = reading_resp.json()
        complete_resp = await post(
            child0_client,
            f"/learning-sessions/{reading_sess['id']}/complete",
            {
                "revision": reading_sess["revision"],
                "client_at": now(),
            },
        )
        assert complete_resp.status_code == 200, complete_resp.text

        diag_initial = (
            await parent_client.get(f"/api/v1/students/{first}/diagnostics")
        ).json()
        assert diag_initial["summary"]["assessed_count"] == 0
        assert diag_initial["summary"]["legacy_imports_count"] == 1
        assert "旧本地档案" in diag_initial["summary"]["legacy_exclusion_note"]

        # 3. 真实课程作答：首答错误 -> 回炉重做正确 -> 诊断为 needs_review（不虚增为 mastered）
        lesson_sess = (
            await post(
                child0_client,
                f"/students/{first}/learning-sessions",
                {
                    "kind": "lesson",
                    "book_id": "g1up",
                    "source_id": "g1up-u1-kp1",
                    "client_at": now(),
                },
            )
        ).json()
        sid = lesson_sess["id"]
        q = lesson_sess["question"]
        wrong_ans = (
            await post(
                child0_client,
                f"/learning-sessions/{sid}/attempts",
                {
                    "revision": lesson_sess["revision"],
                    "question_uid": q["uid"],
                    "question_version": q["version"],
                    "answer": "0",
                    "client_at": now(),
                    "declared_duration_ms": 3000,
                },
            )
        ).json()
        advanced = (
            await post(
                child0_client,
                f"/learning-sessions/{sid}/advance",
                {"revision": wrong_ans["revision"], "client_at": now()},
            )
        ).json()
        right_ans = (
            await post(
                child0_client,
                f"/learning-sessions/{sid}/attempts",
                {
                    "revision": advanced["revision"],
                    "question_uid": q["uid"],
                    "question_version": q["version"],
                    "answer": "1/2",
                    "client_at": now(),
                    "declared_duration_ms": 2500,
                },
            )
        ).json()
        assert right_ans["feedback"]["correct"] is True

        # 记录此时的经济与账本状态，确认后续诊断读取不会修改成绩或奖励
        async with auth_app.state.database.sessions() as db:
            att_count_before = await db.scalar(
                select(func.count()).select_from(Attempt).where(Attempt.student_id == first)
            )
            ledger_count_before = await db.scalar(
                select(func.count())
                .select_from(RewardLedger)
                .where(RewardLedger.student_id == first)
            )
            econ_before = await db.get(EconomyState, first)
            econ_snapshot = dict(econ_before.payload) if econ_before else None

        diag_after = (
            await parent_client.get(f"/api/v1/students/{first}/diagnostics")
        ).json()
        assert diag_after["summary"]["needs_review_count"] == 1
        assert diag_after["summary"]["mastered_count"] == 0
        assert diag_after["priority_review"][0]["id"] == kp1_item["id"]
        assert (
            diag_after["priority_review"][0]["reason_code"]
            == "first_wrong_remediated_same_session"
        )

        # 学生本人在 child 模式下也可读取本人诊断与单点明细
        child_diag = await child0_client.get(f"/api/v1/students/{first}/diagnostics")
        assert child_diag.status_code == 200
        detail_resp = await parent_client.get(
            f"/api/v1/students/{first}/diagnostics/knowledge-points/{kp1_item['id']}"
        )
        assert detail_resp.status_code == 200, detail_resp.text
        detail = detail_resp.json()
        assert detail["knowledge_point"]["id"] == kp1_item["id"]
        assert len(detail["recent_attempts"]) == 2
        assert detail["recent_attempts"][0]["first_attempt"] is False
        assert detail["recent_attempts"][1]["first_attempt"] is True
        assert "secret-explanation" not in json.dumps(detail)
        assert "1/2" not in json.dumps(detail)

        # 确认诊断查询无任何写副作用
        async with auth_app.state.database.sessions() as db:
            assert (
                await db.scalar(
                    select(func.count()).select_from(Attempt).where(Attempt.student_id == first)
                )
                == att_count_before
            )
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(RewardLedger)
                    .where(RewardLedger.student_id == first)
                )
                == ledger_count_before
            )
            econ_after = await db.get(EconomyState, first)
            assert (dict(econ_after.payload) if econ_after else None) == econ_snapshot

        # 4. 权限隔离验证：兄弟姐妹、跨家庭家长、管理员均拒绝越权访问
        assert (
            await child1_client.get(f"/api/v1/students/{first}/diagnostics")
        ).status_code == 404
        assert (
            await child1_client.get(
                f"/api/v1/students/{first}/diagnostics/knowledge-points/{kp1_item['id']}"
            )
        ).status_code == 404
        assert (
            await other_parent_client.get(f"/api/v1/students/{first}/diagnostics")
        ).status_code == 404
        assert (
            await parent_client.get(f"/api/v1/students/{other_student_id}/diagnostics")
        ).status_code == 404
        assert (
            await admin_client.get(f"/api/v1/students/{first}/diagnostics")
        ).status_code == 403

        # 5. 家庭导出包含诊断快照与规则版本说明
        exported = (await parent_client.get("/api/v1/family/export")).json()
        diag_export = exported["data"]["diagnostics"]
        assert diag_export["diagnostic_rule_version"] == DIAGNOSTIC_RULE_VERSION
        assert diag_export["mapping_version"] == MAPPING_VERSION
        first_export = next(
            s for s in diag_export["students"] if s["student_id"] == str(first)
        )
        assert first_export["legacy_imports_excluded"] == 1
        assert first_export["books"][0]["book_id"] == "g1up"
        assert first_export["books"][0]["summary"]["needs_review_count"] == 1

        # 6. 删除学生后无残留作答或诊断隐私数据
        del_resp = await parent_client.delete(
            f"/api/v1/students/{first}",
            params={"confirm": str(first)},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert del_resp.status_code == 204
        assert (
            await parent_client.get(f"/api/v1/students/{first}/diagnostics")
        ).status_code == 404
        exported_after = (await parent_client.get("/api/v1/family/export")).json()
        remaining_ids = [
            s["student_id"] for s in exported_after["data"]["diagnostics"]["students"]
        ]
        assert str(first) not in remaining_ids
