"""T-42 / Issue #68: embed_model / embed_dimensions are guarded by the database itself.

Same argument as `test_config_threshold_constraints.py` and
`test_config_self_check_band.py`, applied to the two keys migration 0018
adds — the only write path in the running system (`apply_embedding_config.py`,
raw SQL, not the admin API: `app/routers/admin.py` keeps both keys read-only)
sits above the database, so only writing into the real table can show the
CHECK holds. No trigger involved here, unlike the two files above: a single
row's shape is either valid or it is not, there is no cross-row band order to
defer.

Every case runs in a transaction that is rolled back afterwards, so the row
values survive the run unchanged.

Precondition: `make e2e` (T-55) — no seeded users needed, this file
never talks to the API.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
import pytest

from app.config import settings

MODEL = "embed_model"
DIMENSIONS = "embed_dimensions"


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


async def set_value(conn: asyncpg.Connection, key: str, value: str) -> None:
    await conn.execute("UPDATE config SET value = $1 WHERE key = $2", value, key)


async def test_both_keys_are_seeded(db_conn: asyncpg.Connection) -> None:
    """Migration 0018 has to have run — otherwise the T-42 startup check
    (`app/services/embedding_config.py`) fails closed on a missing row before
    either API or worker ever comes up."""
    rows = dict(
        await db_conn.fetch(
            "SELECT key, value FROM config WHERE key = ANY($1)", [MODEL, DIMENSIONS]
        )
    )

    assert set(rows) == {MODEL, DIMENSIONS}


@pytest.mark.parametrize("value", ["2001", "0", "-1", "abc", ""])
async def test_an_out_of_range_or_unparsable_dimension_is_rejected(
    db_conn: asyncpg.Connection, value: str
) -> None:
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_value(db_conn, DIMENSIONS, value)


@pytest.mark.parametrize("value", ["1", "1536", "2000"])
async def test_a_dimension_within_the_hnsw_limit_is_accepted(
    db_conn: asyncpg.Connection, value: str
) -> None:
    async with rolled_back(db_conn):
        await set_value(db_conn, DIMENSIONS, value)


@pytest.mark.parametrize("value", ["", "   "])
async def test_an_empty_model_is_rejected(db_conn: asyncpg.Connection, value: str) -> None:
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_value(db_conn, MODEL, value)


async def test_a_non_empty_model_is_accepted(db_conn: asyncpg.Connection) -> None:
    async with rolled_back(db_conn):
        await set_value(db_conn, MODEL, "bge-m3")


async def test_the_confidence_thresholds_are_still_guarded(db_conn: asyncpg.Connection) -> None:
    """0018 drops and recreates the shared CHECK — the older keys must survive
    it. A regression here would be invisible in the reader: the constraint
    would simply stop rejecting, and the first bad value would only surface as
    a suppressed answer nobody can explain."""
    async with rolled_back(db_conn):
        with pytest.raises(asyncpg.CheckViolationError):
            await set_value(db_conn, "confidence_threshold_high", "1.5")
