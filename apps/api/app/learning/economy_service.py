import copy
import math
import secrets
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, tuple_

from app.content.models import QuestionVersion
from app.curriculum.models import Textbook
from app.errors import APIError
from app.families.models import Family
from app.learning import economy as rules
from app.learning import league
from app.learning.models import Attempt, EconomyState, RewardClaim, RewardLedger
from app.learning.review import review_bank
from app.learning.transactions import append_event, receipt, save_receipt


def now_utc():
    return datetime.now(UTC)


async def clock(db, student):
    family = await db.get(Family, student.family_id)
    now = now_utc()
    return now, now.astimezone(ZoneInfo(family.timezone)).date()


async def load_state(db, student):
    row = await db.get(EconomyState, student.id)
    if row is None:
        row = EconomyState(
            student_id=student.id,
            family_id=student.family_id,
            payload=rules.initial_state(),
            revision=1,
        )
        db.add(row)
        await db.flush()
    return row, copy.deepcopy(row.payload)


def state_changes(before, after, path=()):
    changes = []
    for key in before.keys() | after.keys():
        trail = [*path, key]
        if key not in after:
            changes.append({"path": trail, "remove": True})
        elif key not in before:
            changes.append({"path": trail, "value": after[key]})
        elif isinstance(before[key], dict) and isinstance(after[key], dict):
            changes.extend(state_changes(before[key], after[key], trail))
        elif before[key] != after[key]:
            changes.append({"path": trail, "value": after[key]})
    return sorted(changes, key=lambda item: item["path"])


def apply_changes(state, changes):
    for change in changes:
        node = state
        for key in change["path"][:-1]:
            node = node.setdefault(key, {})
        key = change["path"][-1]
        if change.get("remove"):
            node.pop(key, None)
        else:
            node[key] = copy.deepcopy(change["value"])
    return state


async def save_state(db, student, row, state, key, result, client_at, claims=()):
    changes = state_changes(row.payload, state)
    ledger = RewardLedger(
        id=uuid4(),
        student_id=student.id,
        claim_key=key,
        rule_version=rules.VERSION,
        xp_delta=state["xp"] - row.payload["xp"],
        gems_delta=state["gems"] - row.payload["gems"],
        changes=changes,
        result=result,
    )
    db.add(ledger)
    await db.flush()
    for claim_key in set(claims):
        db.add(RewardClaim(student_id=student.id, key=claim_key, ledger_id=ledger.id))
    row.payload = state
    row.revision += 1
    await append_event(
        db,
        student,
        "economy_changed",
        {
            "ledger_id": str(ledger.id),
            "rule_version": rules.VERSION,
            "changes": changes,
            "result": result,
        },
        client_at,
    )
    return ledger


async def achievements(db, student, state):
    bank = await review_bank(db, student)
    reviewed = sum(1 for item in bank.values() if item["correct_count"] > 0)
    ids = rules.unlock_achievements(state, reviewed)
    return ids, [f"achievement:{value}" for value in ids]


async def progress_view(db, student, row, state):
    _, today = await clock(db, student)
    day = today.isoformat()
    return {
        "student_id": str(student.id),
        "revision": row.revision,
        "rule_version": rules.VERSION,
        "state": state,
        "quests": [
            {
                **quest,
                "progress": rules.quest_progress(state, quest["kind"], day),
                "claimed": f"{day}:{quest['id']}" in state["claimedQuests"],
            }
            for quest in rules.quests(day)
        ],
    }


def need_hearts(kind, source_id):
    return kind in {"lesson", "challenge"} and source_id not in rules.NUMBER_LESSONS


async def check_hearts(db, student, kind, source_id):
    row, state = await load_state(db, student)
    now, _ = await clock(db, student)
    rules.refresh_hearts(state, int(now.timestamp() * 1000))
    if need_hearts(kind, source_id) and state["hearts"] <= 0:
        raise APIError(409, "HEARTS_REQUIRED", "红心不足，可先复习或等待恢复")
    return row, state


async def check_number_due(db, student, skill):
    _, state = await load_state(db, student)
    _, today = await clock(db, student)
    if not rules.number_due(state, skill, today.isoformat()):
        raise APIError(409, "NUMBER_REVIEW_NOT_DUE", "请先练习，隔天再检验")


