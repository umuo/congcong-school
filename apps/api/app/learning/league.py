"""原确定性影子同学联赛；云端以学生范围固定种子、家庭时区和奖励账本。"""

import secrets
from datetime import date, timedelta

from app.learning import economy
from app.learning.sampling import MASK, djb2, mix64


def seed(week, tier, salt):
    return mix64(djb2(f"{week}#{tier}#{salt}"))


def draw(value, offset, count):
    return mix64((value + offset) & MASK) % count if count > 0 else 0


def names(week, tier, salt):
    pool = list(economy.POLICY["league"]["names"])
    value = seed(week, tier, salt)
    return [pool.pop(draw(value, 0x1000 + i, len(pool))) for i in range(15)]


def goal(week, tier, salt, index):
    bounds = economy.POLICY["league"]["ranges"][tier]
    return bounds["min"] + draw(
        seed(week, tier, salt), 0x2000 + index, bounds["max"] - bounds["min"] + 1
    )


def bot_xp(week, tier, salt, index, local_now):
    value = seed(week, tier, salt)
    target = goal(week, tier, salt, index)
    day = (local_now.date() - date.fromisoformat(week)).days
    if day < 0:
        return 0
    if day > 6:
        return target
    weights = [1 + draw(value, 0x3000 + index * 0x10 + d, 9) for d in range(7)]
    total = sum(weights)
    previous = target * sum(weights[:day]) // total
    today = target * sum(weights[: day + 1]) // total - previous
    start, end = 6 + draw(value, 0x4000 + index, 5), 18 + draw(value, 0x5000 + index, 6)
    return previous + today * min(max(local_now.hour - start, 0), end - start) // (end - start)


def week_xp(history, week):
    start = date.fromisoformat(week)
    return sum(history.get((start + timedelta(days=i)).isoformat(), 0) for i in range(7))


def settle(state, today):
    policy = economy.POLICY["league"]
    week = (today - timedelta(days=today.weekday())).isoformat()
    state.setdefault("leagueSalt", secrets.token_hex(16))
    state.setdefault("leagueTier", "bronze")
    previous = state.get("leagueWeekKey", "")
    state["leagueWeekKey"] = week
    if not previous or previous >= week or len(state["completedLessons"]) < policy["unlock"]:
        return None, []
    tier, salt = state["leagueTier"], state["leagueSalt"]
    xp = week_xp(state["xpHistory"], previous)
    rank = 1 + sum(goal(previous, tier, salt, i) > xp for i in range(policy["bot_count"]))
    tiers = [item["id"] for item in policy["tiers"]]
    index = tiers.index(tier)
    promoted, demoted = rank <= policy["promote"] and index < 5, rank >= 12 and index > 0
    after = tiers[index + int(promoted) - int(demoted)]
    gems = policy["rank_rewards"].get(str(rank), 0) + (policy["promotion_bonus"] if promoted else 0)
    economy.add_gems(state, gems)
    state["leagueTier"] = after
    result = {
        "weekKey": previous,
        "rank": rank,
        "tierBefore": tier,
        "tierAfter": after,
        "promoted": promoted,
        "demoted": demoted,
        "gems": gems,
        "rule_version": "league-1",
    }
    state["pendingLeagueResult"] = result
    return result, [f"league:{previous}"]


# Frozen v1 pool: appending to the public catalog must not reshuffle existing bots.
BOT_AVATARS_V1 = (
    "panda",
    "fox",
    "rabbit",
    "bear",
    "cat",
    "dog",
    "tiger",
    "lion",
    "koala",
    "penguin",
    "owl",
    "frog",
    "robot",
    "astronaut",
    "star",
    "planet",
)


def standings(state, local_now, student_id="self", avatar_id="panda"):

    if "leagueSalt" not in state:
        return {"started": False, "rows": []}
    week, tier, salt = state["leagueWeekKey"], state["leagueTier"], state["leagueSalt"]
    bots = names(week, tier, salt)
    rows = [
        {
            "id": f"student:{student_id}",
            "avatar_id": avatar_id,
            "name": "你",
            "is_user": True,
            "xp": week_xp(state["xpHistory"], week),
        }
    ]
    rows.extend(
        {
            "id": f"bot:{week}:{tier}:{i}",
            "avatar_id": BOT_AVATARS_V1[
                mix64(djb2(f"avatar-v1#{week}#{tier}#{salt}#{i}")) % len(BOT_AVATARS_V1)
            ],
            "name": name,
            "is_user": False,
            "xp": bot_xp(week, tier, salt, i, local_now),
        }
        for i, name in enumerate(bots)
    )
    rows.sort(key=lambda row: (-row["xp"], not row["is_user"]))
    return {
        "started": True,
        "unlocked": len(state["completedLessons"]) >= 10,
        "week": week,
        "tier": tier,
        "simulated": True,
        "rows": [{**row, "rank": i + 1} for i, row in enumerate(rows)],
    }
