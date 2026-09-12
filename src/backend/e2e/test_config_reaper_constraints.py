"""T-61 (#132): the two reaper "seconds" keys are guarded on *both* ends.

`processing_timeout_seconds` (T-43) sat under `POSITIVE_INTEGER` alone --
a lower bound only. #132's own issue text records
`UPDATE config SET value='999999' WHERE key='processing_timeout_seconds'`
as **accepted** against the unfixed constraint (2026-09-09) -- 999999s is
~11.5 days, chosen here as the new ceiling itself (T-61 decides the range,
not this file), precisely because it is already generous. What #132 rules
out is everything *past* it, unbounded before this migration:

* Large but finite (say, `999999999`), the reap condition on either key
  simply never matches again -- the reaper stops abandoning anything,
  silently, and before T-51 the same was true of the timeout key deciding
  reaping itself.
* Large enough, `now() - make_interval(secs => $1)` (and, doubled, the
  sweep's own `* 2` variant) raises `DatetimeFieldOverflowError` once it
  runs past Postgres's representable timestamp range. Every reaper pass then
  throws into `reaper_loop`'s `except Exception`, which logs and swallows --
  also silent, and this file measures exactly where that starts.

`processing_stall_seconds` (T-51) is new in the same migration (0020) and
gets the identical range from the day it is born, for the same reason: a
value here below the shortest a legitimate embedding-batch retry can take
would reap a run that is merely slow but healthy, and a value silently
accepted far above any plausible calibration reproduces the exact failure
#132 describes, just under the newer key.

Neither failure is reachable through `tests/test_worker.py`: those tests
drive an `AsyncMock`, so Postgres never parses the SQL and never evaluates
the CHECK. Only writing into the real table can show whether the constraint
holds -- same reasoning as `test_config_retention_constraints.py`, whose
shape this file follows.

Every case runs in a transaction that is rolled back afterwards, so the
`config` rows survive the run unchanged.

Precondition: a running stack (`make up`) -- no seeded users needed, this
file never talks to the API.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
import pytest

from app.config import settings

STALL = "processing_stall_seconds"
TIMEOUT = "processing_timeout_seconds"

# The bounds 0020's CHECK enforces for both keys (T-61). 120s is the floor a
# single embedding batch's retry can legitimately take (TIMEOUT_SECONDS *
# (1 + MAX_RETRIES) plus margin, `app/services/embedding.py`); 999999s is the
# exact value #132 demonstrated the old, lower-bound-only constraint would
# silently accept, now the ceiling instead.
MIN_SECONDS = "120"
MAX_SECONDS = "999999"


@pytest.fixture
async def db_conn() -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(settings.asyncpg_dsn)
    try:
        yield conn
    finally:
        await conn.close()


@asynccontextmanager
async def rolled_back(conn: asyncpg.Connection) -> AsyncIterator[None]:
    """Run a case against the real table without keeping any of it."""
    transaction = conn.transaction()
    await transaction.start()
    try:
        yield
    finally:
        await transaction.rollback()


async def set_seconds(conn: asyncpg.Connection, key: str, value: str) -> None:
    await conn.execute("UPDATE config SET value = $1 WHERE key = $2", value, key)


@pytest.mark.parametrize("key", [STALL, TIMEOUT])
@pytest.mark.parametrize(
    "value", [MIN_SECONDS, "121", "300", "2700", "60000", "999998", MAX_SECONDS]
)
async def test_a_plausible_value_is_accepted(
    db_conn: asyncpg.Connection, key: str, value: str
) -> None:
    """Both bounds are inclusive, and everything an operator would plausibly
    calibrate has to pass -- a constraint that rejects 2700 (the timeout's
    own default) would be worse than none."""
    async with rolled_back(db_conn):
        await set_seconds(db_conn, key, value)


@pytest.mark.parametrize("key", [STALL, TIMEOUT])
@pytest.mark.parametrize(
    "value",
    [
        "999999999",  # valid before the fix: reaps nothing, ever, silently
        "999999999999999",  # valid before the fix: overflows make_interval on every pass
        "119",  # one below the floor
        "1000000",  # one past the ceiling
        "0",
        "-1",
        "300.5",  # a period is whole seconds; make_interval would take a float
        "300,5",  # the German decimal comma -- the docs are German and prescribe psql
        "neunhundert",
        "",
    ],
)
async def test_an_implausible_value_is_rejected(
    db_conn: asyncpg.Connection, key: str, value: str
) -> None:
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_seconds(db_conn, key, value)


async def test_the_document_side_overflow_boundary(db_conn: asyncpg.Connection) -> None:
    """`STUCK_DOCUMENTS` compares `documents.index_progress_at` against
    `now() - make_interval(secs => $1)` inside a `WHERE` clause (T-51) --
    the shape measured here, not a bare `SELECT` of the timestamp: that would
    ask asyncpg to decode a result Python's own `datetime` cannot represent
    this far back (`OverflowError`, a client-side artifact of no relevance to
    the server-only comparison the reaper actually runs), and would measure
    the wrong wall entirely. Measured against this database: the `WHERE`
    clause raises once `$1` exceeds roughly 2.127e11 -- Postgres's minimum
    representable timestamp, about 6739 years before `now()`. 999999 (the
    CHECK's own ceiling) sits four orders of magnitude below it.
    """
    accepted = await db_conn.fetchval(
        "SELECT count(*) FROM documents "
        "WHERE index_progress_at < now() - make_interval(secs => $1::float8)",
        2.0e11,
    )
    assert accepted is not None

    with pytest.raises(asyncpg.PostgresError):
        await db_conn.fetchval(
            "SELECT count(*) FROM documents "
            "WHERE index_progress_at < now() - make_interval(secs => $1::float8)",
            3.0e11,
        )


async def test_the_sweeps_doubled_interval_overflows_at_half_that(
    db_conn: asyncpg.Connection,
) -> None:
    """`DELETE_ORPHANED_PICKED_ROWS` doubles the interval outside
    `make_interval` (review on #118) -- `heartbeat < now() - make_interval(secs
    => $1) * 2`, the same `WHERE`-clause shape as above and for the same
    reason. Doubling the interval halves the seconds value that reaches the
    same timestamp wall: measured at roughly 1.063e11, half of the plain
    expression's boundary above. Still four orders of magnitude above
    999999.
    """
    accepted = await db_conn.fetchval(
        "SELECT count(*) FROM pgqueuer "
        "WHERE heartbeat < now() - make_interval(secs => $1::float8) * 2",
        1.0e11,
    )
    assert accepted is not None

    with pytest.raises(asyncpg.PostgresError):
        await db_conn.fetchval(
            "SELECT count(*) FROM pgqueuer "
            "WHERE heartbeat < now() - make_interval(secs => $1::float8) * 2",
            1.5e11,
        )


async def test_the_seeded_defaults_satisfy_their_own_constraint(
    db_conn: asyncpg.Connection,
) -> None:
    """0020 seeds 300 for the stall and narrows the description of the
    existing 2700 for the timeout, against the same CHECK it adds. A
    migration whose own seed its CHECK rejects would fail on a fresh
    database, where the row does not exist yet to be noticed any other way.
    """
    rows = await db_conn.fetch(
        "SELECT key, value FROM config WHERE key IN ($1, $2)", STALL, TIMEOUT
    )
    values = {row["key"]: row["value"] for row in rows}
    assert values == {STALL: "300", TIMEOUT: "2700"}

    async with rolled_back(db_conn):
        for key, value in values.items():
            await set_seconds(db_conn, key, value)
