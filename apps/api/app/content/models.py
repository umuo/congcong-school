"""内容身份独立于版本，版本行只追加，当前发布指针可更新。"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContentContainer(Base):
    __tablename__ = "content_containers"
    __table_args__ = (
        UniqueConstraint("kind", "book_id", "source_id"),
        ForeignKeyConstraint(
            ["id", "current_version"],
            ["content_revisions.container_id", "content_revisions.version"],
            name="fk_content_current_revision",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    book_id: Mapped[str] = mapped_column(ForeignKey("textbooks.id"))
    source_id: Mapped[str] = mapped_column(String(160))
    current_version: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ContentRevision(Base):
    __tablename__ = "content_revisions"
    container_id: Mapped[str] = mapped_column(ForeignKey("content_containers.id"), primary_key=True)
    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    # 原内容含转义 NUL；JSON 无损保留，JSONB 会拒绝。不要静默改写源文本。
    public_payload: Mapped[dict] = mapped_column(JSON)
    question_refs: Mapped[list] = mapped_column(JSONB)
    provenance: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionIdentity(Base):
    __tablename__ = "question_identities"
    __table_args__ = (UniqueConstraint("kind", "book_id", "source_id", "source_question_id"),)
    uid: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    book_id: Mapped[str] = mapped_column(ForeignKey("textbooks.id"))
    source_id: Mapped[str] = mapped_column(String(160))
    source_question_id: Mapped[int] = mapped_column(Integer)


class QuestionVersion(Base):
    __tablename__ = "question_versions"
    uid: Mapped[str] = mapped_column(ForeignKey("question_identities.uid"), primary_key=True)
    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    grading_rule_version: Mapped[str] = mapped_column(String(64))
    private_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
