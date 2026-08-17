"""Retrieval confidence scoring and display bands (ADR-008 stage 1, US-02).

Standalone by design: no project imports, no I/O, standard library only. The
logic can therefore be exercised with a bare `python test_confidence.py` — no
database, no container, no API key, no cost. The agent-facing wrapper lives in
`third_agent.py` and contains no logic of its own.

Nothing here reads configuration. The production caller will fetch the
thresholds from the `config` table (ADR-003, calibratable without a deployment)
and pass them in as arguments; that is what keeps this module importable
anywhere.

Fail-closed (ADR-008): every path that cannot produce a trustworthy score
suppresses the answer instead of raising or guessing. A wrongly suppressed
answer is an acceptable error, a delivered hallucination is not.

Deliberately out of scope for now: the composite score of ADR-008 stage 2,
which folds in the citation coverage measured after generation. It plugs in as
a fourth weighted signal once the citation format is decided.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

# Weights of the three retrieval signals. Start values — to be calibrated
# empirically in the retrieval spike (ADR-007). They must sum to 1.0, otherwise
# the score would leave [0, 1] and the band thresholds below would be
# meaningless; assess() checks this instead of trusting the caller.
DEFAULT_WEIGHT_MAX = 0.5
DEFAULT_WEIGHT_MEAN = 0.3
DEFAULT_WEIGHT_DENSITY = 0.2

# Band thresholds from US-02: under 50 % the answer is suppressed entirely,
# under 80 % it is delivered but marked "Eingeschränkt belegt".
DEFAULT_SUPPRESS_BELOW = 0.50
DEFAULT_LIMITED_BELOW = 0.80

# Number of chunks above the retrieval threshold at which evidence density
# counts as saturated — further hits no longer raise confidence.
DEFAULT_DENSITY_SATURATION = 5


class ConfidenceBand(Enum):
    """Display band of an answer (US-02).

    The values are stable identifiers, not labels: the German user-facing texts
    belong to the frontend, so that this module stays free of presentation.
    """

    SUPPRESSED = "suppressed"
    LIMITED = "limited"
    GROUNDED = "grounded"


@dataclass(frozen=True)
class ConfidenceResult:
    """Outcome of an assessment.

    `band` is the authoritative verdict; `score` is the number behind it and is
    shown in the answer metadata (US-02). `reason` explains any outcome that is
    not GROUNDED and is technical, developer-facing text.
    """

    score: float
    band: ConfidenceBand
    suppressed: bool
    reason: str | None


def evidence_density(
    chunks_above_threshold: int,
    saturation: int = DEFAULT_DENSITY_SATURATION,
) -> float:
    """Map the number of chunks above the retrieval threshold onto [0, 1]."""
    if saturation <= 0:
        return 0.0
    return min(chunks_above_threshold / saturation, 1.0)


def band_for(
    score: float,
    suppress_below: float = DEFAULT_SUPPRESS_BELOW,
    limited_below: float = DEFAULT_LIMITED_BELOW,
) -> ConfidenceBand:
    """Look up the display band for a score.

    The comparisons are strict `<`, so a score sitting exactly on a threshold
    passes it: the thresholds are the lowest values still acceptable. Turning
    these into `<=` would weaken the fail-closed pipeline (ADR-008).
    """
    if score < suppress_below:
        return ConfidenceBand.SUPPRESSED
    if score < limited_below:
        return ConfidenceBand.LIMITED
    return ConfidenceBand.GROUNDED


def _reject(
    max_similarity: float,
    mean_top_n_similarity: float,
    chunks_above_threshold: int,
) -> str | None:
    """Return why the signals cannot be scored, or None if they are usable."""
    similarities = (
        ("max_similarity", max_similarity),
        ("mean_top_n_similarity", mean_top_n_similarity),
    )
    for name, value in similarities:
        # bool is a subclass of int and would silently score as 0.0 / 1.0.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"{name} is not a number"
        if not math.isfinite(value):
            return f"{name} is NaN or infinite"
        if not 0.0 <= value <= 1.0:
            return f"{name}={value} is outside [0, 1]"

    if isinstance(chunks_above_threshold, bool) or not isinstance(
        chunks_above_threshold, int
    ):
        return "chunks_above_threshold is not an integer"
    if chunks_above_threshold < 0:
        return f"chunks_above_threshold={chunks_above_threshold} is negative"

    # A mean over the top-n can never exceed the maximum. If it does, the
    # signals come from different retrievals or are transposed — either way we
    # do not know what we are scoring.
    if mean_top_n_similarity > max_similarity:
        return (
            f"mean_top_n_similarity={mean_top_n_similarity} exceeds "
            f"max_similarity={max_similarity}"
        )
    return None


def assess(
    max_similarity: float,
    mean_top_n_similarity: float,
    chunks_above_threshold: int,
    *,
    weight_max: float = DEFAULT_WEIGHT_MAX,
    weight_mean: float = DEFAULT_WEIGHT_MEAN,
    weight_density: float = DEFAULT_WEIGHT_DENSITY,
    suppress_below: float = DEFAULT_SUPPRESS_BELOW,
    limited_below: float = DEFAULT_LIMITED_BELOW,
    density_saturation: int = DEFAULT_DENSITY_SATURATION,
) -> ConfidenceResult:
    """Score the retrieval signals and decide whether the answer may be shown.

    Never raises on bad input: unusable signals or a broken weighting yield a
    suppressed result carrying the reason, because a caller swallowing an
    exception would be one hallucination away from the NFA (ADR-008).
    """
    rejected = _reject(max_similarity, mean_top_n_similarity, chunks_above_threshold)
    if rejected is not None:
        return ConfidenceResult(
            score=0.0,
            band=ConfidenceBand.SUPPRESSED,
            suppressed=True,
            reason=f"unusable retrieval signals: {rejected}",
        )

    weight_sum = weight_max + weight_mean + weight_density
    if not math.isclose(weight_sum, 1.0):
        return ConfidenceResult(
            score=0.0,
            band=ConfidenceBand.SUPPRESSED,
            suppressed=True,
            reason=f"weights sum to {weight_sum}, expected 1.0",
        )

    score = (
        weight_max * max_similarity
        + weight_mean * mean_top_n_similarity
        + weight_density * evidence_density(chunks_above_threshold, density_saturation)
    )
    band = band_for(score, suppress_below, limited_below)

    if band is ConfidenceBand.SUPPRESSED:
        reason = f"score {score:.3f} below suppress threshold {suppress_below:.2f}"
    elif band is ConfidenceBand.LIMITED:
        reason = f"score {score:.3f} below grounded threshold {limited_below:.2f}"
    else:
        reason = None

    return ConfidenceResult(
        score=score,
        band=band,
        suppressed=band is ConfidenceBand.SUPPRESSED,
        reason=reason,
    )
