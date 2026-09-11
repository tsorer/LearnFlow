"""Review on #126: the retention deadlines are guarded on *both* ends.

The purge in `worker/main.py` promises that configuration cannot switch it off
-- only shorten or lengthen it. Migration 0019 originally backed that with
`POSITIVE_INTEGER`, which is a lower bound only, and a lower bound alone leaves
the very possibility the promise excludes:

* `999999` days puts the cutoff in 713 BC. Perfectly valid, and nothing ever
  matches again -- the purge stops deleting, silently.
* `2147483647` days makes `make_interval` raise `timestamp out of range`. Every
  pass then throws into `retention_loop`'s `except Exception`, which logs and
  swallows -- also silently.

Neither is reachable through `tests/test_worker.py`: those tests drive an
`AsyncMock`, so Postgres never parses the SQL and never evaluates the CHECK.
Only writing into the real table can show whether the constraint holds, which is
why this file exists at all -- same reasoning as
`test_config_threshold_constraints.py`, whose shape it follows.

Every case runs in a transaction that is rolled back afterwards, so the two
`config` rows survive the run unchanged.

Precondition: a running stack (`make up`) -- no seeded users needed, this file
never talks to the API.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
import pytest

from app.config import settings

PSEUDONYMISE = "session_pseudonymise_days"
RETENTION = "answer_retention_days"

# 100 years. Past any real retention policy, and far enough below the overflow
# that "lengthen" can never mean "switch off" (migration 0019).
MAX_DAYS = "36500"


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


async def set_days(conn: asyncpg.Connection, key: str, value: str) -> None:
    await conn.execute("UPDATE config SET value = $1 WHERE key = $2", value, key)


@pytest.mark.parametrize("key", [PSEUDONYMISE, RETENTION])
@pytest.mark.parametrize("value", ["1", "7", "30", "90", "365", "9999", "10000", MAX_DAYS])
async def test_a_plausible_period_is_accepted(
    db_conn: asyncpg.Connection, key: str, value: str
) -> None:
    """Both bounds are inclusive, and everything an operator would plausibly
    set has to pass -- a constraint that rejects 365 would be worse than none."""
    async with rolled_back(db_conn):
        await set_days(db_conn, key, value)


@pytest.mark.parametrize("key", [PSEUDONYMISE, RETENTION])
@pytest.mark.parametrize(
    "value",
    [
        "999999",  # valid before the fix: cutoff in 713 BC, deletes nothing ever again
        "2147483647",  # valid before the fix: make_interval raises on every pass
        "36501",  # one past the bound
        "40000",
        "0",  # would mean "delete everything", and is not the way to say it
        "-1",
        "90.5",  # a period is whole days; make_interval would take a float
        "90,5",  # the German decimal comma -- the docs are German and prescribe psql
        "spaeter",
        "",
    ],
)
async def test_a_value_that_would_disable_the_purge_is_rejected(
    db_conn: asyncpg.Connection, key: str, value: str
) -> None:
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_days(db_conn, key, value)


async def test_the_rejected_values_really_would_have_broken_the_purge(
    db_conn: asyncpg.Connection,
) -> None:
    """The constraint is worth having only if what it rejects is actually
    harmful. Both halves of the claim, measured against this database rather
    than asserted: one cutoff predates every possible row, the other does not
    exist at all.
    """
    # Cast in SQL rather than letting asyncpg decode it: the cutoff lands
    # before year 1, which Python's `datetime` cannot represent at all
    # (`OverflowError` in the codec). That the value is undecodable is itself
    # part of the point.
    ancient = await db_conn.fetchval("SELECT (now() - make_interval(days => 999999))::text")
    assert ancient.endswith("BC"), f"expected a cutoff in antiquity, got {ancient}"

    with pytest.raises(asyncpg.PostgresError, match="out of range"):
        await db_conn.fetchval("SELECT (now() - make_interval(days => 2147483647))::text")


async def test_the_seeded_defaults_satisfy_their_own_constraint(
    db_conn: asyncpg.Connection,
) -> None:
    """0019 seeds 30 and 90 and constrains the same two keys. A migration whose
    seed its own CHECK rejects would fail on a fresh database, where the rows do
    not exist yet to be noticed any other way."""
    rows = await db_conn.fetch(
        "SELECT key, value FROM config WHERE key IN ($1, $2)", PSEUDONYMISE, RETENTION
    )
    values = {row["key"]: row["value"] for row in rows}
    assert values == {PSEUDONYMISE: "30", RETENTION: "90"}

    async with rolled_back(db_conn):
        for key, value in values.items():
            await set_days(db_conn, key, value)
