"""服务端固定题目会话、逐次作答与学生内追加事件。"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
        UniqueConstraint("student_id", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column()
    student_id: Mapped[UUID] = mapped_column()
    kind: Mapped[str] = mapped_column(String(32))
    book_id: Mapped[str | None] = mapped_column(String(120))
    source_id: Mapped[str | None] = mapped_column(String(160))
    sources: Mapped[list] = mapped_column(JSONB)
    question_refs: Mapped[list] = mapped_column(JSONB)
    checkpoint: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


class Attempt(Base):
    __tablename__ = "learning_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_id", "session_id"],
            ["learning_sessions.student_id", "learning_sessions.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["question_uid", "question_version"],
            ["question_versions.uid", "question_versions.version"],
        ),
        UniqueConstraint("session_id", "ordinal"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column()
    session_id: Mapped[UUID] = mapped_column()
    ordinal: Mapped[int] = mapped_column(Integer)
    question_uid: Mapped[str] = mapped_column(String(64))
    question_version: Mapped[str] = mapped_column(String(64))
    answer: Mapped[str] = mapped_column(JSON)
    correct: Mapped[bool] = mapped_column(Boolean)
    first_attempt: Mapped[bool] = mapped_column(Boolean)
    grading_rule_version: Mapped[str] = mapped_column(String(64))
    client_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    declared_duration_ms: Mapped[int] = mapped_column(Integer)
    evidence: Mapped[dict] = mapped_column(JSON)


class LearningCursor(Base):
    __tablename__ = "learning_cursors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
    )
    student_id: Mapped[UUID] = mapped_column(primary_key=True)
    family_id: Mapped[UUID] = mapped_column()
    value: Mapped[int] = mapped_column(BigInteger, default=0)


class LearningEvent(Base):
    __tablename__ = "learning_events"
    __table_args__ = (
        ForeignKeyConstraint(["student_id"], ["learning_cursors.student_id"], ondelete="CASCADE"),
    )
    student_id: Mapped[UUID] = mapped_column(primary_key=True)
    cursor: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON)
    client_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


class LearningReceipt(Base):
    __tablename__ = "learning_receipts"
    __table_args__ = (ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),)
    student_id: Mapped[UUID] = mapped_column(primary_key=True)
    operation: Mapped[str] = mapped_column(String(80), primary_key=True)
    key: Mapped[UUID] = mapped_column(primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)


class EconomyState(Base):
    __tablename__ = "economy_states"
    __table_args__ = (
        ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
    )
    student_id: Mapped[UUID] = mapped_column(primary_key=True)
    family_id: Mapped[UUID] = mapped_column()
    revision: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSONB)


class RewardLedger(Base):
    __tablename__ = "reward_ledger"
    __table_args__ = (
        ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        UniqueConstraint("student_id", "claim_key"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column()
    claim_key: Mapped[str] = mapped_column(String(240))
    rule_version: Mapped[str] = mapped_column(String(64))
    xp_delta: Mapped[int] = mapped_column(Integer)
    gems_delta: Mapped[int] = mapped_column(Integer)
    changes: Mapped[list] = mapped_column(JSONB)
    result: Mapped[dict] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


class RewardClaim(Base):
    __tablename__ = "reward_claims"
    __table_args__ = (
        ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["ledger_id"], ["reward_ledger.id"], ondelete="CASCADE"),
    )
    student_id: Mapped[UUID] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(240), primary_key=True)
    ledger_id: Mapped[UUID] = mapped_column()
