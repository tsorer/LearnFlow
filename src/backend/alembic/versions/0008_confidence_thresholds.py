"""Seed the composite confidence band thresholds into the config table

ADR-008 maps the displayed composite confidence onto three bands (Hoch /
Mittel / Niedrig-unterdrückt). The band limits live in `config` like every
other threshold so they can be recalibrated after the pilot without a
deployment (US-02, US-11). Values are the start values from the pilot
checklist.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

# Fail-closed reading (ADR-008): score >= high -> 'Hoch',
# score >= medium -> 'Mittel', anything below medium is suppressed.
ROWS = [
    (
        "confidence_threshold_high",
        "0.75",
        "Composite confidence at or above this shows band 'Hoch' (ADR-008, US-02)",
    ),
    (
        "confidence_threshold_medium",
        "0.45",
        "Composite confidence below this is suppressed (ADR-008, US-02)",
    ),
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
        sa.text(
            "DELETE FROM config "
            "WHERE key IN ('confidence_threshold_high', 'confidence_threshold_medium')"
        ),
    )
