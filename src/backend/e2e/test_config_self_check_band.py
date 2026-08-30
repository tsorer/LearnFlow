"""T-25: the self-check trigger band is guarded by the database itself.

The same argument as `test_config_threshold_constraints.py`, applied to the two
keys migration 0014 adds. Both write paths — the admin API (T-37) and the direct
`psql` of `Ops/07_Pilotstart-Checkliste.md` — sit above the database, so that is
where the rule belongs, and only writing into the real table can show it holds.

What is worth guarding here is not a typo but an *empty* band: `low > high`
leaves no score that stage 3 could ever fire on. That is not a milder setting,
it is the stage silently switched off — the fail-open direction ADR-008 rules
out. `low == high` is the same thing done on purpose and therefore allowed.

Every case runs in a transaction that is rolled back afterwards, so the row
values survive the run unchanged.

Precondition: a running stack (`make up`) — no seeded users needed, this file
never talks to the API.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
import pytest

from app.config import settings

LOW = "self_check_band_low"
HIGH = "self_check_band_high"

# Raised by the band-order trigger via `USING ERRCODE = 'check_violation'`, the
# same as the confidence bands — the message is what tells the two apart.
BAND_ORDER_MESSAGE = "darf nicht über"


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


async def set_band(conn: asyncpg.Connection, key: str, value: str) -> None:
    await conn.execute("UPDATE config SET value = $1 WHERE key = $2", value, key)


async def check_now(conn: asyncpg.Connection) -> None:
    """Pull the deferred band-order check forward to here. Call once, at the end."""
    await conn.execute("SET CONSTRAINTS ALL IMMEDIATE")


async def test_the_band_is_seeded(db_conn: asyncpg.Connection) -> None:
    """Migration 0014 has to have run — otherwise the reader falls back silently
    and the admin parameter panel edits keys that do not exist.
    """
    rows = dict(
        await db_conn.fetch("SELECT key, value FROM config WHERE key = ANY($1)", [LOW, HIGH])
    )

    assert set(rows) == {LOW, HIGH}


async def test_german_decimal_comma_is_rejected(db_conn: asyncpg.Connection) -> None:
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_band(db_conn, LOW, "0,50")


@pytest.mark.parametrize("value", ["1.5", "-0.1", "spaeter"])
async def test_a_value_outside_the_unit_interval_is_rejected(
    db_conn: asyncpg.Connection, value: str
) -> None:
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_band(db_conn, HIGH, value)


async def test_an_inverted_band_is_rejected(db_conn: asyncpg.Connection) -> None:
    """The case a per-row CHECK cannot see: both values legal, the pair is not."""
    async with rolled_back(db_conn):
        await set_band(db_conn, LOW, "0.90")
        await set_band(db_conn, HIGH, "0.50")

        with pytest.raises(asyncpg.CheckViolationError, match=BAND_ORDER_MESSAGE):
            await check_now(db_conn)


async def test_an_equal_band_is_accepted(db_conn: asyncpg.Connection) -> None:
    """Stage 3 switched off on purpose — an operator decision, not an error."""
    async with rolled_back(db_conn):
        await set_band(db_conn, LOW, "0.60")
        await set_band(db_conn, HIGH, "0.60")

        await check_now(db_conn)


async def test_raising_both_limits_in_one_transaction_is_accepted(
    db_conn: asyncpg.Connection,
) -> None:
    """Why the constraint is DEFERRABLE: statement order must not matter.

    Raising `low` to 0.80 while `high` still sits at 0.75 passes through an
    inverted state that only exists inside the transaction.
    """
    async with rolled_back(db_conn):
        # From the seeded values rather than from whatever the pilot database
        # currently holds, so the intermediate state below is inverted whenever
        # this runs.
        await set_band(db_conn, LOW, "0.50")
        await set_band(db_conn, HIGH, "0.75")

        await set_band(db_conn, LOW, "0.80")
        await set_band(db_conn, HIGH, "0.90")

        await check_now(db_conn)


async def test_raising_the_lower_limit_alone_is_rejected(db_conn: asyncpg.Connection) -> None:
    """The reason the checklist wraps such a pair in BEGIN/COMMIT: in psql
    autocommit every statement is its own transaction, and the intermediate
    inverted state becomes real.
    """
    before = await db_conn.fetchval("SELECT value FROM config WHERE key = $1", LOW)
    try:
        with pytest.raises(asyncpg.CheckViolationError, match=BAND_ORDER_MESSAGE):
            # Deliberately no `rolled_back` here — autocommit is the point.
            await set_band(db_conn, LOW, "0.99")
    finally:
        await set_band(db_conn, LOW, before)

    assert await db_conn.fetchval("SELECT value FROM config WHERE key = $1", LOW) == before


async def test_a_missing_row_is_not_a_violation(db_conn: asyncpg.Connection) -> None:
    """A missing key keeps falling back to the reader's default (ADR-008)."""
    async with rolled_back(db_conn):
        await db_conn.execute("DELETE FROM config WHERE key = $1", HIGH)

        await check_now(db_conn)


async def test_the_confidence_bands_are_still_guarded(db_conn: asyncpg.Connection) -> None:
    """0014 drops and recreates the shared CHECK — the older keys must survive it.

    A regression here would be invisible in the reader: the constraint would
    simply stop rejecting, and the first bad value would only surface as a
    suppressed answer nobody can explain.
    """
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_band(db_conn, "confidence_threshold_high", "0,90")


async def test_the_seeded_band_leaves_no_gap_above_the_suppression_threshold(
    db_conn: asyncpg.Connection,
) -> None:
    """The seeded values, not just the reader defaults (review finding).

    Migration 0014 is what a fresh pilot database actually gets, so the
    alignment has to hold there. A band starting above
    `confidence_threshold_medium` would deliver answers between the two without
    ever running stage 3 on them.
    """
    rows = dict(
        await db_conn.fetch(
            "SELECT key, value FROM config WHERE key = ANY($1)",
            [LOW, HIGH, "confidence_threshold_medium", "confidence_threshold_high"],
        )
    )

    assert float(rows[LOW]) <= float(rows["confidence_threshold_medium"])
    assert float(rows[HIGH]) >= float(rows["confidence_threshold_high"])
