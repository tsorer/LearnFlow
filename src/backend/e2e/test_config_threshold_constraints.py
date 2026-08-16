"""Issue #73: the confidence thresholds are guarded by the database itself.

Migration 0009 puts the strictness below both write paths — the admin API
(T-37) and the direct `psql` path of `Ops/07_Pilotstart-Checkliste.md`. That
guarantee lives in a `CHECK` constraint and a deferred `CONSTRAINT TRIGGER`,
so no amount of mocking in `tests/test_services_config.py` can show whether it
holds; only writing into the real table can. Same reasoning as
`test_documents_cascade.py`, which checks an FK cascade this way.

Every case runs in a transaction that is rolled back afterwards, so the row
values survive the run unchanged. The band order is deferred to commit time,
which is exactly what makes it checkable without committing: `SET CONSTRAINTS
ALL IMMEDIATE` forces the check inside the transaction.

Precondition: a running stack (`make up`) — no seeded users needed, this file
never talks to the API.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
import pytest

from app.config import settings

HIGH = "confidence_threshold_high"
MEDIUM = "confidence_threshold_medium"

# Raised by the CHECK constraint and, via `USING ERRCODE = 'check_violation'`,
# by the band-order trigger too — the cases below tell them apart by message.
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


async def set_threshold(conn: asyncpg.Connection, key: str, value: str) -> None:
    await conn.execute("UPDATE config SET value = $1 WHERE key = $2", value, key)


async def check_now(conn: asyncpg.Connection) -> None:
    """Pull the deferred band-order check forward to here.

    Sticky: the constraint stays IMMEDIATE for the rest of the transaction, so
    every later write in the same case is checked per statement. Call it once,
    at the end of a case.
    """
    await conn.execute("SET CONSTRAINTS ALL IMMEDIATE")


async def test_german_decimal_comma_is_rejected(db_conn: asyncpg.Connection) -> None:
    """The realistic typo: the docs are German and the checklist prescribes psql."""
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_threshold(db_conn, HIGH, "0,90")


async def test_non_numeric_value_is_rejected(db_conn: asyncpg.Connection) -> None:
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_threshold(db_conn, HIGH, "hoch")


@pytest.mark.parametrize("value", ["1.5", "-0.1"])
async def test_value_outside_the_unit_interval_is_rejected(
    db_conn: asyncpg.Connection, value: str
) -> None:
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_threshold(db_conn, HIGH, value)


async def test_transposed_digits_are_rejected_by_the_band_order(
    db_conn: asyncpg.Connection,
) -> None:
    """high='0.09' is numeric and within [0, 1] — the per-row CHECK cannot see it.

    Only the cross-row invariant catches it, which is why a CHECK alone does
    not close this issue.
    """
    async with rolled_back(db_conn):
        await set_threshold(db_conn, HIGH, "0.09")
        await set_threshold(db_conn, MEDIUM, "0.90")

        with pytest.raises(asyncpg.CheckViolationError, match=BAND_ORDER_MESSAGE):
            await check_now(db_conn)


async def test_inverted_bands_are_rejected(db_conn: asyncpg.Connection) -> None:
    async with rolled_back(db_conn):
        await set_threshold(db_conn, HIGH, "0.85")
        await set_threshold(db_conn, MEDIUM, "0.95")

        with pytest.raises(asyncpg.CheckViolationError, match=BAND_ORDER_MESSAGE):
            await check_now(db_conn)


async def test_equal_bands_are_accepted(db_conn: asyncpg.Connection) -> None:
    """medium == high is the boundary of the invariant, not a violation."""
    async with rolled_back(db_conn):
        await set_threshold(db_conn, HIGH, "0.60")
        await set_threshold(db_conn, MEDIUM, "0.60")

        await check_now(db_conn)


async def test_lowering_both_bands_in_one_transaction_is_accepted(
    db_conn: asyncpg.Connection,
) -> None:
    """Why the constraint is DEFERRABLE: statement order must not matter.

    Setting `high` to 0.40 while `medium` still sits at 0.45 passes through an
    inverted state that only exists inside the transaction.
    """
    async with rolled_back(db_conn):
        # Start from the seeded values rather than from whatever the pilot
        # database currently holds, so the intermediate state below is inverted
        # regardless of when this runs.
        await set_threshold(db_conn, HIGH, "0.75")
        await set_threshold(db_conn, MEDIUM, "0.45")

        await set_threshold(db_conn, HIGH, "0.40")
        await set_threshold(db_conn, MEDIUM, "0.30")

        await check_now(db_conn)


async def test_lowering_the_upper_band_alone_is_rejected(db_conn: asyncpg.Connection) -> None:
    """The reason `Ops/07_Pilotstart-Checkliste.md` wraps the two UPDATEs in
    BEGIN/COMMIT: outside a transaction every statement commits on its own, and
    the intermediate inverted state becomes real.
    """
    before = await db_conn.fetchval("SELECT value FROM config WHERE key = $1", HIGH)
    try:
        with pytest.raises(asyncpg.CheckViolationError, match=BAND_ORDER_MESSAGE):
            # Deliberately no `rolled_back` here — autocommit is the point.
            await set_threshold(db_conn, HIGH, "0.40")
    finally:
        await set_threshold(db_conn, HIGH, before)

    assert await db_conn.fetchval("SELECT value FROM config WHERE key = $1", HIGH) == before


async def test_a_missing_row_is_not_a_violation(db_conn: asyncpg.Connection) -> None:
    """AK: a missing key keeps falling back to the reader's default (ADR-008)."""
    async with rolled_back(db_conn):
        await db_conn.execute("DELETE FROM config WHERE key = $1", HIGH)

        await check_now(db_conn)


async def test_unrelated_keys_keep_taking_any_value(db_conn: asyncpg.Connection) -> None:
    """The table stays generic key/value — the rules hang off the key.

    `stale_days` is a plain integer and `chunk_size` a token count; neither is a
    confidence threshold, and the CHECK must not start policing them.
    """
    async with rolled_back(db_conn):
        await db_conn.execute("UPDATE config SET value = $1 WHERE key = 'stale_days'", "90 Tage")

        await check_now(db_conn)
