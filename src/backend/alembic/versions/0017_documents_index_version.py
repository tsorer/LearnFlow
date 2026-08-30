"""Give the worker a version token of its own, and the reaper its budget (T-43)

Since T-15 the worker uses `documents.updated_at` as an optimistic-lock token:
it reads the value with the content and refuses to publish a run whose row no
longer carries the same value. That works only as long as the upload path is
the sole writer of the column -- and `updated_at` carries `onupdate=func.now()`,
so *any* ORM write to the row moves it. The reaper of this ticket is the first
writer that has to touch a row while a job may still be indexing it: setting a
status through the ORM would move the token, and the live job would discard its
own work silently (log level info, no error, document left without chunks).
That is precisely the case acceptance criterion 4 rules out.

`index_version` separates the two meanings the one column carried. `updated_at`
goes back to being what the API shows ("last changed", the pair with
`created_at` telling a replacement apart from a first upload). `index_version`
is the token, and it is incremented by exactly two writers, both of which mean
the same thing by it -- "any indexing run older than this one is void":

* the upload path, because the bytes changed (`documents.py`, `_replace`),
* the reaper, because it declared an abandoned run dead (`worker/main.py`).

The column deliberately has no `onupdate`. A future route that writes a
Document for an unrelated reason (US-06 validation, an area rename) then cannot
invalidate a running job by accident, which is the property the old comment on
`updated_at` could only ask for.

`index_attempts` is the reaper's budget. Re-queueing is safe (re-processing is
idempotent -- `DELETE FROM chunks` precedes the insert), but it must not be
unbounded: a document that reliably kills the worker, say by exhausting its
memory, would otherwise be re-queued forever and take every other document's
processing down with it on each attempt. A successful run resets the counter,
and so does an upload -- the budget is there to bound one incident, not to
follow a document around for the rest of its life.

Both config keys are counts, so they join `COUNT_KEYS` of the CHECK constraint
established in `0009` and extended in `0012` -- same reasoning as there: there
are two write paths (the admin API of T-37 and the `psql` path of the pilot
checklist) and only the database sits below both. A new migration rather than
an edit to `0012`, because that revision has already run everywhere.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-30
"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

CHECK_NAME = "ck_config_confidence_threshold_value"

# Unchanged from 0009/0012 -- repeated rather than imported so this migration
# keeps describing the state it creates.
NUMERIC_UNIT_INTERVAL = r"^(0(\.[0-9]+)?|1(\.0+)?)$"
POSITIVE_INTEGER = r"^[1-9][0-9]*$"

UNIT_INTERVAL_KEYS = (
    "confidence_threshold_high",
    "confidence_threshold_medium",
    "similarity_threshold",
    "min_retrieval_confidence",
    "min_citation_coverage",
)

OLD_COUNT_KEYS = ("retrieval_top_k", "context_top_n", "rrf_k")
NEW_COUNT_KEYS = (*OLD_COUNT_KEYS, "processing_timeout_seconds", "processing_max_attempts")

ROWS = [
    (
        "processing_timeout_seconds",
        "900",
        "Age after which a claimed indexing run counts as abandoned (T-43)",
    ),
    (
        "processing_max_attempts",
        "3",
        "Re-queues the reaper grants a document before marking it failed (T-43)",
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
        "    ELSE true"
        "  END"
        ")"
    )


def upgrade() -> None:
    # `0014` put a DEFERRABLE INITIALLY DEFERRED constraint trigger on `config`
    # and seeded rows through it. Alembic runs the whole upgrade in one
    # transaction, so on a fresh database those trigger events are still pending
    # when this revision starts -- and Postgres refuses to ALTER a table that has
    # them ("cannot ALTER TABLE config because it has pending trigger events").
    # Firing them here is what makes the constraint swap below possible; the
    # trigger only validates the band of 0014 and has nothing to object to.
    # Any later revision that seeds `config` and then alters it needs the same
    # line.
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))

    # DEFAULT 1 is the right answer for every existing row: whatever ran before
    # this migration compared timestamps, and no run survives a deployment.
    op.execute(sa.text("ALTER TABLE documents ADD COLUMN index_version INTEGER NOT NULL DEFAULT 1"))
    op.execute(
        sa.text("ALTER TABLE documents ADD COLUMN index_attempts INTEGER NOT NULL DEFAULT 0")
    )

    # Constraint first, rows second, and not the other way round: `config` has a
    # foreign key to `users`, so an INSERT leaves pending trigger events behind
    # and Postgres refuses to ALTER the table in the same transaction
    # ("cannot ALTER TABLE ... because it has pending trigger events"). The order
    # also means the seed below is validated by the constraint it belongs to.
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
        sa.text("DELETE FROM config WHERE key IN ('processing_timeout_seconds', "
                "'processing_max_attempts')")
    )
    op.execute(sa.text("ALTER TABLE documents DROP COLUMN index_attempts"))
    op.execute(sa.text("ALTER TABLE documents DROP COLUMN index_version"))
    # The DELETE above leaves pending events of the 0014 trigger behind, and the
    # downgrade of 0014 drops that very trigger a few revisions later -- in the
    # same transaction, on a table Postgres would then refuse to touch.
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))