async def record_attempt_effects(db, student, kind, source_id, attempt, client_at):
    row, state = await load_state(db, student)
    now, _ = await clock(db, student)
    now_ms = int(now.timestamp() * 1000)
    rules.refresh_hearts(state, now_ms)
    lost_heart = need_hearts(kind, source_id) and not attempt.correct
    if lost_heart and state["hearts"] > 0:
        state["hearts"] -= 1
        state["nextHeartAt"] = (
            state["nextHeartAt"] or now_ms + rules.C["HEART_REGEN_SECONDS"] * 1000
        )
    unlocked, claims = await achievements(db, student, state)
    if not lost_heart and not unlocked:
        return
    await save_state(
        db,
        student,
        row,
        state,
        f"attempt:{attempt.id}",
        {"kind": "attempt_effects", "attempt_id": str(attempt.id), "achievements": unlocked},
        client_at,
        claims,
    )


async def chest_slot(db, book_id, chest_id=None, after_lesson=None):
    book = await db.get(Textbook, book_id)
    if book is None:
        return None
    for unit in book.units:
        for index, lesson in enumerate(unit["lessons"]):
            if (index + 1) % 5:
                continue
            slot = {
                "id": f"{book_id}-u{unit['number']}-chest-{(index + 1) // 5 - 1}",
                "afterLessonId": lesson["id"],
                "unitNumber": unit["number"],
            }
            if slot["id"] == chest_id or slot["afterLessonId"] == after_lesson:
                return slot
    return None


def roll_chest():
    roll = secrets.randbelow(1_000_000) / 1_000_000
    low, span, tier = (
        (10, 10, "common") if roll < 0.85 else (21, 9, "rare") if roll < 0.95 else (40, 10, "epic")
    )
    return {
        "gems": math.floor(low + secrets.randbelow(1_000_000) / 1_000_000 * span + 0.5),
        "tier": tier,
    }


async def award_chest(db, state, book_id, *, chest_id=None, after_lesson=None):
    slot = await chest_slot(db, book_id, chest_id, after_lesson)
    if not slot or slot["afterLessonId"] not in state["completedLessons"]:
        if chest_id:
            raise APIError(409, "CHEST_NOT_AVAILABLE", "宝箱尚未解锁")
        return None, []
    if slot["id"] in state["claimedChests"]:
        return None, []
    reward = roll_chest()
    state["claimedChests"][slot["id"]] = True
    rules.add_gems(state, reward["gems"])
    return {**slot, **reward}, [f"chest:{slot['id']}"]


