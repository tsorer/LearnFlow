"""Enforce the confidence band thresholds in the database

A broken threshold must be rejected where it is written, not guessed at where
it is read (ADR-008, Nachtrag 2026-08-16, Issue #73). There are two write
paths — the admin API (T-37) and the direct `psql` path the pilot checklist
prescribes — and only the database sits below both.

Two mechanisms, because one does not cover the other's case:

* `CHECK` for the per-row part (numeric, within [0, 1]). Row-local, immediate.
* `CONSTRAINT TRIGGER` for `medium <= high`. That invariant spans two rows,
  and a `CHECK` in PostgreSQL is per row and may not use subqueries.
  Deferred to commit so both values can be set in one transaction in any
  order.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-16
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

CHECK_NAME = "ck_config_confidence_threshold_value"
TRIGGER_NAME = "trg_config_confidence_band_order"
FUNCTION_NAME = "config_check_confidence_band_order"

# Form and range in a single regex on the text value. Deliberately not
# `value ~ '^[0-9.]+$' AND value::numeric BETWEEN 0 AND 1`: PostgreSQL does not
# guarantee the evaluation order of an `AND`, so the cast may run on a value the
# regex would have rejected and surface as a cast error instead of a constraint
# violation. Accepted: 0, 0.45, 1, 1.0 — rejected: 0,45 (German decimal comma),
# 1.5, -0.1, 'hoch', '' .
NUMERIC_UNIT_INTERVAL = r"^(0(\.[0-9]+)?|1(\.0+)?)$"


def upgrade() -> None:
    # Existing rows must satisfy the constraint before it is added. The seeded
    # start values do; a pilot database that was hand-edited into a bad state
    # fails the migration here, which is the intended moment to notice.
    op.execute(
        sa.text(
            f"ALTER TABLE config ADD CONSTRAINT {CHECK_NAME} CHECK ("
            "  CASE"
            "    WHEN key IN ('confidence_threshold_high', 'confidence_threshold_medium')"
            f"    THEN value ~ '{NUMERIC_UNIT_INTERVAL}'"
            "    ELSE true"
            "  END"
            ")"
        )
    )

    # No WHEN clause on the trigger: it fires for INSERT, UPDATE and DELETE, and
    # a WHEN referencing NEW is invalid on DELETE. The body re-reads both rows
    # instead — two primary-key lookups on a table with a handful of rows that
    # is written a few times per pilot.
    op.execute(
        sa.text(
            f"""
            CREATE FUNCTION {FUNCTION_NAME}() RETURNS trigger AS $$
            DECLARE
                high numeric;
                medium numeric;
            BEGIN
                SELECT value::numeric INTO high
                  FROM config WHERE key = 'confidence_threshold_high';
                SELECT value::numeric INTO medium
                  FROM config WHERE key = 'confidence_threshold_medium';

                -- A missing row is not an error: the reader falls back to its
                -- default for it (ADR-008). Only two present rows can be
                -- inverted.
                IF high IS NOT NULL AND medium IS NOT NULL AND medium > high THEN
                    RAISE EXCEPTION
                        'confidence_threshold_medium (%) darf nicht über '
                        'confidence_threshold_high (%) liegen', medium, high
                        USING ERRCODE = 'check_violation';
                END IF;

                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
    )
    op.execute(
        sa.text(
            f"CREATE CONSTRAINT TRIGGER {TRIGGER_NAME} "
            "AFTER INSERT OR UPDATE OR DELETE ON config "
            "DEFERRABLE INITIALLY DEFERRED "
            f"FOR EACH ROW EXECUTE FUNCTION {FUNCTION_NAME}()"
        )
    )


def downgrade() -> None:
    op.execute(sa.text(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON config"))
    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}()"))
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
