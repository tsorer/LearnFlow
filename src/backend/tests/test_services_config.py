from collections.abc import Sequence
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.config import (
    DEFAULT_CONFIDENCE_THRESHOLD_HIGH,
    DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM,
    read_confidence_thresholds,
)

Rows = Sequence[tuple[str, str]]


def make_result(rows: Rows) -> MagicMock:
    result = MagicMock()
    result.all.return_value = list(rows)
    return result


def make_db(*results: Rows) -> AsyncMock:
    """A session whose execute() yields one config snapshot per call."""
    db = AsyncMock()
    db.execute.side_effect = [make_result(rows) for rows in results]
    return db


async def test_reads_both_thresholds_from_the_database() -> None:
    db = make_db((("confidence_threshold_high", "0.8"), ("confidence_threshold_medium", "0.5")))

    thresholds = await read_confidence_thresholds(db)

    assert (thresholds.high, thresholds.medium) == (0.8, 0.5)


async def test_falls_back_to_defaults_when_the_rows_are_missing() -> None:
    db = make_db(())

    thresholds = await read_confidence_thresholds(db)

    assert thresholds.high == DEFAULT_CONFIDENCE_THRESHOLD_HIGH
    assert thresholds.medium == DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM


async def test_missing_single_key_keeps_the_other_database_value() -> None:
    db = make_db((("confidence_threshold_medium", "0.6"),))

    thresholds = await read_confidence_thresholds(db)

    assert thresholds.high == DEFAULT_CONFIDENCE_THRESHOLD_HIGH
    assert thresholds.medium == 0.6


async def test_non_numeric_value_falls_back_instead_of_raising(
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = make_db((("confidence_threshold_high", "hoch"), ("confidence_threshold_medium", "0.5")))

    thresholds = await read_confidence_thresholds(db)

    assert thresholds.high == DEFAULT_CONFIDENCE_THRESHOLD_HIGH
    assert thresholds.medium == 0.5
    assert "confidence_threshold_high" in caplog.text


async def test_inverted_bands_fall_back_to_both_defaults(
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = make_db((("confidence_threshold_high", "0.3"), ("confidence_threshold_medium", "0.9")))

    thresholds = await read_confidence_thresholds(db)

    assert thresholds.high == DEFAULT_CONFIDENCE_THRESHOLD_HIGH
    assert thresholds.medium == DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM
    assert caplog.records


async def test_change_takes_effect_on_the_next_call_without_restart() -> None:
    """AK: the value is never cached — a config change is picked up immediately."""
    db = make_db(
        (("confidence_threshold_high", "0.75"), ("confidence_threshold_medium", "0.45")),
        (("confidence_threshold_high", "0.9"), ("confidence_threshold_medium", "0.6")),
    )

    before = await read_confidence_thresholds(db)
    after = await read_confidence_thresholds(db)

    assert (before.high, before.medium) == (0.75, 0.45)
    assert (after.high, after.medium) == (0.9, 0.6)
    assert db.execute.await_count == 2
