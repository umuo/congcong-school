"""普通账号首次及重置后不强制改密；保留管理员首次改密。"""

from alembic import op

revision = "0006_regular_password_policy"
down_revision = "0005_account_roles"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE users SET must_change_password = false WHERE role IN ('parent', 'student')")


def downgrade():
    # 无法还原哪些普通账号曾改过密码，不推测或重新强迫用户改密。
    pass
