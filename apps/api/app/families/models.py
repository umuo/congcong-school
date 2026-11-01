from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Family(Base):
    __tablename__ = "families"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    __tablename__ = "family_memberships"
    __table_args__ = (
        UniqueConstraint("family_id", "user_id"),
        UniqueConstraint("user_id"),
        ForeignKeyConstraint(
            ["user_id", "user_role"],
            ["users.id", "users.role"],
            name="fk_family_memberships_user_role_users",
            ondelete="CASCADE",
        ),
        CheckConstraint("user_role = 'parent'", name="parent_role"),
        Index("uq_family_owner", "family_id", unique=True, postgresql_where=text("role = 'owner'")),
        CheckConstraint("role in ('owner', 'guardian')", name="valid_role"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user_role: Mapped[str] = mapped_column(String(16), default="parent")
    role: Mapped[str] = mapped_column(String(16), default="owner")
