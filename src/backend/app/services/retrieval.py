"""Hybrid retrieval: dense + sparse + reciprocal rank fusion (ADR-007, T-17).

Two searches contribute to every question. Dense (pgvector cosine over the HNSW
index) finds semantic neighbours; sparse (Postgres full text with the German
configuration over the GIN index) catches the exact compound nouns and acronyms
that a German technical corpus is full of and that vector search reliably
misses. Both indexes already exist and the worker fills both columns on ingest.

The module returns candidates and a context selection — it does not decide
whether an answer may be given. That is the confidence pipeline's job
(app/services/confidence.py), which keeps the ADR-007/ADR-008 boundary visible
in the code and leaves room for a re-ranker between fusion and gate.
"""

import json
import logging
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.config import PipelineConfig
from app.services.embedding import embed_texts

logger = logging.getLogger(__name__)

# Rank 0 means "this chunk was not in that result list". Real ranks are
# 1-based, so the sentinel cannot collide with one. It exists because
# DebugInfo.dense_rank is a required non-nullable integer in the spec.
RANK_ABSENT = 0

# A tsquery of ten content terms already covers the searchable part of a
# question; beyond that the remaining words are filler that only costs index
# time. Counted *after* the stop words are removed — see STOP_WORDS.
MAX_TSQUERY_TERMS = 10

# German questions front-load function words: "Was ist der Unterschied zwischen
# dem Grundbedarf und dem erweiterten Bedarf bei der Sozialhilfe" spends nine of
# its first ten tokens on words that carry no meaning, and the cap would drop
# "Sozialhilfe" — the one term that discriminates. `to_tsvector('german', ...)`
# removes these anyway; taking them out here means the cap counts what will
# actually be searched. Deliberately short: only unambiguous function words, so
# no domain term can be swallowed by it.
STOP_WORDS = frozenset(
    """
    aber alle als am an auch auf aus bei bin bis bist da das dass dem den der des
    dessen die dies diese diesem diesen dieser dieses doch dort du ein eine
    einem einen einer eines er es euer eure fuer für hat hatte hatten hier hin
    ich ihr ihre im in ist ja kann kein keine man mein mit nach nicht noch nun
    nur ob oder ohne sein seine sich sie sind so soll sollte um und uns unser
    vom von vor war waren was wann warum weil welche welchem welchen welcher
    welches wenn wer werden wie wir wird wo zu zum zur über
    """.split()
)

# Single characters carry no term information and match far too much.
MIN_TSQUERY_TERM_LENGTH = 2

# The embedding is bound as text and cast in two steps, exactly as the worker
# does on insert (ADR-005): a direct CAST(:embedding AS vector) would make
# Postgres infer the parameter type as `vector`, which asyncpg cannot encode
# without registering the extension codec on the connection. pgvector's input
# format is a JSON float array, so json.dumps produces the literal it expects.
_EMBEDDING = "CAST(CAST(:embedding AS text) AS vector)"

# Only chunks of fully indexed documents in the caller's area are searchable.
# A document still in 'processing' has some of its chunks written and would
# otherwise answer questions from a fragment of itself.
_VISIBLE = "d.status = 'available' AND d.area = :area AND c.embedding IS NOT NULL"

_COLUMNS = (
    "c.id AS chunk_id, c.document_id, c.content, c.page, c.heading, d.filename, "
    f"1 - (c.embedding <=> {_EMBEDDING}) AS score"
)

# No similarity threshold in the WHERE clause: it would be a post-filter that
# cuts into the LIMIT, so a question whose best chunks are mediocre would
# return fewer candidates than asked for instead of returning them and being
# rejected by the gate. Ordering by the raw distance is also what lets the HNSW
# index serve the query at all.
#
# The `d.status` / `d.area` conditions remain post-filters, though, and that is
# a known pgvector property rather than a bug here: HNSW walks `ef_search`
# candidates (default 40) and the filter is applied to those, so with a corpus
# far larger than the pilot's <10k chunks this can return fewer than `top_k`
# rows. At pilot size the whole corpus is one area and effectively all of it is
# 'available', so the effect is not reachable; raising `ef_search` is the lever
# if it ever is.
DENSE_SQL = text(
    f"SELECT {_COLUMNS} "
    "FROM chunks c JOIN documents d ON d.id = c.document_id "
    f"WHERE {_VISIBLE} "
    f"ORDER BY c.embedding <=> {_EMBEDDING} "
    "LIMIT :top_k"
)

# The same cosine score is selected here, not just the text rank: a chunk found
# only by the full-text half still needs a similarity for the gate (stage 0) and
# for the retrieval confidence (stage 1). Selecting it in this query costs
# nothing and saves a second round-trip to score those chunks afterwards.
SPARSE_SQL = text(
    f"SELECT {_COLUMNS} "
    "FROM chunks c JOIN documents d ON d.id = c.document_id "
    f"WHERE {_VISIBLE} AND c.tsv @@ to_tsquery('german', :tsquery) "
    "ORDER BY ts_rank_cd(c.tsv, to_tsquery('german', :tsquery)) DESC "
    "LIMIT :top_k"
)


