"""Hybrid retrieval: tsquery building, RRF fusion, and the two-search flow (ADR-007)."""

import uuid
from collections.abc import Sequence
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.tables import DocumentStatus
from app.services.config import PipelineConfig
from app.services.retrieval import (
    RANK_ABSENT,
    fuse,
    retrieve,
    to_tsquery_terms,
)

RRF_K = 60

CONFIG = PipelineConfig(
    similarity_threshold=0.35,
    min_retrieval_confidence=0.40,
    min_citation_coverage=0.50,
    # Stage 3 is out of scope here; the band is carried only because
    # PipelineConfig reads the whole config table in one go.
    self_check_band_low=0.50,
    self_check_band_high=0.75,
    retrieval_top_k=20,
    context_top_n=2,
    rrf_k=RRF_K,
)


def make_row(score: float, chunk_id: uuid.UUID | None = None) -> dict[str, Any]:
    return {
        "chunk_id": chunk_id or uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "content": "Inhalt",
        "page": 1,
        "heading": None,
        "filename": "doc.pdf",
        "score": score,
    }


def make_db(*result_sets: Sequence[dict[str, Any]]) -> AsyncMock:
    """A session whose execute() yields one query result per call."""
    db = AsyncMock()
    results = []
    for rows in result_sets:
        result = MagicMock()
        result.mappings.return_value = list(rows)
        results.append(result)
    db.execute.side_effect = results
    return db


# --- tsquery ---------------------------------------------------------------


def test_terms_are_or_joined() -> None:
    """AND would require every word of the question in one chunk — practically never."""
    assert to_tsquery_terms("Was regelt der EU AI Act") == "regelt | EU | AI | Act"


def test_punctuation_and_single_characters_are_dropped() -> None:
    assert to_tsquery_terms("Was ist a KI-System?") == "KI | System"


def test_query_is_capped_at_ten_terms() -> None:
    question = " ".join(f"wort{n}" for n in range(20))

    assert to_tsquery_terms(question).count("|") == 9


def test_the_cap_counts_content_words_not_stop_words() -> None:
    """The regression the cap had: German questions front-load function words.

    Ten raw tokens of this question end at "erweiterten" and drop
    "Sozialhilfe" — the one term that discriminates. Stop words are removed
    before the slice, so the cap now spends its budget on content.
    """
    question = (
        "Was ist der Unterschied zwischen dem Grundbedarf und dem "
        "erweiterten Bedarf bei der Sozialhilfe"
    )

    assert to_tsquery_terms(question) == (
        "Unterschied | zwischen | Grundbedarf | erweiterten | Bedarf | Sozialhilfe"
    )


def test_a_question_of_only_stop_words_yields_an_empty_query() -> None:
    """Empty means the sparse half is skipped — not a syntax error in to_tsquery."""
    assert to_tsquery_terms("Was ist das und wie ist es") == ""


def test_question_without_usable_terms_yields_an_empty_query() -> None:
    assert to_tsquery_terms("? ! a b") == ""


# --- fusion ----------------------------------------------------------------


def test_chunk_found_by_both_searches_outranks_a_chunk_found_by_one() -> None:
    both = uuid.uuid4()
    dense_only = uuid.uuid4()
    # dense_only sits first in the dense ranking, so only the sparse hit can
    # lift `both` above it — which is exactly what fusion is for.
    dense_rows = [make_row(0.5, dense_only), make_row(0.4, both)]
    sparse_rows = [make_row(0.4, both)]

    hits = fuse(dense_rows, sparse_rows, RRF_K)

    assert [hit.chunk_id for hit in hits] == [both, dense_only]
    assert hits[0].rrf_score == pytest.approx(1 / 62 + 1 / 61)


def test_ranks_record_which_search_found_a_chunk() -> None:
    dense_id, sparse_id = uuid.uuid4(), uuid.uuid4()
    fused = fuse([make_row(0.5, dense_id)], [make_row(0.2, sparse_id)], RRF_K)

    hits = {hit.chunk_id: hit for hit in fused}

    assert (hits[dense_id].dense_rank, hits[dense_id].sparse_rank) == (1, RANK_ABSENT)
    assert (hits[sparse_id].dense_rank, hits[sparse_id].sparse_rank) == (RANK_ABSENT, 1)


def test_equal_rrf_scores_are_broken_by_similarity() -> None:
    """Two chunks at rank 1 of different searches score identically under RRF.

    Without the similarity tie-break their order would follow dict iteration,
    so the same question could produce a different context on a second run.
    """
    dense_only, sparse_only = make_row(0.9), make_row(0.3)

    hits = fuse([dense_only], [sparse_only], RRF_K)

    assert hits[0].rrf_score == pytest.approx(hits[1].rrf_score)
    assert [hit.score for hit in hits] == [0.9, 0.3]


def test_a_chunk_appears_once_even_when_both_searches_return_it() -> None:
    shared = uuid.uuid4()

    hits = fuse([make_row(0.5, shared)], [make_row(0.5, shared)], RRF_K)

    assert len(hits) == 1


# --- retrieve --------------------------------------------------------------


async def test_retrieve_runs_both_searches_and_cuts_the_context_to_top_n(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.retrieval.embed_texts", AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    )
    db = make_db([make_row(0.9), make_row(0.8), make_row(0.7)], [make_row(0.6)])

    outcome = await retrieve(db, "Was regelt der EU AI Act", CONFIG, "default")

    assert db.execute.await_count == 2
    assert (outcome.dense_count, outcome.sparse_count) == (3, 1)
    assert len(outcome.candidates) == 4
    assert len(outcome.context) == CONFIG.context_top_n


async def test_retrieve_skips_the_sparse_query_without_searchable_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """to_tsquery on an empty string is a pointless round-trip, not an error."""
    monkeypatch.setattr(
        "app.services.retrieval.embed_texts", AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    )
    db = make_db([make_row(0.9)])

    outcome = await retrieve(db, "? ! a", CONFIG, "default")

    assert db.execute.await_count == 1
    assert outcome.sparse_count == 0


async def test_retrieve_binds_the_embedding_as_a_json_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-005: asyncpg cannot encode a `vector` parameter, so it is bound as text."""
    monkeypatch.setattr(
        "app.services.retrieval.embed_texts", AsyncMock(return_value=[[0.1, 0.2]])
    )
    db = make_db([], [])

    await retrieve(db, "EU AI Act", CONFIG, "default")

    params = db.execute.await_args_list[0].args[1]
    assert params["embedding"] == "[0.1, 0.2]"
    assert params["area"] == "default"
    assert params["top_k"] == CONFIG.retrieval_top_k
    # The visibility filter binds the status instead of spelling it into the
    # SQL — only fully indexed documents are searchable (ADR-007/ADR-008).
    assert params["status"] == DocumentStatus.available
