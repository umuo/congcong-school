import json
from datetime import datetime, timedelta
from pathlib import Path

from app.learning import economy, league


def test_league_matches_shared_original_vectors():
    vector = json.loads(
        (Path(__file__).resolve().parents[3] / "packages/core/spec/golden-vectors.json").read_text()
    )["league"]
    week, tier, salt = vector["weekKey"], vector["tier"], vector["salt"]
    assert league.names(week, tier, salt) == vector["names"]
    for case in vector["bots"]:
        index = case["botIndex"]
        assert league.goal(week, tier, salt, index) == case["expGoal"]
        assert (
            league.bot_xp(week, tier, salt, index, datetime(2026, 8, 26, 12))
            == case["expXpWednesdayNoon"]
        )
        assert (
            league.bot_xp(week, tier, salt, index, datetime(2026, 8, 30, 23, 59))
            == case["expXpSundayNight"]
        )


def test_settlement_preserves_unlock_week_and_one_time_reward_semantics():
    today = datetime(2026, 8, 31).date()
    state = economy.initial_state()
    state.update(leagueSalt="golden-salt", leagueTier="gold", leagueWeekKey="2026-08-24")
    state["completedLessons"] = {str(i): {} for i in range(10)}
    state["xpHistory"] = {"2026-08-24": 10000}
    result, claims = league.settle(state, today)
    assert result["rank"] == 1 and result["gems"] == 120
    assert result["tierAfter"] == "sapphire"
    assert claims == ["league:2026-08-24"]
    before = state["gems"]
    assert league.settle(state, today) == (None, [])
    assert state["gems"] == before
    fresh = economy.initial_state()
    assert league.settle(fresh, today) == (None, [])
    assert league.settle(fresh, today + timedelta(days=7)) == (None, [])
    assert fresh["gems"] == 0


def test_avatar_rows_are_stable_and_do_not_change_original_standings():
    from app.avatars.catalog import AVATAR_IDS

    state = economy.initial_state()
    state.update(leagueSalt="golden-salt", leagueTier="gold", leagueWeekKey="2026-08-24")
    state["completedLessons"] = {str(i): {} for i in range(10)}
    state["xpHistory"] = {"2026-08-24": 450}
    before = json.dumps(state, sort_keys=True)
    first = league.standings(state, datetime(2026, 8, 26, 12), "student-a", "robot")
    later = league.standings(state, datetime(2026, 8, 30, 23, 59), "student-a", "robot")
    assert json.dumps(state, sort_keys=True) == before
    assert first == league.standings(state, datetime(2026, 8, 26, 12), "student-a", "robot")
    assert first["simulated"] is True and len(first["rows"]) == 16
    expected = [{"name": "你", "is_user": True, "xp": 450}]
    expected.extend(
        {
            "name": name,
            "is_user": False,
            "xp": league.bot_xp("2026-08-24", "gold", "golden-salt", i, datetime(2026, 8, 26, 12)),
        }
        for i, name in enumerate(league.names("2026-08-24", "gold", "golden-salt"))
    )
    expected.sort(key=lambda r: (-r["xp"], not r["is_user"]))
    expected = [dict(r, rank=i + 1) for i, r in enumerate(expected)]
    assert [
        {k: v for k, v in row.items() if k not in {"id", "avatar_id"}} for row in first["rows"]
    ] == expected
    original = {r["id"]: r["avatar_id"] for r in first["rows"]}
    assert {r["id"]: r["avatar_id"] for r in later["rows"]} == original
    assert all(r["avatar_id"] in AVATAR_IDS for r in first["rows"])
    assert any(
        r["rank"] != next(x["rank"] for x in later["rows"] if x["id"] == r["id"])
        for r in first["rows"]
    )
    # Catalog growth does not mutate the frozen bot pool or consume XP/name RNG.
    assert isinstance(league.BOT_AVATARS_V1, tuple) and len(league.BOT_AVATARS_V1) == 16
    changed = league.standings(state, datetime(2026, 8, 26, 12), "student-b", "planet")
    assert next(r for r in changed["rows"] if r["is_user"])["avatar_id"] == "planet"
    assert next(r for r in changed["rows"] if r["is_user"])["id"] == "student:student-b"
    assert [r for r in changed["rows"] if not r["is_user"]] == [
        r for r in first["rows"] if not r["is_user"]
    ]
