import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.content.models import ContentContainer, ContentRevision
from app.errors import APIError
from app.learning.models import EconomyState, LearningCursor
from app.portability.models import LegacyImport

MAX_BYTES = 5 * 1024 * 1024


async def read_backup(request):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise APIError(413, "IMPORT_TOO_LARGE", "每个档案最多 5 MB，请逐档案导入")
        chunks.append(chunk)
    try:
        value = json.loads(b"".join(chunks))
        if not isinstance(value, dict) or value.get("schema") != "cstf-backup":
            raise ValueError
        if type(value.get("version")) is not int or value["version"] != 1:
            raise APIError(
                422, "IMPORT_VERSION_UNSUPPORTED", "只支持 cstf-backup v1，请先用本地版导出"
            )
        if not isinstance(value.get("data"), dict):
            raise ValueError
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()
    except (ValueError, TypeError, RecursionError):
        raise APIError(422, "INVALID_BACKUP", "备份结构损坏或包含非法数值") from None
    return value, hashlib.sha256(encoded).hexdigest()


def bounded_map(data, name):
    value = data.get(name, {})
    if not isinstance(value, dict) or len(value) > 20000:
        raise APIError(422, "INVALID_BACKUP", f"{name} 必须是合法的记录表")
    return value


async def preview(db, student, value, source_hash):
    previous = await db.scalar(
        select(LegacyImport).where(
            LegacyImport.student_id == student.id, LegacyImport.source_hash == source_hash
        )
    )
    if previous and previous.confirmed_at:
        return import_view(previous)
    data = value["data"]
    grades = bounded_map(data, "completedLessons")
    cosmetics = bounded_map(data, "ownedCosmetics")
    readings = bounded_map(data, "completedReadings")
    mistakes = data.get("mistakesBank", [])
    if not isinstance(mistakes, list) or len(mistakes) > 20000:
        raise APIError(422, "INVALID_BACKUP", "错题摘要格式无效")
    for mistake in mistakes:
        if (
            not isinstance(mistake, dict)
            or not isinstance(mistake.get("lessonId"), str)
            or len(mistake["lessonId"]) > 160
            or type(mistake.get("questionId")) is not int
        ):
            raise APIError(422, "INVALID_BACKUP", "错题身份格式无效")
    ids = set(grades) | {m["lessonId"] for m in mistakes}
    if any(not isinstance(key, str) or len(key) > 160 for key in ids):
        raise APIError(422, "INVALID_BACKUP", "课程 ID 格式无效")
    if any(
        len(key) > 240 or not isinstance(date, str) or len(date) > 80
        for key, date in readings.items()
    ):
        raise APIError(422, "INVALID_BACKUP", "阅读摘要格式无效")
    containers = (
        (
            await db.scalars(
                select(ContentContainer).where(
                    ContentContainer.source_id.in_(ids),
                    ContentContainer.kind.in_(["lesson", "challenge"]),
                )
            )
        ).all()
        if ids
        else []
    )
    sources = {}
    for container in containers:
        sources.setdefault(container.source_id, []).append(container)
    mapped, unknown = {}, []
    for key, grade in grades.items():
        if (
            not isinstance(grade, dict)
            or type(grade.get("stars")) is not int
            or grade["stars"] not in (1, 2, 3)
        ):
            raise APIError(422, "INVALID_BACKUP", "课程星级格式无效")
        accuracy = grade.get("accuracy")
        if type(accuracy) not in (int, float) or not 0 <= accuracy <= 1:
            raise APIError(422, "INVALID_BACKUP", "课程正确率格式无效")
        matches = sources.get(key, [])
        if len(matches) != 1:
            unknown.append({"kind": "lesson", "source_id": key, "reason": "NO_EXACT_SOURCE"})
            continue
        mapped[key] = {
            "book_id": matches[0].book_id,
            "stars": grade["stars"],
            "accuracy": accuracy,
            "completedAt": str(grade.get("completedAt", ""))[:80],
        }
    mapped_mistakes = []
    for mistake in mistakes:
        if not isinstance(mistake, dict) or type(mistake.get("questionId")) is not int:
            raise APIError(422, "INVALID_BACKUP", "错题身份格式无效")
        matches = sources.get(mistake.get("lessonId"), [])
        found = None
        if len(matches) == 1:
            revision = await db.get(ContentRevision, (matches[0].id, matches[0].current_version))
            found = (
                next(
                    (
                        ref
                        for ref in revision.question_refs
                        if ref["source_question_id"] == mistake["questionId"]
                    ),
                    None,
                )
                if revision
                else None
            )
        if not found:
            unknown.append(
                {
                    "kind": "question",
                    "source_id": mistake.get("lessonId"),
                    "question_id": mistake["questionId"],
                    "reason": "NO_EXACT_SOURCE",
                }
            )
        else:
            mapped_mistakes.append(
                {
                    "lesson_id": mistake["lessonId"],
                    "question_id": mistake["questionId"],
                    "uid": found["uid"],
                    "version": None,
                    "version_basis": "legacy_version_unknown",
                    "source": "legacy_unverified",
                }
            )
    state = await db.get(EconomyState, student.id)
    current = state.payload.get("completedLessons", {}) if state else {}
    conflicts = sorted(set(mapped) & set(current))
    cursor = await db.get(LearningCursor, student.id)
    payload = {
        "source": "legacy_unverified",
        "backup_version": 1,
        "platform": str(value.get("platform", "unknown"))[:20],
        "completedLessons": mapped,
        "mistakes": mapped_mistakes,
        "completedReadings": {str(k)[:240]: str(v)[:80] for k, v in readings.items()},
        "legacyCosmetics": {str(k)[:100]: True for k, v in cosmetics.items() if v is True},
        "equipped": {
            k: str(v)[:100]
            for k, v in data.get("equipped", {}).items()
            if k in {"mascotSkin", "uiTheme", "lessonBackdrop"} and isinstance(v, str)
        }
        if isinstance(data.get("equipped", {}), dict)
        else {},
    }
    report = {
        "mapped_lessons": len(mapped),
        "mapped_mistakes": len(mapped_mistakes),
        "unmapped": unknown,
        "conflicts": conflicts,
        "authority": "historical_summary_only",
        "rewards_imported": False,
        "limitations": [
            "旧摘要不能还原逐次作答",
            "不导入可消费余额或发放奖励",
            "云端新记录保留，本地备份不会删除",
        ],
    }
    if previous is None:
        previous = LegacyImport(
            family_id=student.family_id, student_id=student.id, source_hash=source_hash
        )
        db.add(previous)
    previous.target_revision = student.revision
    previous.target_cursor = cursor.value if cursor else 0
    previous.created_at = datetime.now(UTC)
    previous.payload, previous.report = payload, report
    await db.commit()
    return import_view(previous)


def import_view(row):
    return {
        "preview_id": str(row.id),
        "source_hash": row.source_hash,
        "revision": row.target_revision,
        "report": row.report,
        "confirmed": row.confirmed_at is not None,
    }


async def confirm(db, student, body):
    row = await db.scalar(
        select(LegacyImport).where(
            LegacyImport.id == body.preview_id, LegacyImport.student_id == student.id
        )
    )
    if row is None or row.source_hash != body.source_hash:
        raise APIError(404, "IMPORT_NOT_FOUND", "找不到该学生的导入预览")
    if row.confirmed_at:
        return import_view(row)
    cursor = await db.get(LearningCursor, student.id)
    if (
        row.target_revision != student.revision
        or body.revision != student.revision
        or row.target_cursor != (cursor.value if cursor else 0)
    ):
        raise APIError(409, "REVISION_CONFLICT", "预览后资料或学习记录已变化，请重新预览")
    if datetime.now(UTC) - row.created_at > timedelta(minutes=30):
        raise APIError(409, "IMPORT_PREVIEW_EXPIRED", "预览已过期，请重新预览")
    row.confirmed_at = datetime.now(UTC)
    student.revision += 1
    await db.commit()
    return import_view(row)