async def complete(db, student, session, body, key):
    operation = f"complete:{session.id}"
    old, request_hash = await receipt(db, student.id, operation, key, body)
    if old is not None:
        return old
    # 换新键重放已结束会话也只返回已有结算，不再判分或发奖。
    existing = await db.scalar(
        select(RewardLedger).where(
            RewardLedger.student_id == student.id, RewardLedger.claim_key == f"session:{session.id}"
        )
    )
    if existing is not None:
        return await save_receipt(db, student.id, operation, key, request_hash, existing.result)
    if session.revision != body.revision:
        raise APIError(409, "LEARNING_REVISION_CONFLICT", "学习进度已变化，请刷新后继续")
    if body.abandon and session.kind != "review":
        raise APIError(422, "INVALID_COMPLETE_MODE", "只有复习可以结算已完成的部分")
    cp = session.checkpoint
    if (cp["pending"] or cp["feedback"]) and not (
        body.abandon and session.kind == "review" and cp["attempted"]
    ):
        raise APIError(409, "SESSION_NOT_FINISHED", "请先完成当前题目及反馈")
    row, state = await load_state(db, student)
    now, today = await clock(db, student)
    day = today.isoformat()
    rules.refresh_hearts(state, int(now.timestamp() * 1000))
    rules.roll_day(state, day)
    total = len(session.question_refs)
    correct = cp["first_correct"]
    accuracy = correct / total if total else 0
    result = {
        "session_id": str(session.id),
        "kind": session.kind,
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "xp_gained": 0,
        "gems_gained": 0,
        "hearts_gained": 0,
        "first_perfect": False,
        "chest": None,
        "partial": bool(body.abandon and (cp["pending"] or cp["feedback"])),
        "reviewed": len(cp["attempted"]),
        "reading_kind": cp.get("reading_kind"),
    }
    claims = []
    activity_credited = session.kind != "jump"
    xp_before, gems_before = state["xp"], state["gems"]
    if session.kind in {"lesson", "challenge"}:
        star = rules.stars(accuracy) if total >= 3 else 1
        first_perfect = star == 3 and session.source_id not in state["perfectedLessons"]
        xp = rules.lesson_xp(
            correct,
            correct == total and total >= 3,
            first_perfect,
            today.weekday() >= 5,
            session.kind == "challenge",
        )
        crossed = rules.add_xp(state, xp, day)
        rules.add_gems(state, rules.gem_drip(star, first_perfect, crossed))
        if first_perfect:
            state["perfectedLessons"][session.source_id] = True
            claims.append(f"first-perfect:{session.source_id}")
        if crossed:
            claims.append(f"goal:{day}")
        previous = state["completedLessons"].get(session.source_id)
        if not previous or star >= previous["stars"]:
            state["completedLessons"][session.source_id] = {
                "lessonId": session.source_id,
                "stars": star,
                "accuracy": max(accuracy, previous["accuracy"] if previous else 0),
                "completedAt": now.isoformat(),
            }
        skill = rules.number_skill(session.source_id)
        if skill:
            evidence = await number_evidence(db, session)
            rules.record_number_practice(state, skill, evidence, day)
            result["number_evidence"] = evidence
        state["dailyLessons"] += 1
        state["lessonHistory"][day] = state["lessonHistory"].get(day, 0) + 1
        before_claimed = set(state["claimedStreakRewards"])
        rules.bump_streak(state, today)
        claims.extend(f"streak:{n}" for n in set(state["claimedStreakRewards"]) - before_claimed)
        result.update(
            stars=star,
            first_perfect=first_perfect,
            weekend=today.weekday() >= 5,
            exam=session.kind == "challenge",
        )
        result["chest"], chest_claims = await award_chest(
            db, state, session.book_id, after_lesson=session.source_id
        )
        claims.extend(chest_claims)
    elif session.kind == "review":
        crossed = rules.add_xp(state, correct * 5, day)
        if crossed:
            rules.add_gems(state, rules.C["DAILY_GOAL_BONUS"])
            claims.append(f"goal:{day}")
        state["dailyReviews"] += len(cp["attempted"])
        if (
            state["lastReviewHeartDate"] != day
            and correct >= min(rules.C["REVIEW_HEART_MIN_CORRECT"], total)
            and state["hearts"] < rules.C["MAX_HEARTS"]
        ):
            state["hearts"] += rules.C["REVIEW_HEART_REWARD"]
            if state["hearts"] >= rules.C["MAX_HEARTS"]:
                state["nextHeartAt"] = None
            state["lastReviewHeartDate"] = day
            result["hearts_gained"] = rules.C["REVIEW_HEART_REWARD"]
            claims.append(f"review-heart:{day}")
        prior = set(state["claimedStreakRewards"])
        rules.bump_streak(state, today)
        claims.extend(f"streak:{n}" for n in set(state["claimedStreakRewards"]) - prior)
    elif session.kind in {"story", "reading"}:
        reading_kind = "story" if session.kind == "story" else cp["reading_kind"]
        reading_key = f"reading:{reading_kind}:{session.source_id}"
        activity_credited = reading_key not in state["completedReadings"]
        if activity_credited:
            xp = rules.C["READING_XP"][
                ("storyGood" if accuracy >= rules.C["READING_XP"]["goodThreshold"] else "storyBase")
                if session.kind == "story"
                else reading_kind
            ]
            crossed = rules.add_xp(state, xp, day)
            if crossed:
                rules.add_gems(state, rules.C["DAILY_GOAL_BONUS"])
                claims.append(f"goal:{day}")
            state["completedReadings"][reading_key] = day
            state["dailyReadings"] += 1
            claims.append(reading_key)
            prior = set(state["claimedStreakRewards"])
            rules.bump_streak(state, today)
            claims.extend(f"streak:{n}" for n in set(state["claimedStreakRewards"]) - prior)
    elif session.kind == "jump":
        result["passed"] = accuracy >= 0.8
        if result["passed"]:
            for source in session.sources:
                lesson_id = source["lesson_id"]
                if lesson_id not in state["completedLessons"]:
                    state["completedLessons"][lesson_id] = {
                        "lessonId": lesson_id,
                        "stars": 1,
                        "accuracy": 0.8,
                        "completedAt": now.isoformat(),
                        "source": "jump",
                    }
    elif session.kind == "number_review":
        skill = session.source_id.split("-")[2]
        eligible = rules.record_number_review(state, skill, correct, total, day)
        activity_credited = eligible
        result.update(number_skill=skill, number_review_eligible=eligible)
        if eligible:
            crossed = rules.add_xp(state, correct * 5, day)
            if crossed:
                rules.add_gems(state, rules.C["DAILY_GOAL_BONUS"])
                claims.append(f"goal:{day}")
            prior = set(state["claimedStreakRewards"])
            rules.bump_streak(state, today)
            claims.extend(f"streak:{n}" for n in set(state["claimedStreakRewards"]) - prior)
            claims.append(f"number-review:{skill}:{day}")
    if activity_credited:
        state["studyDays"][day] = True
    result["activity_credited"] = activity_credited
    session.status = "completed"
    session.revision += 1
    await append_event(
        db,
        student,
        "session_completed",
        {
            "session_id": str(session.id),
            "kind": session.kind,
            "book_id": session.book_id,
            "source_id": session.source_id,
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "reading_kind": cp.get("reading_kind"),
            "content_refs": session.sources,
            "study_day": day,
            "number_evidence": result.get("number_evidence"),
            "number_review_eligible": result.get("number_review_eligible"),
        },
        body.client_at,
    )
    unlocked, achievement_claims = await achievements(db, student, state)
    claims.extend(achievement_claims)
    result.update(
        xp_gained=state["xp"] - xp_before,
        gems_gained=state["gems"] - gems_before,
        achievements=unlocked,
    )
    result["progress_revision"] = row.revision + 1
    await save_state(
        db, student, row, state, f"session:{session.id}", result, body.client_at, claims
    )
    return await save_receipt(db, student.id, operation, key, request_hash, result)


