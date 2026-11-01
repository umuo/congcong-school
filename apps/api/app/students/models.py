from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("family_id", "id"),
        CheckConstraint("grade between 1 and 12", name="valid_grade"),
        CheckConstraint("daily_goal_minutes between 1 and 240", name="valid_daily_goal"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    nickname: Mapped[str] = mapped_column(String(80))
    avatar: Mapped[str] = mapped_column(String(32), default="panda")
    birth_month: Mapped[str | None] = mapped_column(String(7))
    province: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(80))
    school: Mapped[str | None] = mapped_column(String(120))
    school_stage: Mapped[str] = mapped_column(String(16), default="primary")
    grade: Mapped[int] = mapped_column(Integer, default=1)
    school_year: Mapped[str | None] = mapped_column(String(9))
    semester: Mapped[str] = mapped_column(String(16), default="up")
    daily_goal_minutes: Mapped[int] = mapped_column(Integer, default=20)
    parent_notes: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1)
