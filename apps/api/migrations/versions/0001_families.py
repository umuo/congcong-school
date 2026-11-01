"""建立家庭根实体。"""

import sqlalchemy as sa
from alembic import op

revision = "0001_families"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "families",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_families"),
    )


def downgrade():
    op.drop_table("families")
