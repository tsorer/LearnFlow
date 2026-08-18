"""Extend the config value constraint to the retrieval parameters

T-17 introduces six new `config` keys. ADR-008 (Nachtrag 2026-08-16) puts the
strictness in the database rather than in the reader, because there are two
write paths — the admin API (T-37) and the `psql` path the pilot checklist
prescribes — and only the database sits below both. `0009` established that for
the confidence bands and notes the CASE block is meant to be extended; this is
that extension.

A new migration rather than an edit to `0009`: that revision has already run on
every existing database, so the constraint is dropped and recreated here.

Two value shapes, because the keys are not all thresholds:

* `similarity_threshold`, `min_retrieval_confidence`, `min_citation_coverage`
  are similarities and ratios — the unit interval, same regex as `0009`.
* `retrieval_top_k`, `context_top_n`, `rrf_k` are counts. `0` would retrieve
  nothing and turn every question into a refusal, so the floor is 1.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-18
"""

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

CHECK_NAME = "ck_config_confidence_threshold_value"

# Unchanged from 0009 — repeated rather than imported so this migration keeps
# describing the state it creates, even if 0009 is ever squashed away.
NUMERIC_UNIT_INTERVAL = r"^(0(\.[0-9]+)?|1(\.0+)?)$"

# No leading zero, no sign, no decimal point: 1, 20, 60 — rejected: 0, -3, 2.5.
POSITIVE_INTEGER = r"^[1-9][0-9]*$"

UNIT_INTERVAL_KEYS = (
    "confidence_threshold_high",
    "confidence_threshold_medium",
    "similarity_threshold",
    "min_retrieval_confidence",
    "min_citation_coverage",
)

COUNT_KEYS = ("retrieval_top_k", "context_top_n", "rrf_k")

OLD_CHECK = (
    f"ALTER TABLE config ADD CONSTRAINT {CHECK_NAME} CHECK ("
    "  CASE"
    "    WHEN key IN ('confidence_threshold_high', 'confidence_threshold_medium')"
    f"    THEN value ~ '{NUMERIC_UNIT_INTERVAL}'"
    "    ELSE true"
    "  END"
    ")"
)


def _quoted(keys: tuple[str, ...]) -> str:
    return ", ".join(f"'{key}'" for key in keys)


NEW_CHECK = (
    f"ALTER TABLE config ADD CONSTRAINT {CHECK_NAME} CHECK ("
    "  CASE"
    f"    WHEN key IN ({_quoted(UNIT_INTERVAL_KEYS)})"
    f"    THEN value ~ '{NUMERIC_UNIT_INTERVAL}'"
    f"    WHEN key IN ({_quoted(COUNT_KEYS)})"
    f"    THEN value ~ '{POSITIVE_INTEGER}'"
    "    ELSE true"
    "  END"
    ")"
)


def upgrade() -> None:
    # A pilot database hand-edited into a bad state fails here, which is the
    # intended moment to notice — same trade-off as 0009.
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(NEW_CHECK))


def downgrade() -> None:
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(OLD_CHECK))
