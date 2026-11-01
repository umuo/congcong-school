"""镜像 core 经济纯函数，数值目录从同一来源导出。"""

import copy
import json
from datetime import date, timedelta
from pathlib import Path

from app.learning.sampling import MASK, djb2, mix64

POLICY = json.loads(Path(__file__).with_name("policy.json").read_text())
C = POLICY["constants"]
VERSION = POLICY["version"]
COSMETICS = {item["id"]: item for item in POLICY["cosmetics"]}
NUMBER_LESSONS = {item["id"] for item in POLICY["number_lessons"].values()}


def stars(accuracy):
    return (
        3
        if accuracy >= C["THREE_STAR_ACCURACY"]
        else 2
        if accuracy >= C["TWO_STAR_ACCURACY"]
        else 1
    )


def lesson_xp(correct, perfect, first_perfect, weekend, exam=False):
    value = correct * C["XP_PER_CORRECT"]
    if perfect:
        value += C["PERFECT_XP_BONUS"]
    if first_perfect:
        value += C["FIRST_PERFECT_XP_BONUS"]
    if weekend:
        value *= C["WEEKEND_XP_MULTIPLIER"]
    if exam:
        value *= C["EXAM_XP_MULTIPLIER"]
    return value


def gem_drip(star, first_perfect, crossed_goal):
    value = C["LESSON_GEM_BASE"]
    if star == 3:
        value += C["LESSON_GEM_THREE_STAR_BONUS"]
    elif star == 2:
        value += C["LESSON_GEM_TWO_STAR_BONUS"]
    return (
        value
        + (C["FIRST_PERFECT_GEM_BONUS"] if first_perfect else 0)
        + (C["DAILY_GOAL_BONUS"] if crossed_goal else 0)
    )


def advance_streak(streak, freezes, gap, monday):
    if gap <= 0:
        return streak, freezes, 0
    if gap == 1:
        return streak + 1, freezes + 1 if monday and freezes < C["MAX_FREEZES"] else freezes, 0
    missed = gap - 1
    if freezes >= missed:
        return streak + 1, freezes - missed, missed
    return 1, freezes, 0


def daily_reward(streak):
    return C["DAILY_REWARD_TABLE"][min(len(C["DAILY_REWARD_TABLE"]) - 1, max(0, int(streak)))]


def milestone(streak):
    return C["STREAK_MILESTONE_REWARDS"].get(str(streak), 0)


def quests(day):
    hashed = mix64(djb2(day))

    def index(count, salt):
        return mix64((hashed + salt) & MASK) % count

    rest = ["finishLessons", "reviewMistakes", "readTexts"]
    first = rest.pop(index(len(rest), 0x11))
    second = rest[index(len(rest), 0x22)]
    result = []
    for kind, salt in [("earnXP", 0x01), (first, 0x33), (second, 0x44)]:
        options = [q for q in POLICY["quests"] if q["kind"] == kind]
        result.append(copy.deepcopy(options[index(len(options), salt)]))
    return result


def initial_state():
    starters = {item["id"]: True for item in POLICY["cosmetics"] if item.get("starter")}
    return {
        "xp": 0,
        "gems": 0,
        "lifetimeGems": 0,
        "streak": 0,
        "lastActiveDate": "",
        "streakFreezes": C["INITIAL_FREEZES"],
        "hearts": C["MAX_HEARTS"],
        "nextHeartAt": None,
        "lastReviewHeartDate": "",
        "dailyGoal": C["DEFAULT_DAILY_GOAL"],
        "todayXp": 0,
        "lastXpDate": "",
        "completedLessons": {},
        "perfectedLessons": {},
        "claimedChests": {},
        "claimedStreakRewards": {},
        "unlockedAchievements": {},
        "ownedCosmetics": starters,
        "equippedMascotSkin": POLICY["equipped"]["mascotSkin"],
        "equippedTheme": POLICY["equipped"]["uiTheme"],
        "equippedBackdrop": POLICY["equipped"]["lessonBackdrop"],
        "dailyQuestDate": "",
        "dailyLessons": 0,
        "dailyReviews": 0,
        "dailyReadings": 0,
        "claimedQuests": {},
        "claimedGoalDates": {},
        "lastDailyRewardDate": "",
        "xpHistory": {},
        "lessonHistory": {},
        "studyDays": {},
        "completedReadings": {},
        "numberSenseProgress": {},
    }


def roll_day(state, day):
    if state["dailyQuestDate"] != day:
        state.update(dailyQuestDate=day, dailyLessons=0, dailyReviews=0, dailyReadings=0)
    if state["lastXpDate"] != day:
        state.update(lastXpDate=day, todayXp=0)


def add_gems(state, amount):
    state["gems"] += amount
    state["lifetimeGems"] += max(0, amount)


