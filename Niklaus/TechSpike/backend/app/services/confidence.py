"""ADR-008: Mehrstufige Konfidenz-Pipeline (fail-closed)."""

import re
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    chunk_id: str
    content: str
    score: float
    document_id: str
    filename: str
    page: int | None
    heading: str | None


def compute_retrieval_confidence(results: list[RetrievalResult]) -> float:
    """Stage 1: deterministic retrieval confidence from similarity scores."""
    if not results:
        return 0.0
    top_score = results[0].score
    mean_score = sum(r.score for r in results) / len(results)
    evidence_density = min(len(results) / 5, 1.0)
    return round(0.5 * top_score + 0.3 * mean_score + 0.2 * evidence_density, 4)


def compute_retrieval_confidence_detail(results: list[RetrievalResult]) -> dict:
    """Returns per-component breakdown of Stage 1 confidence formula."""
    if not results:
        return {"top_score": 0.0, "mean_score": 0.0, "evidence_density": 0.0, "result": 0.0, "count": 0}
    top_score = results[0].score
    mean_score = sum(r.score for r in results) / len(results)
    evidence_density = min(len(results) / 5, 1.0)
    result = round(0.5 * top_score + 0.3 * mean_score + 0.2 * evidence_density, 4)
    return {
        "top_score": round(top_score, 4),
        "mean_score": round(mean_score, 4),
        "evidence_density": round(evidence_density, 4),
        "result": result,
        "count": len(results),
    }


def compute_citation_coverage(answer: str, chunk_ids: list[str]) -> float:
    """Stage 2: fraction of answer sentences that contain a citation marker."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
    if not sentences:
        return 0.0

    citation_pattern = re.compile(r"\[\d+\]")
    cited = sum(1 for s in sentences if citation_pattern.search(s))
    return round(cited / len(sentences), 4)


def parse_cited_indices(answer: str) -> list[int]:
    """Extract all [N] citation indices from answer text."""
    return [int(m) - 1 for m in re.findall(r"\[(\d+)\]", answer)]


def compute_composite_confidence(
    retrieval_confidence: float,
    citation_coverage: float,
    weights: tuple[float, float] = (0.6, 0.4),
) -> float:
    return round(weights[0] * retrieval_confidence + weights[1] * citation_coverage, 4)


def is_borderline(
    retrieval_confidence: float,
    citation_coverage: float,
    low: float = 0.50,
    high: float = 0.75,
) -> bool:
    """True when composite score is in the borderline zone (triggers Stage 3 self-check)."""
    score = compute_composite_confidence(retrieval_confidence, citation_coverage)
    return low <= score < high
