"""Seed chunking parameters into the config table

Chunk size and overlap live in `config` (like the retrieval thresholds from
0004) so they can be calibrated in the spike without a deployment (ADR-007).
Values are the ADR-007 start values.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

ROWS = [
    ("chunk_size", "512", "Target chunk size in tokens (ADR-007)"),
    ("chunk_overlap", "64", "Overlap between consecutive chunks in tokens (ADR-007)"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for key, value, description in ROWS:
        bind.execute(
            sa.text(
                "INSERT INTO config (key, value, description) VALUES (:key, :value, :description)"
            ),
            {"key": key, "value": value, "description": description},
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM config WHERE key IN ('chunk_size', 'chunk_overlap')"),
    )