def add_xp(state, amount, day):
    roll_day(state, day)
    before = state["todayXp"]
    state["xp"] += amount
    state["todayXp"] += amount
    state["xpHistory"][day] = state["xpHistory"].get(day, 0) + amount
    crossed = before < state["dailyGoal"] <= state["todayXp"] and state["dailyGoal"] > 0
    if crossed and day not in state["claimedGoalDates"]:
        state["claimedGoalDates"][day] = True
        return True
    return False


def refresh_hearts(state, now_ms):
    if state["hearts"] >= C["MAX_HEARTS"]:
        state["nextHeartAt"] = None
        return
    interval = C["HEART_REGEN_SECONDS"] * 1000
    if not state["nextHeartAt"]:
        state["nextHeartAt"] = now_ms + interval
        return
    while (
        state["nextHeartAt"]
        and now_ms >= state["nextHeartAt"]
        and state["hearts"] < C["MAX_HEARTS"]
    ):
        state["hearts"] += 1
        state["nextHeartAt"] = (
            state["nextHeartAt"] + interval if state["hearts"] < C["MAX_HEARTS"] else None
        )


def bump_streak(state, today):
    day = today.isoformat()
    if state["lastActiveDate"] == day:
        return 0
    if state["lastActiveDate"]:
        streak, freezes, _ = advance_streak(
            state["streak"],
            state["streakFreezes"],
            (today - date.fromisoformat(state["lastActiveDate"])).days,
            today.weekday() == 0,
        )
        state.update(streak=streak, streakFreezes=freezes)
    else:
        state["streak"] = 1
    state["lastActiveDate"] = day
    amount = milestone(state["streak"])
    key = str(state["streak"])
    if amount and key not in state["claimedStreakRewards"]:
        state["claimedStreakRewards"][key] = True
        add_gems(state, amount)
        return amount
    return 0


def effective_streak(state, today):
    if state["streak"] <= 0 or not state["lastActiveDate"]:
        return 0
    gap = (today - date.fromisoformat(state["lastActiveDate"])).days
    return state["streak"] if gap <= 1 or gap - 1 <= state["streakFreezes"] else 0


def quest_progress(state, kind, day):
    if kind == "earnXP":
        return state["todayXp"] if state["lastXpDate"] == day else 0
    if state["dailyQuestDate"] != day:
        return 0
    return {
        "finishLessons": state["dailyLessons"],
        "reviewMistakes": state["dailyLessons"] + state["dailyReviews"],
        "readTexts": state["dailyReadings"],
    }.get(kind, 0)


def unlock_achievements(state, reviewed_count):
    starter = {item["id"] for item in POLICY["cosmetics"] if item.get("starter")}
    granted = []
    for _ in range(5):
        metrics = {
            "lessons": len(state["completedLessons"]),
            "xp": state["xp"],
            "streak": state["streak"],
            "perfect": len(state["perfectedLessons"]),
            "cosmetics": len(set(state["ownedCosmetics"]) - starter),
            "lifetimeGems": state["lifetimeGems"],
            "reviews": reviewed_count,
        }
        new = [
            a
            for a in POLICY["achievements"]
            if metrics[a["metric"]] >= a["goal"] and a["id"] not in state["unlockedAchievements"]
        ]
        if not new:
            break
        for achievement in new:
            state["unlockedAchievements"][achievement["id"]] = True
            add_gems(state, achievement["reward"])
            granted.append(achievement["id"])
    return granted


def number_skill(source_id):
    return next(
        (skill for skill, item in POLICY["number_lessons"].items() if item["id"] == source_id), None
    )


def record_number_practice(state, skill, evidence, day):
    state["numberSenseProgress"][skill] = {
        "version": POLICY["number_version"],
        "practicedOn": day,
        "nextReviewOn": (date.fromisoformat(day) + timedelta(days=1)).isoformat(),
        "evidence": evidence,
    }


def number_due(state, skill, day):
    entry = state["numberSenseProgress"].get(skill)
    return bool(
        entry
        and entry.get("version") == POLICY["number_version"]
        and day > entry["practicedOn"]
        and day >= entry["nextReviewOn"]
    )


def record_number_review(state, skill, correct, total, day):
    if not number_due(state, skill, day) or total != 2 or not 0 <= correct <= total:
        return False
    entry = state["numberSenseProgress"][skill]
    passed = correct == total
    entry.update(
        reviewedOn=day,
        reviewCorrect=correct,
        reviewTotal=total,
        nextReviewOn=(date.fromisoformat(day) + timedelta(days=7 if passed else 1)).isoformat(),
    )
    if passed:
        entry["verifiedOn"] = day
    else:
        entry.pop("verifiedOn", None)
    return True
