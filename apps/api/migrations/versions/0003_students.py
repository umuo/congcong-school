"""学生档案和会话中的家庭学生一致性约束。"""

import sqlalchemy as sa
from alembic import op

revision = "0003_students"
down_revision = "0002_parent_auth"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "students",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("nickname", sa.String(80), nullable=False),
        sa.Column("avatar", sa.String(32), nullable=False),
        sa.Column("birth_month", sa.String(7), nullable=True),
        sa.Column("province", sa.String(80), nullable=True),
        sa.Column("city", sa.String(80), nullable=True),
        sa.Column("school", sa.String(120), nullable=True),
        sa.Column("school_stage", sa.String(16), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("school_year", sa.String(9), nullable=True),
        sa.Column("semester", sa.String(16), nullable=False),
        sa.Column("daily_goal_minutes", sa.Integer(), nullable=False),
        sa.Column("parent_notes", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_students"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("family_id", "id", name="uq_students_family_id"),
        sa.CheckConstraint("grade between 1 and 12", name="ck_students_valid_grade"),
        sa.CheckConstraint(
            "daily_goal_minutes between 1 and 240", name="ck_students_valid_daily_goal"
        ),
    )
    op.add_column("auth_sessions", sa.Column("family_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_auth_sessions_family_id_students",
        "auth_sessions",
        "students",
        ["family_id", "student_id"],
        ["family_id", "id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "ck_auth_sessions_mode_student_context",
        "auth_sessions",
        "(mode = 'parent' AND student_id IS NULL AND family_id IS NULL) OR "
        "(mode = 'child' AND student_id IS NOT NULL AND family_id IS NOT NULL)",
    )


def downgrade():
    op.drop_constraint("ck_auth_sessions_mode_student_context", "auth_sessions", type_="check")
    op.drop_constraint("fk_auth_sessions_family_id_students", "auth_sessions", type_="foreignkey")
    op.drop_column("auth_sessions", "family_id")
    op.drop_table("students")