@dataclass(frozen=True)
class RetrievalHit:
    """One candidate chunk with everything a citation and the debug view need."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    content: str
    page: int | None
    heading: str | None
    score: float
    dense_rank: int
    sparse_rank: int
    rrf_score: float


@dataclass(frozen=True)
class RetrievalOutcome:
    """Fused candidates plus the slice that would become the LLM context."""

    candidates: list[RetrievalHit]
    context: list[RetrievalHit]
    dense_count: int
    sparse_count: int


async def retrieve(
    db: AsyncSession,
    question: str,
    config: PipelineConfig,
    area: str,
) -> RetrievalOutcome:
    """Embed the question, run both searches, fuse them, return the top-n context."""
    embedding = (await embed_texts([question]))[0]
    params: dict[str, Any] = {
        "embedding": json.dumps(embedding),
        "area": area,
        "top_k": config.retrieval_top_k,
    }

    # Sequential, not asyncio.gather: an AsyncSession holds a single asyncpg
    # connection and asyncpg forbids concurrent operations on one connection —
    # the same constraint that makes the worker take a pooled connection per
    # job. "Parallel" in ADR-007 means both searches contribute, not that they
    # run concurrently; at k=20 over <10k chunks the second query is noise next
    # to the embedding round-trip that precedes both.
    dense_rows = await _fetch(db, DENSE_SQL, params)

    tsquery = to_tsquery_terms(question)
    sparse_rows = await _fetch(db, SPARSE_SQL, {**params, "tsquery": tsquery}) if tsquery else []

    candidates = fuse(dense_rows, sparse_rows, config.rrf_k)
    return RetrievalOutcome(
        candidates=candidates,
        context=candidates[: config.context_top_n],
        dense_count=len(dense_rows),
        sparse_count=len(sparse_rows),
    )


def to_tsquery_terms(question: str) -> str:
    """Turn a question into a tsquery, or "" when nothing searchable is left.

    Terms are OR-ed, not AND-ed. An AND query only matches chunks containing
    *every* word of the question, which for a natural-language question is
    almost never true — the sparse half would then contribute nothing and the
    hybrid search would silently degrade to dense-only. With OR, ts_rank_cd
    ranks by how well a chunk covers the question and RRF weighs that ranking
    against the dense one, which is the point of fusing two rankings.
    """
    terms = [
        term
        for term in re.findall(r"\w+", question)
        if len(term) >= MIN_TSQUERY_TERM_LENGTH and term.lower() not in STOP_WORDS
    ]
    return " | ".join(terms[:MAX_TSQUERY_TERMS])


def fuse(
    dense_rows: Sequence[Mapping[str, Any]],
    sparse_rows: Sequence[Mapping[str, Any]],
    rrf_k: int,
) -> list[RetrievalHit]:
    """Reciprocal rank fusion: score = sum of 1/(k + rank) over both rankings.

    RRF combines rankings, not scores, which is why a cosine similarity and a
    ts_rank_cd value can be merged at all without normalising two incomparable
    scales (ADR-007).
    """
    dense_ranks = {row["chunk_id"]: rank for rank, row in enumerate(dense_rows, start=1)}
    sparse_ranks = {row["chunk_id"]: rank for rank, row in enumerate(sparse_rows, start=1)}

    # Dense last so that it wins: in a dict comprehension the later key
    # overwrites the earlier one, so a chunk found by both searches keeps its
    # dense row. The two rows carry identical column values anyway — the ranks
    # that actually differ are tracked separately above.
    rows_by_id = {row["chunk_id"]: row for row in [*sparse_rows, *dense_rows]}

    hits = [
        RetrievalHit(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            filename=row["filename"],
            content=row["content"],
            page=row["page"],
            heading=row["heading"],
            score=float(row["score"]),
            dense_rank=dense_ranks.get(chunk_id, RANK_ABSENT),
            sparse_rank=sparse_ranks.get(chunk_id, RANK_ABSENT),
            rrf_score=_rrf_score(dense_ranks.get(chunk_id), sparse_ranks.get(chunk_id), rrf_k),
        )
        for chunk_id, row in rows_by_id.items()
    ]

    # Similarity breaks ties: two chunks found only by the same search share an
    # RRF score exactly, and without a second key their order would depend on
    # dict iteration — the context would differ between runs of the same query.
    hits.sort(key=lambda hit: (hit.rrf_score, hit.score), reverse=True)
    return hits


def _rrf_score(dense_rank: int | None, sparse_rank: int | None, rrf_k: int) -> float:
    ranks = [rank for rank in (dense_rank, sparse_rank) if rank is not None]
    return sum(1.0 / (rrf_k + rank) for rank in ranks)


async def _fetch(
    db: AsyncSession, statement: Any, params: dict[str, Any]
) -> list[Mapping[str, Any]]:
    result = await db.execute(statement, params)
    # Materialised as plain dicts: a RowMapping stays bound to the result set,
    # and fuse() should work on rows, not on a driver type.
    return [dict(row) for row in result.mappings()]
