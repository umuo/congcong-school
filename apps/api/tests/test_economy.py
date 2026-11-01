import hashlib
import json
from pathlib import Path

from app.learning import economy as rules

ROOT = Path(__file__).resolve().parents[3]
VECTORS = json.loads((ROOT / "packages/core/spec/golden-vectors.json").read_text())


def test_exported_policy_matches_core_sources():
    for source, expected in rules.POLICY["source_hashes"].items():
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == expected
    assert len(rules.POLICY["cosmetics"]) == 30 and len(rules.POLICY["achievements"]) == 16


def test_economy_golden_vectors():
    for case in VECTORS["stars"]:
        assert rules.stars(case["accuracy"]) == case["expStars"]
    for case in [*VECTORS["xp"], *VECTORS["examXp"]]:
        assert (
            rules.lesson_xp(
                case["correctCount"],
                case["perfect"],
                case["firstPerfect"],
                case["isWeekend"],
                case.get("isExam", False),
            )
            == case["expXp"]
        )
    for case in VECTORS["gemDrip"]:
        assert (
            rules.gem_drip(case["stars"], case["isFirstPerfect"], case["crossedDailyGoal"])
            == case["expGems"]
        )
    for case in VECTORS["streakAdvance"]:
        assert rules.advance_streak(
            case["streak"], case["freezes"], case["gapDays"], case["isMonday"]
        ) == (case["expStreak"], case["expFreezes"], case["expConsumed"])
    for case in VECTORS["dailyReward"]:
        assert rules.daily_reward(case["streak"]) == case["expGems"]
    for case in VECTORS["milestone"]:
        assert rules.milestone(case["streakAfter"]) == case["expGems"]
    for case in VECTORS["quests"]:
        actual = [
            {key: quest[key] for key in ["kind", "target", "reward", "id"]}
            for quest in rules.quests(case["date"])
        ]
        assert actual == case["expQuests"]


def test_heart_regeneration_and_one_daily_goal_award():
    state = rules.initial_state()
    state.update(hearts=0, nextHeartAt=1000)
    rules.refresh_hearts(state, 1000 + rules.C["HEART_REGEN_SECONDS"] * 1000)
    assert state["hearts"] == 2
    rules.refresh_hearts(state, 1000 + 10 * rules.C["HEART_REGEN_SECONDS"] * 1000)
    assert state["hearts"] == 5 and state["nextHeartAt"] is None
    day = "2026-11-04"
    assert rules.add_xp(state, 50, day)
    state["dailyGoal"] = 100
    assert not rules.add_xp(state, 50, day)
    assert rules.add_xp(state, 100, "2026-11-05")


def test_sparse_projection_changes_rebuild_exact_state():
    from app.learning.economy_service import apply_changes, state_changes

    before = rules.initial_state()
    after = rules.initial_state()
    after["completedLessons"]["lesson"] = {"stars": 3, "accuracy": 1, "completedAt": "fixture"}
    after["hearts"] = 4
    after["nextHeartAt"] = 123456
    after["ownedCosmetics"]["skin_test"] = True
    changes = state_changes(before, after)
    assert apply_changes(before, changes) == after
    original = rules.initial_state()
    assert apply_changes(after, state_changes(after, original)) == original
