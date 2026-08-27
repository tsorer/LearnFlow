"""Give quiz_questions the fields the review needs (T-33, T-34, US-07/US-08)

`0005` created the table on a guess: `approved` as a boolean, and no reference
to the passage a question was generated from. Both fall short of what T-34 asks
for, and the reason is visible in the ticket history -- the schema was cut
before the endpoint that fills it existed. Nothing ever wrote to the table, so
this migration is a schema change and not a data migration, but it is written to
survive rows anyway.

Three decisions are worth spelling out here, because the column definitions are
the only place they are enforced:

`chunk_id` is nullable with ON DELETE SET NULL, not CASCADE. Replacing a
document deletes the chunks of the old version (T-15, documents.py `_replace`),
and CASCADE would take Stefan's reviewed questions with them. The decision on
#40 is that they survive and lose their approval instead -- so the reference
goes to NULL, and `chunk_id IS NULL` becomes the marker "generated from a
version that no longer exists".

`source_excerpt` is the copy that makes that survivable. Once `chunk_id` is
NULL, nothing else holds the passage the question was written from, and the
review dashboard (US-07, "inklusive der Quellen-Passage") would have nothing to
show.

`status` replaces `approved` and defaults to 'pending'. Fail-closed by
construction (ADR-008): a row that reaches the table without anyone naming a
status is not an approved one. The CHECK is what makes the three values of
T-34 a fact about the database rather than a convention in the application --
there are two writers, this endpoint and the edit path of T-35.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

CHECK_STATUS = "ck_quiz_questions_status"
CHECK_OPTIONS = "ck_quiz_questions_options"
FK_CHUNK = "fk_quiz_questions_chunk_id"


def upgrade() -> None:
    op.add_column("quiz_questions", sa.Column("chunk_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        FK_CHUNK, "quiz_questions", "chunks", ["chunk_id"], ["id"], ondelete="SET NULL"
    )

    # Added with a default and stripped of it again: the column is NOT NULL, and
    # a table that did hold rows has no value to put in them otherwise. The
    # default is not kept, because "" is not a passage -- every writer has to
    # supply one.
    for column in ("source_excerpt", "explanation"):
        op.add_column(
            "quiz_questions", sa.Column(column, sa.Text, nullable=False, server_default="")
        )
        op.alter_column("quiz_questions", column, server_default=None)

    op.add_column(
        "quiz_questions",
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "quiz_questions", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute(
        "UPDATE quiz_questions SET status = CASE WHEN approved THEN 'approved' ELSE 'pending' END"
    )

    op.drop_index("ix_quiz_questions_approved", table_name="quiz_questions")
    op.drop_column("quiz_questions", "approved")
    op.create_index("ix_quiz_questions_status", "quiz_questions", ["status"])

    op.create_check_constraint(
        CHECK_STATUS, "quiz_questions", "status IN ('pending', 'approved', 'rejected')"
    )
    # Four options is an acceptance criterion of T-33, not a rendering detail:
    # a question with three of them is not a multiple-choice question the UI of
    # T-36 can lay out.
    op.create_check_constraint(
        CHECK_OPTIONS, "quiz_questions", "jsonb_array_length(options) = 4"
    )


def downgrade() -> None:
    op.drop_constraint(CHECK_OPTIONS, "quiz_questions", type_="check")
    op.drop_constraint(CHECK_STATUS, "quiz_questions", type_="check")

    op.add_column(
        "quiz_questions",
        sa.Column("approved", sa.Boolean, nullable=False, server_default="false"),
    )
    op.execute("UPDATE quiz_questions SET approved = (status = 'approved')")

    op.drop_index("ix_quiz_questions_status", table_name="quiz_questions")
    op.create_index(
        "ix_quiz_questions_approved",
        "quiz_questions",
        ["approved"],
        postgresql_where=sa.text("approved = true"),
    )

    op.drop_column("quiz_questions", "approved_at")
    op.drop_column("quiz_questions", "status")
    op.drop_column("quiz_questions", "explanation")
    op.drop_column("quiz_questions", "source_excerpt")
    op.drop_constraint(FK_CHUNK, "quiz_questions", type_="foreignkey")
    op.drop_column("quiz_questions", "chunk_id")
