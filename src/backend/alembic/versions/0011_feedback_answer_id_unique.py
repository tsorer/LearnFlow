"""Make feedback.answer_id unique -- one rating per answer

A retry after a timeout, a second tab, or a component remount previously
wrote a second, unrelated row for the same answer -- indistinguishable from
a genuine second opinion once pseudonymised, and inflating T-32's
aggregation. The endpoint now upserts against this index as the ON CONFLICT
arbiter (review on #81).

Recreated in place, same name: `mapped_column(unique=True, index=True)`
(Feedback.answer_id) makes SQLAlchemy declare a single unique *index* named
ix_feedback_answer_id, not a separately named constraint -- matching that
keeps the model's table metadata and the actual schema in agreement.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-16
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_feedback_answer_id", table_name="feedback")
    op.create_index("ix_feedback_answer_id", "feedback", ["answer_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_feedback_answer_id", table_name="feedback")
    op.create_index("ix_feedback_answer_id", "feedback", ["answer_id"], unique=False)
