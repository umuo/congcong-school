"""带显式规则版本（diag-v1）的可重算知识点掌握度诊断引擎。"""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DIAGNOSTIC_RULE_VERSION = "diag-v1"

STATUS_ORDER = (
    "needs_review",
    "developing",
    "insufficient_evidence",
    "mastered",
    "unassessed",
)

STATUS_LABELS = {
    "mastered": "已掌握",
    "developing": "巩固中",
    "needs_review": "待加强",
    "insufficient_evidence": "证据不足",
    "unassessed": "未练习",
}


@dataclass(frozen=True)
class AttemptEvidence:
    attempt_id: str
    session_id: str
    session_kind: str
    ordinal: int
    question_uid: str
    question_version: str
    correct: bool
    first_attempt: bool
    hint_level: int
    received_at: datetime
    client_at: datetime
    declared_duration_ms: int


def resolve_zone(timezone: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone or "Asia/Shanghai")
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        return ZoneInfo("Asia/Shanghai")


def study_day_of(dt: datetime, zone: ZoneInfo) -> str:
    return dt.astimezone(zone).date().isoformat()


def evaluate_knowledge_point(
    attempts: list[AttemptEvidence],
    *,
    total_questions_available: int,
    timezone: str = "Asia/Shanghai",
) -> dict:
    zone = resolve_zone(timezone)
    ordered = sorted(
        attempts,
        key=lambda a: (a.received_at, a.session_id, a.ordinal, a.attempt_id),
    )

    total_attempts = len(ordered)
    if total_attempts == 0:
        return {
            "status": "unassessed",
            "status_label": STATUS_LABELS["unassessed"],
            "diagnostic_rule_version": DIAGNOSTIC_RULE_VERSION,
            "reason_code": "no_attempts",
            "reason_text": "尚无云端作答记录",
            "total_questions_available": total_questions_available,
            "distinct_questions_attempted": 0,
            "distinct_sessions": 0,
            "distinct_days": 0,
            "total_attempts": 0,
            "first_attempts_total": 0,
            "first_attempts_correct": 0,
            "unassisted_first_correct": 0,
            "hint_assisted_count": 0,
            "retry_attempts_total": 0,
            "retry_attempts_correct": 0,
            "first_accuracy": None,
            "unassisted_first_accuracy": None,
            "last_practiced_at": None,
            "last_study_day": None,
        }

    distinct_questions = len({a.question_uid for a in ordered})
    distinct_sessions = len({a.session_id for a in ordered})
    study_days = [study_day_of(a.received_at, zone) for a in ordered]
    distinct_days = len(set(study_days))

    first_attempts = [a for a in ordered if a.first_attempt]
    retry_attempts = [a for a in ordered if not a.first_attempt]
    # 极端防御：若仅存非首答记录，将每个会话该题最早一条视为首答基准
    if not first_attempts:
        seen_session_q: set[tuple[str, str]] = set()
        for a in ordered:
            key = (a.session_id, a.question_uid)
            if key not in seen_session_q:
                seen_session_q.add(key)
                first_attempts.append(a)

    first_total = len(first_attempts)
    first_correct = sum(1 for a in first_attempts if a.correct)
    unassisted_first_correct = sum(
        1 for a in first_attempts if a.correct and a.hint_level <= 0
    )
    hint_assisted_count = sum(1 for a in ordered if a.hint_level > 0)
    retry_total = len(retry_attempts)
    retry_correct = sum(1 for a in retry_attempts if a.correct)

    first_accuracy = round(first_correct / first_total, 4) if first_total else None
    unassisted_accuracy = (
        round(unassisted_first_correct / first_total, 4) if first_total else None
    )
    last_practiced_at = ordered[-1].received_at.isoformat()
    last_study_day = study_days[-1]

    recent_two_wrong = (
        first_total >= 2
        and not first_attempts[-1].correct
        and not first_attempts[-2].correct
    )
    all_first_wrong = first_total >= 1 and first_correct == 0
    low_unassisted = (
        first_total >= 2
        and (unassisted_first_correct / first_total) < 0.6
        and first_correct < first_total
    )

    if recent_two_wrong:
        status = "needs_review"
        reason_code = "recent_consecutive_errors"
        reason_text = (
            f"最近连续 2 次首答出错（无提示首答正确 {unassisted_first_correct}/{first_total}），"
            "建议优先复习"
        )
    elif all_first_wrong:
        status = "needs_review"
        if retry_correct > 0:
            reason_code = "first_wrong_remediated_same_session"
            reason_text = (
                f"首答出错（0/{first_total}），虽已完成当堂回炉订正"
                f"（{retry_correct}/{retry_total}），仍需隔次独立练习巩固"
            )
        else:
            reason_code = "first_attempts_wrong"
            reason_text = f"首答尚未答对（0/{first_total}），建议结合课程讲解巩固"
    elif low_unassisted:
        status = "needs_review"
        reason_code = "low_unassisted_accuracy"
        reason_text = (
            f"无提示首答正确率较低（{unassisted_first_correct}/{first_total}），建议针对错题巩固"
        )
    elif first_total < 2:
        status = "insufficient_evidence"
        if hint_assisted_count > 0:
            reason_code = "single_attempt_with_hint"
            reason_text = "仅有 1 次提示辅助下的作答记录，证据不足"
        else:
            reason_code = "single_attempt_only"
            reason_text = "仅有 1 次首答正确记录，需更多题目或隔天练习确认掌握"
    elif distinct_questions < 2 and distinct_days < 2:
        status = "insufficient_evidence"
        reason_code = "single_question_same_day"
        reason_text = (
            f"仅在单日练习同一道题（{first_total} 次），需覆盖更多题目或隔天验证"
        )
    elif unassisted_first_correct == 0:
        status = "insufficient_evidence"
        reason_code = "hint_dependent"
        reason_text = (
            f"共 {first_total} 次首答均依赖解题提示，尚无独立无提示首答证据"
        )
    else:
        latest_unassisted_ok = (
            first_attempts[-1].correct and first_attempts[-1].hint_level <= 0
        )
        enough_breadth_or_retention = (distinct_questions >= 3) or (
            distinct_questions >= 2 and distinct_days >= 2
        )
        if (
            (unassisted_first_correct / first_total) >= 0.8
            and latest_unassisted_ok
            and enough_breadth_or_retention
        ):
            status = "mastered"
            reason_code = "multi_evidence_mastered"
            reason_text = (
                f"无提示首答 {unassisted_first_correct}/{first_total} 正确，"
                f"已覆盖 {distinct_questions} 题、{distinct_days} 个学习日"
            )
        else:
            status = "developing"
            if not enough_breadth_or_retention:
                reason_code = "awaiting_cross_day_or_more_questions"
                reason_text = (
                    f"已完成 {distinct_questions} 道题无提示首答正确"
                    f"（{unassisted_first_correct}/{first_total}），"
                    "再练习更多题目或隔天巩固即可确认掌握"
                )
            elif not latest_unassisted_ok:
                reason_code = "latest_attempt_needed_support_or_retry"
                reason_text = (
                    f"无提示首答 {unassisted_first_correct}/{first_total} 正确，"
                    "但最近一次作答出错或使用了提示，建议再巩固一次"
                )
            else:
                reason_code = "developing_accuracy"
                reason_text = (
                    f"无提示首答 {unassisted_first_correct}/{first_total} 正确"
                    f"（覆盖 {distinct_questions} 题、{distinct_days} 天），正处于巩固阶段"
                )

    return {
        "status": status,
        "status_label": STATUS_LABELS[status],
        "diagnostic_rule_version": DIAGNOSTIC_RULE_VERSION,
        "reason_code": reason_code,
        "reason_text": reason_text,
        "total_questions_available": total_questions_available,
        "distinct_questions_attempted": distinct_questions,
        "distinct_sessions": distinct_sessions,
        "distinct_days": distinct_days,
        "total_attempts": total_attempts,
        "first_attempts_total": first_total,
        "first_attempts_correct": first_correct,
        "unassisted_first_correct": unassisted_first_correct,
        "hint_assisted_count": hint_assisted_count,
        "retry_attempts_total": retry_total,
        "retry_attempts_correct": retry_correct,
        "first_accuracy": first_accuracy,
        "unassisted_first_accuracy": unassisted_accuracy,
        "last_practiced_at": last_practiced_at,
        "last_study_day": last_study_day,
    }