async def action(db, student, body, key):
    operation = "economy-action"
    old, request_hash = await receipt(db, student.id, operation, key, body)
    if old is not None:
        return old
    row, state = await load_state(db, student)
    now, today = await clock(db, student)
    day = today.isoformat()
    rules.refresh_hearts(state, int(now.timestamp() * 1000))
    rules.roll_day(state, day)
    before_gems = state["gems"]
    claims = []
    result = {"kind": body.kind, "applied": False}
    if body.kind == "league":
        settlement, league_claims = league.settle(state, today)
        result.update(applied=settlement is not None, settlement=settlement)
        claims.extend(league_claims)
    elif body.kind == "daily_reward":
        if state["lastDailyRewardDate"] != day:
            effective = rules.effective_streak(state, today)
            rules.add_gems(state, rules.daily_reward(effective))
            state["lastDailyRewardDate"] = day
            result.update(applied=True, effective_streak=effective)
            claims.append(f"daily:{day}")
    elif body.kind == "quest":
        quest = next((item for item in rules.quests(day) if item["id"] == body.quest_id), None)
        if quest is None:
            raise APIError(404, "QUEST_NOT_FOUND", "找不到今天的任务")
        claim_key = f"{day}:{quest['id']}"
        if claim_key not in state["claimedQuests"]:
            if rules.quest_progress(state, quest["kind"], day) < quest["target"]:
                raise APIError(409, "QUEST_NOT_COMPLETE", "任务尚未完成")
            state["claimedQuests"][claim_key] = True
            rules.add_gems(state, quest["reward"])
            result["applied"] = True
            claims.append(f"quest:{claim_key}")
    elif body.kind == "chest":
        chest, chest_claims = await award_chest(db, state, body.book_id, chest_id=body.chest_id)
        result.update(applied=chest is not None, chest=chest)
        claims.extend(chest_claims)
    elif body.kind in {"buy_hearts", "buy_freeze", "makeup"}:
        cost = rules.C[
            {
                "buy_hearts": "HEART_REFILL_COST",
                "buy_freeze": "FREEZE_COST",
                "makeup": "STREAK_MAKEUP_COST",
            }[body.kind]
        ]
        allowed = (
            state["hearts"] < rules.C["MAX_HEARTS"]
            if body.kind == "buy_hearts"
            else state["streakFreezes"] < rules.C["MAX_FREEZES"]
            if body.kind == "buy_freeze"
            else bool(state["lastActiveDate"])
            and (today - date.fromisoformat(state["lastActiveDate"])).days >= 2
        )
        if not allowed:
            raise APIError(409, "PURCHASE_NOT_AVAILABLE", "当前状态无需购买此道具")
        if state["gems"] < cost:
            raise APIError(409, "INSUFFICIENT_GEMS", "宝石不足")
        state["gems"] -= cost
        if body.kind == "buy_hearts":
            state.update(hearts=rules.C["MAX_HEARTS"], nextHeartAt=None)
        elif body.kind == "buy_freeze":
            state["streakFreezes"] += 1
        else:
            state["lastActiveDate"] = (today - timedelta(days=1)).isoformat()
        result["applied"] = True
    elif body.kind in {"purchase_cosmetic", "equip_cosmetic"}:
        item = rules.COSMETICS.get(body.item_id)
        if item is None:
            raise APIError(404, "COSMETIC_NOT_FOUND", "找不到装扮")
        if body.kind == "purchase_cosmetic" and body.item_id in state["ownedCosmetics"]:
            raise APIError(409, "COSMETIC_ALREADY_OWNED", "已经拥有这件装扮")
        if body.kind == "purchase_cosmetic" and body.item_id not in state["ownedCosmetics"]:
            if state["gems"] < item["cost"]:
                raise APIError(409, "INSUFFICIENT_GEMS", "宝石不足")
            state["gems"] -= item["cost"]
            state["ownedCosmetics"][body.item_id] = True
            result["applied"] = True
            claims.append(f"cosmetic:{body.item_id}")
        if body.item_id not in state["ownedCosmetics"]:
            raise APIError(409, "COSMETIC_NOT_OWNED", "还没有这件装扮")
        field = {
            "mascot_skin": "equippedMascotSkin",
            "ui_theme": "equippedTheme",
            "lesson_backdrop": "equippedBackdrop",
        }[item["type"]]
        state[field] = body.item_id
        result["applied"] = True
    elif body.kind == "set_daily_goal":
        if row.revision != body.revision:
            raise APIError(409, "ECONOMY_REVISION_CONFLICT", "目标配置已变化，请刷新后重试")
        if (
            body.daily_goal not in rules.C["DAILY_GOAL_OPTIONS"]
            and body.daily_goal != state["dailyGoal"]
        ):
            raise APIError(422, "INVALID_DAILY_GOAL", "请选择可用的目标档位")
        state["dailyGoal"] = body.daily_goal
        result["applied"] = True
    unlocked, achievement_claims = await achievements(db, student, state)
    claims.extend(achievement_claims)
    result.update(gems_delta=state["gems"] - before_gems, achievements=unlocked)
    await save_state(db, student, row, state, f"action:{key}", result, body.client_at, claims)
    response = {"result": result, "progress": await progress_view(db, student, row, state)}
    return await save_receipt(db, student.id, operation, key, request_hash, response)


