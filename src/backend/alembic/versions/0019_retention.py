"""Give the question log a lifetime, and cut its link to the person (M8T1-Lab)

Until this revision nothing in the system ever deleted anything. `answers`
holds every question ever asked, in plain text, and `query_sessions.user_id`
ties each one to a named account -- so two joins recover who asked what, for
the entire life of the installation. The `ondelete` clauses of those tables
describe an account deletion that no route can trigger, which left them
decorative.

The two numbers seeded below are **proposals, not policy**: 30 and 90 days are
what `Docs/02_Requirements.md` §3 records as Vorschlagswerte, chosen so the
mechanism has something to enforce, and explicitly meant to be adjusted once the
team settles on real periods. Adjusting them needs no deployment and no restart
-- the worker re-reads both once per pass, so a new value is in force within the
hour. That is why they live in `config` and not in `worker/main.py`, where only
their fallbacks sit.

Two keys rather than one, because the two mitigations answer different
questions and must be tunable apart:

* `session_pseudonymise_days` cuts the personal reference. The question text
  survives -- ADR-009 evaluates the pipeline against exactly these rows, and a
  question without an asker still measures retrieval just as well.
* `answer_retention_days` removes the text itself. It has to be the larger of
  the two, or pseudonymisation would never be observable: the row would already
  be gone. Nothing enforces that ordering in the database, because a shorter
  retention is not *wrong* -- it is merely stricter, and a constraint here
  would block the one direction an operator may legitimately want to move in a
  hurry.

Both are counts, so they join `COUNT_KEYS` of the CHECK established in `0009`
and carried forward by `0012`, `0014`, `0017` and `0018` -- same reasoning as
there: the admin API and the `psql` path of the pilot checklist both write this
table, and only the database sits below both.

`POSITIVE_INTEGER` means a value of 0 cannot be stored, so the purge cannot be
switched off through configuration -- only shortened or lengthened. That is
deliberate for a deletion mechanism: a privacy control that a typo in the
config table can silently disable is not a control. Removing the row entirely
falls back to the default in `worker/main.py`, which is also active, not off.

Deleting an answer takes its feedback with it (`feedback.answer_id` is
ON DELETE CASCADE), which is the intended reach: a rating is meaningless once
the answer it rates is gone, and an orphaned comment would be the one row left
carrying free text.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

CHECK_NAME = "ck_config_confidence_threshold_value"

# Unchanged from 0018 -- repeated rather than imported so this migration keeps
# describing the state it creates.
NUMERIC_UNIT_INTERVAL = r"^(0(\.[0-9]+)?|1(\.0+)?)$"
POSITIVE_INTEGER = r"^[1-9][0-9]*$"
EMBED_DIMENSIONS_RANGE = r"^([1-9][0-9]{0,2}|1[0-9]{3}|2000)$"
NON_EMPTY = r"\S"
UNIT_INTERVAL_KEYS = (
    "confidence_threshold_high",
    "confidence_threshold_medium",
    "similarity_threshold",
    "min_retrieval_confidence",
    "min_citation_coverage",
    "self_check_band_low",
    "self_check_band_high",
)
OLD_COUNT_KEYS = (
    "retrieval_top_k",
    "context_top_n",
    "rrf_k",
    "processing_timeout_seconds",
    "processing_max_attempts",
)
NEW_COUNT_KEYS = (*OLD_COUNT_KEYS, "answer_retention_days", "session_pseudonymise_days")

ROWS = [
    (
        "session_pseudonymise_days",
        "30",
        "Age at which query_sessions.user_id is cleared, unlinking questions from the account",
    ),
    (
        "answer_retention_days",
        "90",
        "Age at which answers are deleted; their feedback goes with them (ON DELETE CASCADE)",
    ),
]


def _quoted(keys: tuple[str, ...]) -> str:
    return ", ".join(f"'{key}'" for key in keys)


def _check(count_keys: tuple[str, ...]) -> str:
    return (
        f"ALTER TABLE config ADD CONSTRAINT {CHECK_NAME} CHECK ("
        "  CASE"
        f"    WHEN key IN ({_quoted(UNIT_INTERVAL_KEYS)})"
        f"    THEN value ~ '{NUMERIC_UNIT_INTERVAL}'"
        f"    WHEN key IN ({_quoted(count_keys)})"
        f"    THEN value ~ '{POSITIVE_INTEGER}'"
        "    WHEN key = 'embed_dimensions'"
        f"    THEN value ~ '{EMBED_DIMENSIONS_RANGE}'"
        "    WHEN key = 'embed_model'"
        f"    THEN value ~ '{NON_EMPTY}'"
        "    ELSE true"
        "  END"
        ")"
    )


def upgrade() -> None:
    # Same reason as 0017 and 0018: Alembic runs the upgrade in one transaction,
    # and a fresh database still has the 0014 band-order trigger's events
    # pending when this revision starts -- Postgres refuses to ALTER a table
    # that has them.
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))

    # Constraint first, rows second -- same ordering as 0017/0018 and for the
    # same reason: `config` has a foreign key to `users`, so inserting first
    # would leave pending trigger events behind and Postgres would refuse the
    # ALTER. The order also means the seed below is validated by the constraint
    # it belongs to.
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(_check(NEW_COUNT_KEYS)))

    bind = op.get_bind()
    for key, value, description in ROWS:
        bind.execute(
            sa.text(
                "INSERT INTO config (key, value, description) VALUES (:key, :value, :description)"
            ),
            {"key": key, "value": value, "description": description},
        )


def downgrade() -> None:
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(_check(OLD_COUNT_KEYS)))
    op.execute(
        sa.text(
            "DELETE FROM config WHERE key IN "
            "('answer_retention_days', 'session_pseudonymise_days')"
        )
    )
    # The DELETE leaves pending events of the 0014 trigger behind, and the
    # downgrade of 0014 drops that trigger a few revisions later -- in the same
    # transaction, on a table Postgres would then refuse to touch.
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))
