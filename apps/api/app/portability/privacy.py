import fcntl
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, inspect, select

from app.auth.models import AuthSession, StudentAccount, User
from app.curriculum.models import StudentSubject, TextbookSelection
from app.diagnostics.service import export_family_diagnostics
from app.errors import APIError
from app.families.models import Family, Membership
from app.learning.models import (
    Attempt,
    EconomyState,
    LearningEvent,
    LearningSession,
    RewardClaim,
    RewardLedger,
)
from app.portability.models import DeletionReceipt, LegacyImport
from app.students.models import Student


def public_row(row):
    return {column.key: getattr(row, column.key) for column in inspect(type(row)).columns}


async def export_family(db, family_id):
    family = await db.get(Family, family_id)
    students = (await db.scalars(select(Student).where(Student.family_id == family_id))).all()
    ids = [student.id for student in students]
    data = {"family": public_row(family), "students": [public_row(s) for s in students]}
    # 明确白名单；绝不导出 User ORM 的认证内部列、令牌或速率限制记录。
    for name, model in [
        ("subjects", StudentSubject),
        ("textbook_selections", TextbookSelection),
        ("sessions", LearningSession),
        ("attempts", Attempt),
        ("events", LearningEvent),
        ("progress", EconomyState),
        ("rewards", RewardLedger),
        ("claims", RewardClaim),
        ("legacy_imports", LegacyImport),
    ]:
        statement = select(model).where(model.student_id.in_(ids))
        if model is LegacyImport:
            statement = statement.where(LegacyImport.confirmed_at.is_not(None))
        data[name] = [public_row(row) for row in (await db.scalars(statement)).all()]
    bindings = (
        await db.execute(
            select(
                StudentAccount.student_id, User.id, User.login_name, User.nickname, Student.avatar
            )
            .join(Student, Student.id == StudentAccount.student_id)
            .join(User, User.id == StudentAccount.user_id)
            .where(StudentAccount.family_id == family_id)
        )
    ).all()
    data["student_accounts"] = [dict(row._mapping) for row in bindings]
    members = (
        await db.execute(
            select(User.id, User.login_name, User.nickname, Membership.role, User.avatar)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.family_id == family_id)
        )
    ).all()
    data["family_members"] = [dict(row._mapping) for row in members]
    data["diagnostics"] = await export_family_diagnostics(db, family, students)
    return jsonable_encoder(
        {
            "schema": "cstf-family-export",
            "version": 1,
            "exported_at": datetime.now(UTC),
            "data": data,
        }
    )


def backup_policy(settings):
    return {
        "external_backups_enabled": settings.backup_retention_days > 0,
        "retention_days": settings.backup_retention_days,
        "notice": (
            f"活动数据立即删除。运营者配置的备份最多保留 {settings.backup_retention_days} 天，"
            "恢复前须重放删除清单。"
            if settings.backup_retention_days
            else "活动数据立即删除。当前部署不自动建立外部备份；请同时清理自己的下载和设备副本。"
        ),
    }


def journal(settings, kind, target):
    now = datetime.now(UTC)
    record = {
        "kind": kind,
        "id": str(target),
        "requested_at": now.isoformat(),
        "expires_at": (now + timedelta(days=settings.backup_retention_days + 1)).isoformat(),
    }
    path = settings.deletion_journal
    path.parent.mkdir(parents=True, exist_ok=True)
    # 在数据库提交前持久化删除意图，崩溃恢复也不得复活已确认删除的资料。
    fd = os.open(path, os.O_APPEND | os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, (json.dumps(record) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    return now + timedelta(days=settings.backup_retention_days + 1)


async def erase_student(db, student_id):
    # 先锁账号，再锁学生，与认证写入的锁顺序一致。
    users = list(
        await db.scalars(
            select(StudentAccount.user_id).where(StudentAccount.student_id == student_id)
        )
    )
    if users:
        await db.scalars(select(User).where(User.id.in_(users)).order_by(User.id).with_for_update())
    student = await db.scalar(select(Student).where(Student.id == student_id).with_for_update())
    if student is None:
        return
    # 锁学生后再核对绑定，包含并发开通后刚提交的账号。
    users = list(
        await db.scalars(
            select(StudentAccount.user_id).where(StudentAccount.student_id == student_id)
        )
    )
    await db.execute(delete(AuthSession).where(AuthSession.student_id == student_id))
    if users:
        await db.execute(delete(User).where(User.id.in_(users), User.role == "student"))
    await db.execute(delete(Student).where(Student.id == student_id))


async def erase_family(db, family_id):
    parents = list(
        await db.scalars(select(Membership.user_id).where(Membership.family_id == family_id))
    )
    students = list(await db.scalars(select(Student.id).where(Student.family_id == family_id)))
    users = list(
        await db.scalars(
            select(StudentAccount.user_id).where(StudentAccount.family_id == family_id)
        )
    )
    if users or parents:
        await db.scalars(
            select(User).where(User.id.in_(users + parents)).order_by(User.id).with_for_update()
        )
    for student in students:
        await erase_student(db, student)
    await db.execute(delete(Family).where(Family.id == family_id))
    if parents:
        await db.execute(delete(User).where(User.id.in_(parents), User.role == "parent"))


async def delete_target(db, who, kind, target, key, settings):
    target_hash = hashlib.sha256(f"{kind}:{target}".encode()).hexdigest()
    old = await db.get(DeletionReceipt, (who.user.id, key))
    if old:
        if old.target_hash != target_hash:
            raise APIError(409, "IDEMPOTENCY_CONFLICT", "同一删除标识不能用于不同范围")
        return
    expires = journal(settings, kind, target)
    principal = who.user.id
    if kind == "student":
        await erase_student(db, target)
    else:
        await erase_family(db, target)
    db.add(
        DeletionReceipt(
            principal_id=principal, key=key, target_hash=target_hash, expires_at=expires
        )
    )
    await db.commit()


async def replay_deletions(db, settings):
    path = settings.deletion_journal
    if not path.exists():
        return 0
    now, count = datetime.now(UTC), 0
    # 不丢弃到期清单前先重放，避免恢复了超期备份时留下资料。
    for line in path.read_text().splitlines():
        item = json.loads(line)
        if item["kind"] == "student":
            await erase_student(db, UUID(item["id"]))
        elif item["kind"] == "family":
            await erase_family(db, UUID(item["id"]))
        else:
            raise ValueError("Unknown deletion journal kind; keep access closed")
        count += 1
    await db.execute(delete(DeletionReceipt).where(DeletionReceipt.expires_at < now))
    await db.commit()
    # 清理清单应在备份到期确认后离线执行；不在活跃写入期间重写日志。
    return count


def purge_expired_journal(settings):
    path = settings.deletion_journal
    if not path.exists():
        return 0
    now = datetime.now(UTC)
    with path.open("r+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        rows = [json.loads(line) for line in stream if line.strip()]
        keep = [row for row in rows if datetime.fromisoformat(row["expires_at"]) >= now]
        stream.seek(0)
        stream.write("".join(json.dumps(row) + "\n" for row in keep))
        stream.truncate()
        stream.flush()
        os.fsync(stream.fileno())
    return len(rows) - len(keep)
