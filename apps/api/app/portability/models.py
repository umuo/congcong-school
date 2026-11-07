from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKeyConstraint, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LegacyImport(Base):
    __tablename__ = "legacy_imports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
        UniqueConstraint("student_id", "source_hash"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column()
    student_id: Mapped[UUID] = mapped_column()
    source_hash: Mapped[str] = mapped_column(String(64))
    target_revision: Mapped[int] = mapped_column(Integer)
    target_cursor: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeletionReceipt(Base):
    __tablename__ = "deletion_receipts"
    principal_id: Mapped[UUID] = mapped_column(primary_key=True)
    key: Mapped[UUID] = mapped_column(primary_key=True)
    target_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
