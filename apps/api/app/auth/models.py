from datetime import datetime
from uuid import UUID

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role in ('admin', 'parent', 'student')", name="valid_role"),
        UniqueConstraint("id", "role"),
    )

    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True, nullable=True)
    login_name: Mapped[str] = mapped_column(String(320), unique=True)
    role: Mapped[str] = mapped_column(String(16), default="parent")
    must_change_password: Mapped[bool] = mapped_column(default=False)
    nickname: Mapped[str] = mapped_column(String(80))
    avatar: Mapped[str | None] = mapped_column(String(32))
    avatar_revision: Mapped[int | None] = mapped_column(Integer)


class StudentAccount(Base):
    __tablename__ = "student_accounts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["user_id", "user_role"], ["users.id", "users.role"], ondelete="CASCADE"
        ),
        CheckConstraint("user_role = 'student'", name="student_role"),
    )

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    user_role: Mapped[str] = mapped_column(String(16), default="student")
    family_id: Mapped[UUID] = mapped_column(Uuid)
    student_id: Mapped[UUID] = mapped_column(Uuid, unique=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint("mode in ('admin', 'parent', 'child')", name="valid_mode"),
        ForeignKeyConstraint(
            ["user_id", "principal_role"],
            ["users.id", "users.role"],
            name="fk_auth_sessions_principal_role_users",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
        CheckConstraint(
            "(mode = principal_role AND principal_role in ('admin', 'parent') "
            "AND student_id IS NULL AND family_id IS NULL) OR "
            "(mode = 'child' AND principal_role in ('parent', 'student') "
            "AND student_id IS NOT NULL AND family_id IS NOT NULL)",
            name="mode_student_context",
        ),
    )

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    principal_role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    csrf_hash: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(10), default="parent")
    student_id: Mapped[UUID | None] = mapped_column(Uuid)
    family_id: Mapped[UUID | None] = mapped_column(Uuid)
    parent_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer)
