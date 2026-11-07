"""knowledge points catalog, controlled relations, and question version links"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_knowledge_diagnostics"
down_revision = "0011_avatars"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_points",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject_code", sa.String(length=64), nullable=False),
        sa.Column("book_id", sa.String(length=120), nullable=False),
        sa.Column("unit_number", sa.Integer(), nullable=False),
        sa.Column("unit_title", sa.String(length=200), nullable=False),
        sa.Column("lesson_id", sa.String(length=160), nullable=True),
        sa.Column("scope_kind", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=1200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["book_id"], ["textbooks.id"], name=op.f("fk_knowledge_points_book_id_textbooks")
        ),
        sa.ForeignKeyConstraint(
            ["subject_code"],
            ["subjects.code"],
            name=op.f("fk_knowledge_points_subject_code_subjects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_points")),
        sa.UniqueConstraint("book_id", "code", name=op.f("uq_knowledge_points_book_id")),
    )
    op.create_index(
        op.f("ix_knowledge_points_book_id"), "knowledge_points", ["book_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_points_subject_code"),
        "knowledge_points",
        ["subject_code"],
        unique=False,
    )
    op.create_table(
        "knowledge_point_relations",
        sa.Column("source_kp_id", sa.String(length=64), nullable=False),
        sa.Column("target_kp_id", sa.String(length=64), nullable=False),
        sa.Column("relation_kind", sa.String(length=48), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_kp_id"],
            ["knowledge_points.id"],
            name=op.f("fk_knowledge_point_relations_source_kp_id_knowledge_points"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_kp_id"],
            ["knowledge_points.id"],
            name=op.f("fk_knowledge_point_relations_target_kp_id_knowledge_points"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "source_kp_id",
            "target_kp_id",
            "relation_kind",
            name=op.f("pk_knowledge_point_relations"),
        ),
    )
    op.create_index(
        op.f("ix_knowledge_point_relations_target_kp_id"),
        "knowledge_point_relations",
        ["target_kp_id"],
        unique=False,
    )
    op.create_table(
        "question_knowledge_links",
        sa.Column("question_uid", sa.String(length=64), nullable=False),
        sa.Column("question_version", sa.String(length=64), nullable=False),
        sa.Column("kp_id", sa.String(length=64), nullable=False),
        sa.Column("mapping_role", sa.String(length=32), nullable=False),
        sa.Column("mapping_source", sa.String(length=48), nullable=False),
        sa.Column("mapping_version", sa.String(length=32), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["kp_id"],
            ["knowledge_points.id"],
            name=op.f("fk_question_knowledge_links_kp_id_knowledge_points"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_uid", "question_version"],
            ["question_versions.uid", "question_versions.version"],
            name=op.f("fk_question_knowledge_links_question_uid_question_versions"),
        ),
        sa.PrimaryKeyConstraint(
            "question_uid",
            "question_version",
            "kp_id",
            name=op.f("pk_question_knowledge_links"),
        ),
    )
    op.create_index(
        op.f("ix_question_knowledge_links_kp_id"),
        "question_knowledge_links",
        ["kp_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_question_knowledge_links_kp_id"), table_name="question_knowledge_links")
    op.drop_table("question_knowledge_links")
    op.drop_index(
        op.f("ix_knowledge_point_relations_target_kp_id"),
        table_name="knowledge_point_relations",
    )
    op.drop_table("knowledge_point_relations")
    op.drop_index(op.f("ix_knowledge_points_subject_code"), table_name="knowledge_points")
    op.drop_index(op.f("ix_knowledge_points_book_id"), table_name="knowledge_points")
    op.drop_table("knowledge_points")
