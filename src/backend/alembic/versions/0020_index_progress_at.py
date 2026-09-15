"""Give the reaper a progress clock of its own, not a claim clock (T-51, #106)

`heartbeat` on the `pgqueuer` row is not a liveness signal for us: pgqueuer
only sends its periodic heartbeat when `retry_timer` is set, and the worker's
registration (`worker/main.py`, `main()`) leaves it at the default
`timedelta(0)`, so `Heartbeat.__aenter__` never starts the sender. What
`heartbeat` actually carries is the moment pgqueuer handed the job out
(`SET status = 'picked', heartbeat = NOW()`) -- "claimed this long ago", not
"still alive". T-43's reaper had to use it as a liveness proxy anyway, which
forced `processing_timeout_seconds` (2700s, ADR-006) into two jobs a single
number cannot do together: long enough to outlast the worst legitimate run,
and short enough to repair a crash quickly. It settled on the first, at the
price of a worst-case recovery near 45 minutes -- and AK 4 of #69 ("a document
being processed right now is left alone") held only probabilistically, not by
construction.

`documents.index_progress_at` replaces the liveness proxy with an actual one:
the worker writes it at phase boundaries inside `process_document` (after
parsing, after chunking, after every embedding batch), and the reaper measures
"no progress in X" instead of "claimed more than X ago". X can now be small,
independent of how long the whole run takes.

The column is a sibling of `index_version`/`index_attempts` from `0017`, not
an extension of `updated_at`: it needs the same `onupdate`-free write path for
the same reason those two do (`0017`'s docstring covers it in full) -- a
future unrelated ORM write on the row (US-06 validation, an area rename) must
not refresh a running job's clock and mask its own death. It also has to
carry the same `index_version` guard as every other worker write to this row:
without it, a run the reaper has already declared abandoned and handed to a
fresh attempt could keep refreshing the clock the reaper reads, and the
document would never be reapable again. That failure mode is exactly why the
liveness signal could not live back on the `pgqueuer` row either (the
alternative T-51 considered and rejected) -- a queue row is addressed by
document, not by version, so a recovering "zombie" writer there has no
version to fail against and would hold the document alive indefinitely for a
reaper that can see nothing wrong.

`DEFAULT now()` for every existing row, same reasoning as `index_version`'s
`DEFAULT 1` in `0017`: a document already `processing` when this migration
runs gets a fresh clock and survives one more `processing_stall_seconds`
before the new logic can even see it -- not a backfill onto `updated_at`,
which would instead make every such row simultaneously overdue the moment
the new reaper pass runs, a requeue storm timed to land in the exact window
where workers are already restarting for the same deployment.

Two config keys where T-43 used one, not a redefinition of the existing key:
`processing_timeout_seconds` (2700s, ADR-006's "longest legitimate run")
keeps exactly the meaning it already has and keeps driving
`DELETE_ORPHANED_PICKED_ROWS` (T-52) unchanged -- that sweep still has no
progress signal of its own to read, only the queue row's stale heartbeat.
`processing_stall_seconds` (new, seeded 300) drives the reap decision
instead. Redefining the existing key in place would have left every
already-deployed installation silently running the new, much stricter
semantics under its old, much larger value -- the same deployment trap
`0017` avoided by introducing a column instead of repurposing `updated_at`.

300s is measured, not guessed, against three gaps a run can go quiet across
(PR text carries the full numbers): parsing + chunking the corpus's densest
document scaled to the 10 MiB upload limit runs to roughly 32s combined,
inserting ~1850 chunks with their vectors and publishing the row against a
real database takes on the order of 5s, and a single embedding batch may
legitimately take `TIMEOUT_SECONDS * (1 + MAX_RETRIES)` = 90s before
LiteLLM's own backoff -- call it 120s with margin, the one gap that is
computed rather than timed, since it is bounded by constants in
`app/services/embedding.py`, not by content. Doubling the largest of the
three (120s) and rounding gives 300s: under it, a run whose provider
stumbles once on a single batch would be reaped mid-retry, which is the
exact failure T-43's 2700s existed to prevent one level up.

`processing_stall_seconds` and `processing_timeout_seconds` share one new
CHECK branch this migration adds, bounded on both sides (T-61, #132): below
120s a value could reap a run mid-retry regardless of which of the two keys
carries it, and above 999999 -- the exact value #132 demonstrated the old,
lower-bound-only constraint would silently accept -- neither key can express
anything a real installation needs (2700s is ADR-006's own default; 999999s
is already ~370x that). The branch sits *before* the `COUNT_KEYS` branch
this constraint already has, same reason `0019` places
`RETENTION_DAYS_RANGE` before it: `CASE` takes the first matching arm, so
this branch keeps winning even if a later revision re-adds one of these two
keys to `COUNT_KEYS` by mistake. `COUNT_KEYS` itself is untouched --
`processing_timeout_seconds` stays listed there too, overridden by the
tighter arm above it, exactly the construction `0019` uses for the
retention keys. `processing_max_attempts` is deliberately left alone:
`0019`'s docstring already settles that the counts in that branch are meant
to stay unbounded above, and #132 does not ask for this key.

Both overflow boundaries were measured against this stack's own Postgres
(17, pgvector image), not guessed: `now() - make_interval(secs => $1)`
starts raising once $1 exceeds roughly 2.127e11 (~6739 years, Postgres's
minimum timestamp), and `now() - make_interval(secs => $1) * 2` raises at
roughly half that, ~1.063e11 (~3369 years) -- doubling the interval halves
the seconds value that reaches the same wall. 999999 sits nowhere near
either boundary; the upper bound here is about rejecting operator typos,
not about avoiding an overflow that a sane value could never reach.

`processing_timeout_seconds` predates this migration (`0017`) and was, until
this revision, writable to anything `POSITIVE_INTEGER` accepts -- unbounded
above, the exact gap #132 reports. `ALTER TABLE ... ADD CONSTRAINT` validates
every existing row against the new CHECK before it commits, so an
installation carrying a value #132 would call valid today (`999999999`, say)
would otherwise fail `alembic upgrade head` outright: a crash on `api`'s own
startup command (`alembic upgrade head && uvicorn ...`), on exactly the
column this migration exists to stop being unbounded. The `UPDATE` below
clamps any such row into `[120, 999999]` before the constraint is added --
same choice this migration already makes for `index_progress_at`'s
`DEFAULT now()` and `0017`'s `DEFAULT 1`: a safe value for existing rows
rather than a failed deployment. `processing_stall_seconds` needs no such
clamp -- it is seeded fresh by this same migration and never had a wider
range to violate.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-11
"""

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

