from collections.abc import Sequence
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.config import (
    DEFAULT_CONFIDENCE_THRESHOLD_HIGH,
    DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM,
    DEFAULT_CONTEXT_TOP_N,
    DEFAULT_MIN_CITATION_COVERAGE,
    DEFAULT_MIN_RETRIEVAL_CONFIDENCE,
    DEFAULT_RETRIEVAL_TOP_K,
    DEFAULT_RRF_K,
    DEFAULT_SELF_CHECK_BAND_HIGH,
    DEFAULT_SELF_CHECK_BAND_LOW,
    DEFAULT_SIMILARITY_THRESHOLD,
    ConfigurationError,
    read_confidence_thresholds,
    read_pipeline_config,
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


# The three cases from issue #73: each one is somebody trying to tighten the
# bands. None of them may end up at the looser start values (ADR-008).


async def test_german_decimal_comma_raises_instead_of_loosening() -> None:
    db = make_db((("confidence_threshold_high", "0,90"), ("confidence_threshold_medium", "0,80")))

    with pytest.raises(ConfigurationError, match="confidence_threshold_high"):
        await read_confidence_thresholds(db)


async def test_transposed_digits_raise_instead_of_loosening() -> None:
    """high='0.09' is numeric and in range — only the band order catches it."""
    db = make_db((("confidence_threshold_high", "0.09"), ("confidence_threshold_medium", "0.90")))

    with pytest.raises(ConfigurationError, match="liegt über"):
        await read_confidence_thresholds(db)


async def test_inverted_bands_raise_instead_of_loosening() -> None:
    db = make_db((("confidence_threshold_high", "0.85"), ("confidence_threshold_medium", "0.95")))

    with pytest.raises(ConfigurationError, match="liegt über"):
        await read_confidence_thresholds(db)


async def test_non_numeric_value_raises() -> None:
    db = make_db((("confidence_threshold_high", "hoch"), ("confidence_threshold_medium", "0.5")))

    with pytest.raises(ConfigurationError, match="keine Zahl"):
        await read_confidence_thresholds(db)


@pytest.mark.parametrize("raw", ["1.5", "-0.1"])
async def test_value_outside_the_unit_interval_raises(raw: str) -> None:
    db = make_db((("confidence_threshold_high", raw),))

    with pytest.raises(ConfigurationError, match=r"\[0, 1\]"):
        await read_confidence_thresholds(db)


async def test_equal_bands_are_accepted() -> None:
    """medium == high is the invariant's boundary, not a violation."""
    db = make_db((("confidence_threshold_high", "0.6"), ("confidence_threshold_medium", "0.6")))

    thresholds = await read_confidence_thresholds(db)

    assert (thresholds.high, thresholds.medium) == (0.6, 0.6)


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


async def test_reads_every_pipeline_parameter_from_the_database() -> None:
    db = make_db(
        (
            ("similarity_threshold", "0.5"),
            ("min_retrieval_confidence", "0.6"),
            ("min_citation_coverage", "0.7"),
            ("retrieval_top_k", "30"),
            ("context_top_n", "8"),
            ("rrf_k", "40"),
        )
    )

    config = await read_pipeline_config(db)

    assert config.similarity_threshold == 0.5
    assert config.min_retrieval_confidence == 0.6
    assert config.min_citation_coverage == 0.7
    assert (config.retrieval_top_k, config.context_top_n, config.rrf_k) == (30, 8, 40)


async def test_pipeline_config_falls_back_to_the_seeded_start_values() -> None:
    """Fail-closed: an empty config table must not unguard the pipeline."""
    config = await read_pipeline_config(make_db(()))

    assert config.similarity_threshold == DEFAULT_SIMILARITY_THRESHOLD
    assert config.min_retrieval_confidence == DEFAULT_MIN_RETRIEVAL_CONFIDENCE
    assert config.min_citation_coverage == DEFAULT_MIN_CITATION_COVERAGE
    assert config.retrieval_top_k == DEFAULT_RETRIEVAL_TOP_K
    assert config.context_top_n == DEFAULT_CONTEXT_TOP_N
    assert config.rrf_k == DEFAULT_RRF_K
    assert config.self_check_band_low == DEFAULT_SELF_CHECK_BAND_LOW
    assert config.self_check_band_high == DEFAULT_SELF_CHECK_BAND_HIGH


@pytest.mark.parametrize("value", ["0", "-3", "viele", "2.5"])
async def test_a_top_k_that_is_not_a_positive_integer_raises(value: str) -> None:
    """A top_k of 0 retrieves nothing and turns every question into a refusal.

    Falling back to 20 would answer a deliberate setting with a different one —
    the same fail-open the #73 addendum closed for the confidence bands.
    """
    with pytest.raises(ConfigurationError, match="retrieval_top_k"):
        await read_pipeline_config(make_db((("retrieval_top_k", value),)))


@pytest.mark.parametrize("value", ["-1", "-0.01", "1.5", "42"])
async def test_a_threshold_outside_zero_to_one_raises(value: str) -> None:
    """A negative similarity_threshold is passed by every chunk.

    That silently disables the ADR-007 gate — the single mechanism behind the
    out-of-corpus refusal rate — so an out-of-range value is refused just like
    an unparseable one.
    """
    with pytest.raises(ConfigurationError, match=r"\[0, 1\]"):
        await read_pipeline_config(make_db((("similarity_threshold", value),)))


async def test_the_german_decimal_comma_raises_for_the_pipeline_keys_too() -> None:
    """The #73 case, now on the key that guards the gate."""
    with pytest.raises(ConfigurationError, match="keine Zahl"):
        await read_pipeline_config(make_db((("similarity_threshold", "0,90"),)))


@pytest.mark.parametrize("value", ["0", "1", "0.35"])
async def test_the_range_bounds_themselves_are_accepted(value: str) -> None:
    """`0` and `1` are legitimate settings: never gate, and only exact matches."""
    config = await read_pipeline_config(make_db((("similarity_threshold", value),)))

    assert config.similarity_threshold == float(value)


async def test_pipeline_config_is_read_fresh_on_every_call() -> None:
    db = make_db((("similarity_threshold", "0.35"),), (("similarity_threshold", "0.9"),))

    before = await read_pipeline_config(db)
    after = await read_pipeline_config(db)

    assert (before.similarity_threshold, after.similarity_threshold) == (0.35, 0.9)


# ── Self-Check-Grenzband (ADR-008 Stufe 3, T-25) ────────────────────────────


async def test_reads_the_self_check_band_from_the_database() -> None:
    db = make_db((("self_check_band_low", "0.4"), ("self_check_band_high", "0.8")))

    config = await read_pipeline_config(db)

    assert (config.self_check_band_low, config.self_check_band_high) == (0.4, 0.8)


async def test_an_inverted_self_check_band_raises() -> None:
    """An inverted band is not a milder setting but an empty one.

    No score is both at or above `high` and below `low`, so stage 3 would never
    run — and nothing would say so. Guarded by trg_config_self_check_band_order
    at write time; this is the reader's backstop for a write past the database.
    """
    db = make_db((("self_check_band_low", "0.9"), ("self_check_band_high", "0.5")))

    with pytest.raises(ConfigurationError, match="self_check_band_low"):
        await read_pipeline_config(db)


async def test_an_equal_self_check_band_is_allowed() -> None:
    """low == high is stage 3 switched off — an operator decision, not an error."""
    db = make_db((("self_check_band_low", "0.6"), ("self_check_band_high", "0.6")))

    config = await read_pipeline_config(db)

    assert config.self_check_band_low == config.self_check_band_high == 0.6


@pytest.mark.parametrize("value", ["0,5", "hoch", "1.5", "-0.1"])
async def test_an_unusable_self_check_band_value_raises(value: str) -> None:
    """Same rule as every other threshold: a broken row must not fall back."""
    with pytest.raises(ConfigurationError, match="self_check_band_low"):
        await read_pipeline_config(make_db((("self_check_band_low", value),)))


def test_the_trigger_band_starts_where_suppression_stops() -> None:
    """Review finding: a gap between the two let the weakest answers skip stage 3.

    With `medium` at 0.45 and the band starting at 0.50, a score in between was
    delivered *and* never verified — and those are the least well-founded answers
    the pipeline ships at all. Fail-open in the one range ADR-008 cares most
    about.

    Not a coupling the database enforces: the two keys are calibrated against
    different questions, and an operator may deliberately narrow the band to save
    calls. Their *start values* still have to agree, which is what this pins.
    """
    assert DEFAULT_SELF_CHECK_BAND_LOW == DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM
    assert DEFAULT_SELF_CHECK_BAND_HIGH == DEFAULT_CONFIDENCE_THRESHOLD_HIGH
