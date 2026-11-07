"""Account avatars; student accounts retain their single Student source."""

import sqlalchemy as sa
from alembic import op

revision = "0011_avatars"
down_revision = "0010_portability"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("avatar", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("avatar_revision", sa.Integer(), nullable=True))
    op.execute("UPDATE users SET avatar = 'panda', avatar_revision = 1 WHERE role != 'student'")


def downgrade():
    op.drop_column("users", "avatar_revision")
    op.drop_column("users", "avatar")