CHECK_NAME = "ck_config_confidence_threshold_value"

# Unchanged from 0019 -- repeated rather than imported so this migration keeps
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
COUNT_KEYS = (
    "retrieval_top_k",
    "context_top_n",
    "rrf_k",
    "processing_timeout_seconds",
    "processing_max_attempts",
)
RETENTION_DAYS_RANGE = r"^([1-9][0-9]{0,3}|[1-2][0-9]{4}|3[0-5][0-9]{3}|36[0-4][0-9]{2}|36500)$"
RETENTION_DAYS_KEYS = ("answer_retention_days", "session_pseudonymise_days")

# 120-999: `1[2-9][0-9]` (120-199) or `[2-9][0-9]{2}` (200-999); 1000-999999:
# `[1-9][0-9]{3,5}` (4 to 6 digits). Exhaustively checked 0..1,000,050 against
# the intended range [120, 999999] before this went into the migration --
# written as alternatives rather than a cast-and-compare for the same reason
# `RETENTION_DAYS_RANGE`/`EMBED_DIMENSIONS_RANGE` are: `config.value` is text,
# and a casting CHECK would raise instead of reject on the very values it
# exists to catch.
PROCESSING_SECONDS_RANGE = r"^(1[2-9][0-9]|[2-9][0-9]{2}|[1-9][0-9]{3,5})$"
PROCESSING_SECONDS_KEYS = ("processing_stall_seconds", "processing_timeout_seconds")

ROW = (
    "processing_stall_seconds",
    "300",
    "Age since the last progress mark after which a claimed indexing run counts "
    "as abandoned (T-51)",
)
TIMEOUT_DESCRIPTION_NARROWED = (
    "Age after which an abandoned run's orphaned pgqueuer row is swept (T-52); "
    "reaping itself is decided by processing_stall_seconds since T-51"
)
TIMEOUT_DESCRIPTION_ORIGINAL = "Age after which a claimed indexing run counts as abandoned (T-43)"


def _quoted(keys: tuple[str, ...]) -> str:
    return ", ".join(f"'{key}'" for key in keys)


