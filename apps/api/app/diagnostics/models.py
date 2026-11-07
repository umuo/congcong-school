"""稳定知识点目录、跨版受控关联与不可变题目版本映射模型。"""

from datetime import datetime

from sqlalchemy import (
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


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    __table_args__ = (UniqueConstraint("book_id", "code"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_code: Mapped[str] = mapped_column(ForeignKey("subjects.code"), index=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("textbooks.id"), index=True)
    unit_number: Mapped[int] = mapped_column(Integer)
    unit_title: Mapped[str] = mapped_column(String(200))
    lesson_id: Mapped[str | None] = mapped_column(String(160))
    scope_kind: Mapped[str] = mapped_column(String(32))
    code: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(String(1200))
    sort_order: Mapped[int] = mapped_column(Integer)
    provenance: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class KnowledgePointRelation(Base):
    __tablename__ = "knowledge_point_relations"
    source_kp_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True
    )
    target_kp_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    relation_kind: Mapped[str] = mapped_column(String(48), primary_key=True)
    provenance: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QuestionKnowledgeLink(Base):
    __tablename__ = "question_knowledge_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["question_uid", "question_version"],
            ["question_versions.uid", "question_versions.version"],
        ),
    )
    question_uid: Mapped[str] = mapped_column(String(64), primary_key=True)
    question_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    kp_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    mapping_role: Mapped[str] = mapped_column(String(32))
    mapping_source: Mapped[str] = mapped_column(String(48))
    mapping_version: Mapped[str] = mapped_column(String(32))
    provenance: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
