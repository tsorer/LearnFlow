"""Deterministic confidence stages of the answer pipeline (ADR-008, T-17).

Covered here are stage 0 (the retrieval gate from ADR-007) and stage 1 (the
retrieval confidence). Both are pure functions over similarity scores: no
database, no LLM, no I/O. That is deliberate — these two stages are the part of
the reliability chain that must stay reproducible and cheap to test, and they
are what decides whether an LLM is called at all.

Stage 2 (citation coverage) and stage 3 (self-check) arrive with T-18; they
belong in this module too, but they need the generated answer.
"""

from collections.abc import Sequence
from dataclasses import dataclass

# Weights of the stage-1 components. ADR-008 names the three signals but not
# their weighting; these are start values to be calibrated against the eval
# dataset (ADR-009), which is why they are constants with a name rather than
# literals inside the formula. They stay in code, not in the config table: the
# config table holds thresholds the pilot recalibrates, and a weight change
# alters the meaning of every stored confidence_score.
WEIGHT_TOP_SCORE = 0.5
WEIGHT_MEAN_SCORE = 0.3
WEIGHT_EVIDENCE_DENSITY = 0.2

# Scores are stored and shown; four decimals is well beyond what a cosine
# similarity meaningfully distinguishes and keeps assertions in tests exact.
SCORE_DIGITS = 4


@dataclass(frozen=True)
class RetrievalDetail:
    """Stage-1 result with its components, mirroring `RetrievalDetail` in the spec.

    The breakdown is not decoration: an admin looking at a suppressed answer
    needs to see *which* signal was weak, otherwise the thresholds cannot be
    calibrated from real questions.
    """

    top_score: float
    mean_score: float
    evidence_density: float
    result: float
    count: int


def passes_retrieval_gate(scores: Sequence[float], similarity_threshold: float) -> bool:
    """Stage 0: at least one chunk must reach the similarity threshold (ADR-007).

    `>=`, not `>` — the seeded threshold is the lowest value that still counts
    as evidence, and tightening it here would silently diverge from the value an
    operator reads in the config table.
    """
    return any(score >= similarity_threshold for score in scores)


def compute_retrieval_confidence(
    scores: Sequence[float],
    similarity_threshold: float,
    context_top_n: int,
) -> RetrievalDetail:
    """Stage 1: deterministic confidence from the similarity of the context chunks.

    `scores` are the similarities of the chunks that would go to the LLM, in
    context order. ADR-008 names three signals: the best chunk, the average of
    the top-n, and how many chunks actually carry evidence.
    """
    if not scores:
        return RetrievalDetail(
            top_score=0.0, mean_score=0.0, evidence_density=0.0, result=0.0, count=0
        )

    # max(), not scores[0]: the context is ordered by the RRF rank, which mixes
    # in the sparse ranking, so the first chunk is not necessarily the closest
    # one. "Maximale Similarity des Top-Chunks" (ADR-008) means the best chunk.
    top_score = max(scores)
    mean_score = sum(scores) / len(scores)

    # Evidence density measured against the *configured* context size, not
    # against the chunks that happened to be found: three good chunks out of a
    # planned five is a weaker footing than five out of five, and the score
    # should say so. Capped at 1.0 so raising retrieval_top_k cannot inflate it.
    above_threshold = sum(1 for score in scores if score >= similarity_threshold)
    evidence_density = min(above_threshold / context_top_n, 1.0) if context_top_n else 0.0

    result = (
        WEIGHT_TOP_SCORE * top_score
        + WEIGHT_MEAN_SCORE * mean_score
        + WEIGHT_EVIDENCE_DENSITY * evidence_density
    )

    return RetrievalDetail(
        top_score=round(top_score, SCORE_DIGITS),
        mean_score=round(mean_score, SCORE_DIGITS),
        evidence_density=round(evidence_density, SCORE_DIGITS),
        result=round(result, SCORE_DIGITS),
        count=len(scores),
    )