async def number_evidence(db, session):
    refs = session.question_refs
    versions = (
        await db.scalars(
            select(QuestionVersion).where(
                tuple_(QuestionVersion.uid, QuestionVersion.version).in_(
                    [(ref["uid"], ref["version"]) for ref in refs]
                )
            )
        )
    ).all()
    by_version = {(row.uid, row.version): row.private_payload for row in versions}
    attempts = (
        await db.scalars(
            select(Attempt).where(Attempt.session_id == session.id, Attempt.first_attempt.is_(True))
        )
    ).all()
    first = {row.question_uid: row for row in attempts}
    evidence = {
        "independentCorrect": 0,
        "independentTotal": 0,
        "transferCorrect": 0,
        "transferTotal": 0,
        "hintsUsed": 0,
    }
    for index, ref in enumerate(refs):
        question = by_version[ref["uid"], ref["version"]]
        attempt = first.get(ref["uid"])
        hinted = session.checkpoint.get("hint_levels", {}).get(str(index), 0) > 0 or bool(
            attempt and attempt.evidence.get("hint_level", 0) > 0
        )
        if hinted:
            evidence["hintsUsed"] += 1
        stage = (question.get("numberTask") or {}).get("stage")
        if stage in {"independent", "transfer"}:
            evidence[stage + "Total"] += 1
            if attempt and attempt.correct and not hinted:
                evidence[stage + "Correct"] += 1
    return evidence
