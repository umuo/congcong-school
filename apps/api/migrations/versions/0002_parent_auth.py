"""家长、家庭成员及可撤销会话。"""

import sqlalchemy as sa
from alembic import op

revision = "0002_parent_auth"
down_revision = "0001_families"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(1024), nullable=False),
        sa.Column("nickname", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "family_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.CheckConstraint(
            "role in ('owner', 'guardian')", name="ck_family_memberships_valid_role"
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_family_memberships"),
        sa.UniqueConstraint("family_id", "user_id", name="uq_family_memberships_family_id"),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("parent_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode in ('parent', 'child')", name="ck_auth_sessions_valid_mode"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token", name="pk_auth_sessions"),
    )
    op.create_table(
        "auth_rate_limits",
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("window", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_auth_rate_limits"),
    )


def downgrade():
    op.drop_table("auth_rate_limits")
    op.drop_table("auth_sessions")
    op.drop_table("family_memberships")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
