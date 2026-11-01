from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Subject(Base):
    __tablename__ = "subjects"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))


class Textbook(Base):
    __tablename__ = "textbooks"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    subject_code: Mapped[str] = mapped_column(ForeignKey("subjects.code"))
    title: Mapped[str] = mapped_column(String(300))
    grade: Mapped[int] = mapped_column(Integer)
    school_stage: Mapped[str] = mapped_column(String(16), default="primary")
    school_system: Mapped[str] = mapped_column(String(16))
    semester: Mapped[str] = mapped_column(String(16))
    publisher_label: Mapped[str | None] = mapped_column(String(120))
    publisher: Mapped[str | None] = mapped_column(String(160))
    edition_label: Mapped[str | None] = mapped_column(String(120))
    source_edition: Mapped[str | None] = mapped_column(String(160))
    source_printing: Mapped[str | None] = mapped_column(String(160))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    isbn: Mapped[str | None] = mapped_column(String(32))
    supersedes: Mapped[str | None] = mapped_column(String(120))
    superseded_by: Mapped[str | None] = mapped_column(String(120))
    units: Mapped[list] = mapped_column(JSONB)
    provenance: Mapped[dict] = mapped_column(JSONB)
    content_revision: Mapped[str] = mapped_column(String(64))


class StudentSubject(Base):
    __tablename__ = "student_subjects"
    __table_args__ = (
        ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
    )
    student_id: Mapped[UUID] = mapped_column(primary_key=True)
    family_id: Mapped[UUID] = mapped_column()
    subject_code: Mapped[str] = mapped_column(ForeignKey("subjects.code"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean)


class TextbookSelection(Base):
    __tablename__ = "textbook_selections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
        Index(
            "uq_active_textbook_selection",
            "student_id",
            "subject_code",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column()
    family_id: Mapped[UUID] = mapped_column()
    subject_code: Mapped[str] = mapped_column(ForeignKey("subjects.code"))
    book_id: Mapped[str] = mapped_column(ForeignKey("textbooks.id"))
    current_unit_number: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot: Mapped[dict] = mapped_column(JSONB)
