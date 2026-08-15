"""Stages 0 and 1 of the confidence pipeline (ADR-008, T-17).

These are the two gates that decide whether a question ever reaches an LLM, so
they are tested against exact numbers rather than ranges.
"""

from app.services.confidence import (
    WEIGHT_EVIDENCE_DENSITY,
    WEIGHT_MEAN_SCORE,
    WEIGHT_TOP_SCORE,
    compute_retrieval_confidence,
    passes_retrieval_gate,
)

THRESHOLD = 0.35
TOP_N = 5


def test_gate_passes_when_one_chunk_reaches_the_threshold() -> None:
    assert passes_retrieval_gate([0.1, 0.2, 0.4], THRESHOLD) is True


def test_gate_passes_exactly_on_the_threshold() -> None:
    """ADR-008 tripwire: the comparison is >=, never >."""
    assert passes_retrieval_gate([THRESHOLD], THRESHOLD) is True


def test_gate_fails_when_every_chunk_is_below_the_threshold() -> None:
    assert passes_retrieval_gate([0.34, 0.2, 0.01], THRESHOLD) is False


def test_gate_fails_without_any_chunk() -> None:
    assert passes_retrieval_gate([], THRESHOLD) is False


def test_confidence_of_no_chunks_is_zero() -> None:
    detail = compute_retrieval_confidence([], THRESHOLD, TOP_N)

    assert (detail.top_score, detail.mean_score, detail.result, detail.count) == (0.0, 0.0, 0.0, 0)


def test_confidence_combines_the_three_signals() -> None:
    scores = [0.8, 0.6, 0.4]  # all three above the threshold, 3 of 5 planned

    detail = compute_retrieval_confidence(scores, THRESHOLD, TOP_N)

    assert detail.top_score == 0.8
    assert detail.mean_score == 0.6
    assert detail.evidence_density == 0.6
    expected = WEIGHT_TOP_SCORE * 0.8 + WEIGHT_MEAN_SCORE * 0.6 + WEIGHT_EVIDENCE_DENSITY * 0.6
    assert detail.result == round(expected, 4)
    assert detail.count == 3


def test_top_score_is_the_best_chunk_not_the_first() -> None:
    """The context is ordered by RRF rank, so the first chunk need not be closest."""
    detail = compute_retrieval_confidence([0.5, 0.9], THRESHOLD, TOP_N)

    assert detail.top_score == 0.9


def test_chunks_below_the_threshold_do_not_count_as_evidence() -> None:
    detail = compute_retrieval_confidence([0.9, 0.1, 0.1, 0.1, 0.1], THRESHOLD, TOP_N)

    assert detail.evidence_density == 0.2  # only one of five carries evidence
    assert detail.mean_score == 0.26  # but every chunk still drags the mean down


def test_evidence_density_is_capped_at_one() -> None:
    """A larger context must not inflate the score beyond a full evidence base."""
    detail = compute_retrieval_confidence([0.9] * 8, THRESHOLD, TOP_N)

    assert detail.evidence_density == 1.0


def test_weak_retrieval_stays_below_the_seeded_gate() -> None:
    """Regression guard: barely-above-threshold chunks must not pass stage 1."""
    detail = compute_retrieval_confidence([0.36, 0.35], THRESHOLD, TOP_N)

    assert detail.result < 0.40
