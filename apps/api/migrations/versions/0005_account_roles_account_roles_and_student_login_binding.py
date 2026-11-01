"""三类账号、学生绑定及旧家长兼容；升级撤销旧会话。"""

import sqlalchemy as sa
from alembic import op

revision = "0005_account_roles"
down_revision = "0004_curriculum"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM auth_sessions")
    op.add_column("users", sa.Column("login_name", sa.String(320), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(16), nullable=True))
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=True))
    op.execute(
        "UPDATE users SET login_name = lower(email), role = 'parent', must_change_password = false"
    )
    for name, kind in [
        ("login_name", sa.String(320)),
        ("role", sa.String(16)),
        ("must_change_password", sa.Boolean()),
    ]:
        op.alter_column("users", name, existing_type=kind, nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(320), nullable=True)
    op.create_unique_constraint("uq_users_id", "users", ["id", "role"])
    op.create_unique_constraint("uq_users_login_name", "users", ["login_name"])
    op.create_check_constraint("valid_role", "users", "role in ('admin', 'parent', 'student')")
    op.create_table(
        "student_accounts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("user_role", sa.String(16), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("user_role = 'student'", name="student_role"),
        sa.ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "user_role"], ["users.id", "users.role"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("student_id"),
    )
    op.add_column("auth_sessions", sa.Column("principal_role", sa.String(16), nullable=False))
    op.create_foreign_key(
        "fk_auth_sessions_principal_role_users",
        "auth_sessions",
        "users",
        ["user_id", "principal_role"],
        ["id", "role"],
        ondelete="CASCADE",
    )
    op.drop_constraint("ck_auth_sessions_valid_mode", "auth_sessions", type_="check")
    op.drop_constraint("ck_auth_sessions_mode_student_context", "auth_sessions", type_="check")
    op.create_check_constraint(
        "valid_mode", "auth_sessions", "mode in ('admin', 'parent', 'child')"
    )
    op.create_check_constraint(
        "mode_student_context",
        "auth_sessions",
        "(mode = principal_role AND principal_role in ('admin', 'parent') "
        "AND student_id IS NULL AND family_id IS NULL) OR "
        "(mode = 'child' AND principal_role in ('parent', 'student') "
        "AND student_id IS NOT NULL AND family_id IS NOT NULL)",
    )
    op.add_column("family_memberships", sa.Column("user_role", sa.String(16), nullable=True))
    op.execute("UPDATE family_memberships SET user_role = 'parent'")
    op.alter_column("family_memberships", "user_role", existing_type=sa.String(16), nullable=False)
    op.create_unique_constraint("uq_family_memberships_user_id", "family_memberships", ["user_id"])
    op.create_index(
        "uq_family_owner",
        "family_memberships",
        ["family_id"],
        unique=True,
        postgresql_where=sa.text("role = 'owner'"),
    )
    op.create_foreign_key(
        "fk_family_memberships_user_role_users",
        "family_memberships",
        "users",
        ["user_id", "user_role"],
        ["id", "role"],
        ondelete="CASCADE",
    )
    op.create_check_constraint("parent_role", "family_memberships", "user_role = 'parent'")


def downgrade():
    # 新角色不能无损降级到旧家长模型；阻止误删，生产仅回滚兼容的 API。
    if op.get_bind().scalar(
        sa.text("SELECT count(*) FROM users WHERE role <> 'parent' OR email IS NULL")
    ):
        raise RuntimeError("新增角色账号存在，不能降级到仅家长模型；请使用兼容版本回滚")
    op.execute("DELETE FROM auth_sessions")
    op.drop_table("student_accounts")
    op.drop_constraint(
        "fk_family_memberships_user_role_users", "family_memberships", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("ck_family_memberships_parent_role"), "family_memberships", type_="check"
    )
    op.drop_index("uq_family_owner", table_name="family_memberships")
    op.drop_constraint("uq_family_memberships_user_id", "family_memberships", type_="unique")
    op.drop_column("family_memberships", "user_role")
    op.drop_constraint("fk_auth_sessions_principal_role_users", "auth_sessions", type_="foreignkey")
    op.drop_constraint(op.f("ck_auth_sessions_valid_mode"), "auth_sessions", type_="check")
    op.drop_constraint(
        op.f("ck_auth_sessions_mode_student_context"), "auth_sessions", type_="check"
    )
    op.create_check_constraint(
        "ck_auth_sessions_valid_mode", "auth_sessions", "mode in ('parent', 'child')"
    )
    op.create_check_constraint(
        "ck_auth_sessions_mode_student_context",
        "auth_sessions",
        "(mode = 'parent' AND student_id IS NULL AND family_id IS NULL) OR "
        "(mode = 'child' AND student_id IS NOT NULL AND family_id IS NOT NULL)",
    )
    op.drop_column("auth_sessions", "principal_role")
    op.drop_constraint("uq_users_login_name", "users", type_="unique")
    op.drop_constraint("uq_users_id", "users", type_="unique")
    op.drop_constraint(op.f("ck_users_valid_role"), "users", type_="check")
    op.alter_column("users", "email", existing_type=sa.String(320), nullable=False)
    for name in ["must_change_password", "role", "login_name"]:
        op.drop_column("users", name)
