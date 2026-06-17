"""Create quiz_questions table (US-07 / US-08, SHOULD priority)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-17
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quiz_questions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("options", JSONB, nullable=False),
        sa.Column("correct_answer", sa.String(10), nullable=False),
        sa.Column("approved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
            name="fk_quiz_questions_document_id",
        ),
    )
    op.create_index("ix_quiz_questions_document_id", "quiz_questions", ["document_id"])
    op.create_index(
        "ix_quiz_questions_approved",
        "quiz_questions",
        ["approved"],
        postgresql_where=sa.text("approved = true"),
    )


def downgrade() -> None:
    op.drop_table("quiz_questions")
