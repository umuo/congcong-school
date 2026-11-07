"""legacy import provenance and bounded deletion receipts"""

import sqlalchemy as sa
from alembic import op

revision = "0010_portability"
down_revision = "0009_economy"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "legacy_imports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("target_revision", sa.Integer(), nullable=False),
        sa.Column("target_cursor", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["family_id", "student_id"], ["students.family_id", "students.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("student_id", "source_hash"),
    )
    op.create_table(
        "deletion_receipts",
        sa.Column("principal_id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.Uuid(), primary_key=True),
        sa.Column("target_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("deletion_receipts")
    op.drop_table("legacy_imports")
