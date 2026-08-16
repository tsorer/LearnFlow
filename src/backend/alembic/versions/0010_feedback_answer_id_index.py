"""Add index on feedback.answer_id

Every other FK column in the RAG tables (query_sessions.user_id,
answers.session_id, chunks.document_id) has an index; feedback.answer_id
was missed in 0004. Needed for feedback aggregation by answer (T-32).

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-16
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_feedback_answer_id", "feedback", ["answer_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_answer_id", table_name="feedback")
