"""Record the self-check verdict on the answer

The calibration ADR-009 owes the thresholds needs to know which answers stage 3
looked at and what it decided — a verdict that only ever appeared in the
admin-only debug response is gone the moment the request ends.

Nullable, and the NULL means something, exactly as `citation_coverage` does
(ADR-008, Nachtrag 2026-08-20): NULL is "stage 3 did not run", which is the
normal case, because the stage only fires inside the trigger band. `false` is
"ran and found uncovered statements". Defaulting to `false` would merge those
two into one value and make every skipped stage look like a failed one.

No `self_check_verdict` text column alongside it: the model's wording is
material for debugging a single request, not a fact worth keeping about every
answer, and it would put generated prose into a table whose `answer_text` is
deliberately NULL for suppressed answers.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-22
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("answers", sa.Column("self_check_passed", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("answers", "self_check_passed")
