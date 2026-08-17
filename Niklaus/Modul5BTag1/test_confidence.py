"""Tests for the confidence tool — no dependencies at all.

Two ways to run, both without the LearnFlow environment:

    python test_confidence.py     # built-in runner at the bottom of this file
    pytest test_confidence.py     # same tests, if pytest happens to be there

Plain `assert` and `math.isclose` are used instead of `pytest.approx` so the
first form works in an interpreter with nothing installed.
"""

import math

from confidence import (
    DEFAULT_LIMITED_BELOW,
    DEFAULT_SUPPRESS_BELOW,
    ConfidenceBand,
    assess,
    band_for,
    evidence_density,
)


# --- scoring end to end ---------------------------------------------------


def test_strong_signals_are_grounded():
    result = assess(0.92, 0.85, 6)
    assert result.band is ConfidenceBand.GROUNDED
    assert result.suppressed is False
    assert result.reason is None
    assert math.isclose(result.score, 0.915)


def test_medium_signals_are_limited():
    result = assess(0.75, 0.62, 3)
    assert result.band is ConfidenceBand.LIMITED
    assert result.suppressed is False
    assert math.isclose(result.score, 0.681)
    assert "below grounded threshold" in result.reason


def test_weak_signals_are_suppressed():
    result = assess(0.42, 0.31, 2)
    assert result.band is ConfidenceBand.SUPPRESSED
    assert result.suppressed is True
    assert math.isclose(result.score, 0.383)
    assert "below suppress threshold" in result.reason


def test_score_stays_in_unit_interval():
    for signals in ((0.0, 0.0, 0), (1.0, 1.0, 99), (0.5, 0.1, 3)):
        score = assess(*signals).score
        assert 0.0 <= score <= 1.0, f"{signals} scored {score}"


# --- band lookup ----------------------------------------------------------


def test_a_score_on_the_threshold_passes_it():
    # Fail-closed means "below the threshold is out", not "at it" — ADR-008.
    assert band_for(DEFAULT_SUPPRESS_BELOW) is ConfidenceBand.LIMITED
    assert band_for(DEFAULT_LIMITED_BELOW) is ConfidenceBand.GROUNDED


def test_a_score_just_under_the_threshold_drops_a_band():
    assert band_for(0.4999) is ConfidenceBand.SUPPRESSED
    assert band_for(0.7999) is ConfidenceBand.LIMITED


def test_custom_thresholds_are_honoured():
    assert band_for(0.62, suppress_below=0.70) is ConfidenceBand.SUPPRESSED
    assert assess(0.92, 0.85, 6, limited_below=0.95).band is ConfidenceBand.LIMITED


# --- evidence density -----------------------------------------------------


def test_evidence_density_saturates():
    assert evidence_density(0) == 0.0
    assert math.isclose(evidence_density(2), 0.4)
    assert evidence_density(5) == 1.0
    assert evidence_density(500) == 1.0


def test_evidence_density_survives_a_zero_saturation():
    assert evidence_density(3, saturation=0) == 0.0


# --- fail-closed on bad input ---------------------------------------------


def test_nan_is_suppressed_not_raised():
    result = assess(float("nan"), 0.5, 3)
    assert result.suppressed is True
    assert result.score == 0.0
    assert "NaN" in result.reason


def test_similarity_outside_the_unit_interval_is_suppressed():
    assert assess(1.4, 0.5, 3).suppressed is True
    assert assess(0.9, -0.1, 3).suppressed is True


def test_negative_chunk_count_is_suppressed():
    assert assess(0.9, 0.8, -1).suppressed is True


def test_mean_above_max_is_suppressed():
    result = assess(0.4, 0.9, 3)
    assert result.suppressed is True
    assert "exceeds max_similarity" in result.reason


def test_booleans_are_not_accepted_as_numbers():
    # True would otherwise sail through as a perfect similarity of 1.0.
    assert assess(True, 0.5, 3).suppressed is True
    assert assess(0.9, 0.8, True).suppressed is True


def test_broken_weighting_is_suppressed():
    result = assess(0.92, 0.85, 6, weight_max=0.9)
    assert result.suppressed is True
    assert "weights sum to" in result.reason


# --- runner for an interpreter without pytest -----------------------------

if __name__ == "__main__":
    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
        except AssertionError as exc:
            failed.append(name)
            print(f"FAIL  {name}: {exc or '(assertion failed)'}")
        else:
            print(f"ok    {name}")

    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
