"""Seed and constrain the self-check trigger band

Stage 3 of ADR-008 is deliberately not run for every answer: it costs a second
LLM call, and without streaming (ADR-002) that lands directly on the wait the
user sees. It runs only for answers whose composite score sits *near* the
threshold — the band between these two values.

The keys already existed in the frontend before they existed here: the admin
parameter panel offered `self_check_band_low` / `self_check_band_high` and fell
back to invented literals when the backend did not ship them. Seeding them is
what makes that panel edit something real (T-25).

Both mechanisms of `0009` apply again, for the same reasons:

* `CHECK` for the per-row part — the band limits are ratios in [0, 1], so the
  key list of `ck_config_confidence_threshold_value` is extended rather than a
  second constraint added. The `CASE` block was written to be extended.
* `CONSTRAINT TRIGGER` for `low <= high`. An inverted band is not a milder
  setting but an empty one: no score can be both above the high limit and below
  the low one, so stage 3 would silently never run — the fail-open direction
  ADR-008 rules out. Two rows, so a `CHECK` cannot see it; deferred to commit so
  both values can be moved in one transaction in any order.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-22
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

CHECK_NAME = "ck_config_confidence_threshold_value"
TRIGGER_NAME = "trg_config_self_check_band_order"
FUNCTION_NAME = "config_check_self_check_band_order"

KEY_LOW = "self_check_band_low"
KEY_HIGH = "self_check_band_high"

# Start values, and hypotheses like every other threshold in ADR-008 (offener
# Punkt 1). The lower edge is `confidence_threshold_medium` itself, not a value
# above it: the band has to start where suppression stops, otherwise answers
# between the two are delivered *and* skip stage 3 — and those are the weakest
# answers the pipeline ships at all. The upper edge is
# `confidence_threshold_high`, above which ADR-008 calls the footing clear
# enough that the second call buys nothing.
ROWS = [
    (
        KEY_LOW,
        "0.45",
        "Composite confidence at or above this triggers the self-check (ADR-008 stage 3)",
    ),
    (
        KEY_HIGH,
        "0.75",
        "Composite confidence at or above this skips the self-check (ADR-008 stage 3)",
    ),
]

# Repeated from 0009/0012 rather than imported, so this migration keeps
# describing the state it creates even if an earlier one is squashed away.
NUMERIC_UNIT_INTERVAL = r"^(0(\.[0-9]+)?|1(\.0+)?)$"
POSITIVE_INTEGER = r"^[1-9][0-9]*$"

OLD_UNIT_INTERVAL_KEYS = (
    "confidence_threshold_high",
    "confidence_threshold_medium",
    "similarity_threshold",
    "min_retrieval_confidence",
    "min_citation_coverage",
)
NEW_UNIT_INTERVAL_KEYS = (*OLD_UNIT_INTERVAL_KEYS, KEY_LOW, KEY_HIGH)

COUNT_KEYS = ("retrieval_top_k", "context_top_n", "rrf_k")


def _quoted(keys: tuple[str, ...]) -> str:
    return ", ".join(f"'{key}'" for key in keys)


def _check(unit_interval_keys: tuple[str, ...]) -> str:
    return (
        f"ALTER TABLE config ADD CONSTRAINT {CHECK_NAME} CHECK ("
        "  CASE"
        f"    WHEN key IN ({_quoted(unit_interval_keys)})"
        f"    THEN value ~ '{NUMERIC_UNIT_INTERVAL}'"
        f"    WHEN key IN ({_quoted(COUNT_KEYS)})"
        f"    THEN value ~ '{POSITIVE_INTEGER}'"
        "    ELSE true"
        "  END"
        ")"
    )


def upgrade() -> None:
    bind = op.get_bind()

    # The constraint is widened before the rows are written, so the seed itself
    # is already covered by it.
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(_check(NEW_UNIT_INTERVAL_KEYS)))

    for key, value, description in ROWS:
        # DO NOTHING, as in 0008: an existing value is a deliberate operator
        # setting and must not be reset to the start value by a migration.
        bind.execute(
            sa.text(
                "INSERT INTO config (key, value, description) "
                "VALUES (:key, :value, :description) ON CONFLICT (key) DO NOTHING"
            ),
            {"key": key, "value": value, "description": description},
        )

    # No WHEN clause, same as trg_config_confidence_band_order: the trigger fires
    # for INSERT, UPDATE and DELETE, and a WHEN referencing NEW is invalid on
    # DELETE. The body re-reads both rows instead.
    op.execute(
        sa.text(
            f"""
            CREATE FUNCTION {FUNCTION_NAME}() RETURNS trigger AS $$
            DECLARE
                low numeric;
                high numeric;
            BEGIN
                SELECT value::numeric INTO low
                  FROM config WHERE key = '{KEY_LOW}';
                SELECT value::numeric INTO high
                  FROM config WHERE key = '{KEY_HIGH}';

                -- A missing row is not an error: the reader falls back to its
                -- default for it (ADR-008). Only two present rows can be
                -- inverted. Equal limits are allowed — that is an empty band on
                -- purpose, i.e. stage 3 switched off, the same way a
                -- similarity_threshold of 0 switches off stage 0.
                IF low IS NOT NULL AND high IS NOT NULL AND low > high THEN
                    RAISE EXCEPTION
                        '{KEY_LOW} (%) darf nicht über '
                        '{KEY_HIGH} (%) liegen', low, high
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
    bind = op.get_bind()

    op.execute(sa.text(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON config"))
    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}()"))

    # The rows go before the constraint narrows again — otherwise a hand-set
    # band value would be left behind under a constraint that no longer names
    # its key, where the next ALTER on this table would trip over it.
    bind.execute(
        sa.text("DELETE FROM config WHERE key IN (:low, :high)"),
        {"low": KEY_LOW, "high": KEY_HIGH},
    )

    # The DELETE queues deferred events for the *other* band-order trigger
    # (migration 0009, still in place), and PostgreSQL refuses to ALTER a table
    # that has pending trigger events — the downgrade died here with
    # ObjectInUseError. Flushing them now is safe: they would check rows that
    # this migration never touched.
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))

    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(_check(OLD_UNIT_INTERVAL_KEYS)))