def _check(*, with_processing_seconds: bool) -> str:
    """The constraint, with or without this revision's range branch.

    Placed before the `COUNT_KEYS` branch, same reasoning as `0019`'s
    `RETENTION_DAYS_RANGE`: `CASE` takes the first matching arm, so this
    branch keeps winning even if a later revision re-adds one of these two
    keys to `COUNT_KEYS` by mistake. `COUNT_KEYS` itself stays as `0017` left
    it -- `processing_timeout_seconds` is still listed there too, simply
    overridden by the tighter arm above it.
    """
    processing = (
        f"    WHEN key IN ({_quoted(PROCESSING_SECONDS_KEYS)})"
        f"    THEN value ~ '{PROCESSING_SECONDS_RANGE}'"
        if with_processing_seconds
        else ""
    )
    return (
        f"ALTER TABLE config ADD CONSTRAINT {CHECK_NAME} CHECK ("
        "  CASE"
        f"    WHEN key IN ({_quoted(UNIT_INTERVAL_KEYS)})"
        f"    THEN value ~ '{NUMERIC_UNIT_INTERVAL}'"
        f"    WHEN key IN ({_quoted(RETENTION_DAYS_KEYS)})"
        f"    THEN value ~ '{RETENTION_DAYS_RANGE}'"
        f"{processing}"
        f"    WHEN key IN ({_quoted(COUNT_KEYS)})"
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
    # Same reason as every migration since 0014 that alters `config` in the
    # same transaction it seeds a row into: a fresh database still has the
    # 0014 band-order trigger's events pending when this revision starts, and
    # Postgres refuses to ALTER a table that has them.
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))

    # DEFAULT now() is the right answer for every existing row, same reasoning
    # as index_version's DEFAULT 1 in 0017: a document already 'processing'
    # when this migration runs gets a fresh clock rather than an instantly
    # overdue one, and survives one more processing_stall_seconds before the
    # new logic can even see it.
    op.execute(
        sa.text(
            "ALTER TABLE documents ADD COLUMN index_progress_at "
            "TIMESTAMPTZ NOT NULL DEFAULT now()"
        )
    )

    # Clamp before constrain: processing_timeout_seconds predates this
    # migration and was writable to anything POSITIVE_INTEGER accepts --
    # unbounded above, the exact gap #132 reports. ADD CONSTRAINT validates
    # every existing row synchronously, so an installation already carrying
    # a value only the old, looser shape allowed would otherwise fail this
    # upgrade outright (verified: downgrade to 0019, set the key to
    # 900000000 -- valid then -- and upgrade raises CheckViolationError).
    # numeric, not bigint, for the cast: the old shape had no digit-count
    # limit, so an absurd but technically-valid value must not itself
    # overflow the clamp that is supposed to catch it.
    op.execute(
        sa.text(
            "UPDATE config SET value = LEAST(GREATEST(value::numeric, 120), 999999)::bigint::text "
            "WHERE key = 'processing_timeout_seconds' "
            "AND value::numeric NOT BETWEEN 120 AND 999999"
        )
    )

    # Constraint first, row second -- same ordering as every prior revision
    # that both seeds `config` and alters it: `config` has a foreign key to
    # `users`, so inserting first would leave pending trigger events behind
    # and Postgres would refuse the ALTER.
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(_check(with_processing_seconds=True)))

    bind = op.get_bind()
    key, value, description = ROW
    bind.execute(
        sa.text(
            "INSERT INTO config (key, value, description) VALUES (:key, :value, :description)"
        ),
        {"key": key, "value": value, "description": description},
    )
    bind.execute(
        sa.text(
            "UPDATE config SET description = :description "
            "WHERE key = 'processing_timeout_seconds'"
        ),
        {"description": TIMEOUT_DESCRIPTION_NARROWED},
    )


def downgrade() -> None:
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(_check(with_processing_seconds=False)))
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE config SET description = :description "
            "WHERE key = 'processing_timeout_seconds'"
        ),
        {"description": TIMEOUT_DESCRIPTION_ORIGINAL},
    )
    op.execute(sa.text("DELETE FROM config WHERE key = 'processing_stall_seconds'"))
    op.execute(sa.text("ALTER TABLE documents DROP COLUMN index_progress_at"))
    # The DELETE above leaves pending events of the 0014 trigger behind, and
    # the downgrade of 0014 drops that very trigger a few revisions later --
    # in the same transaction, on a table Postgres would then refuse to touch.
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))
