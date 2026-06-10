"""RAG pipeline: Hybrid Retrieval + ADR-008 Confidence Pipeline."""

import re
from dataclasses import dataclass, field

import litellm
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services import embedding as emb_service
from app.services.confidence import (
    RetrievalResult,
    compute_citation_coverage,
    compute_composite_confidence,
    compute_retrieval_confidence,
    is_borderline,
    parse_cited_indices,
)


@dataclass
class Citation:
    chunk_id: str
    document_id: str
    filename: str
    page: int | None
    excerpt: str
    index: int


@dataclass
class QueryResult:
    suppressed: bool
    suppression_reason: str | None = None
    answer: str | None = None
    citations: list[Citation] = field(default_factory=list)
    confidence_score: float | None = None
    confidence_band: str | None = None
    retrieval_score: float | None = None
    citation_coverage: float | None = None
    refinement_hint: str | None = None


GROUNDING_PROMPT = """\
Du bist ein Lernassistent für neue Mitarbeitende. Antworte NUR auf Basis der bereitgestellten Quellen.
Belege JEDE Aussage mit mindestens einer Quellenangabe in der Form [1], [2] usw.
Wenn die Quellen keine ausreichende Antwort ermöglichen, schreibe ausschliesslich: "Ich weiss es nicht."
Antworte präzise und auf Deutsch.

Quellen:
{context}

Frage: {question}

Antwort (mit Quellenangaben [1], [2] etc.):"""

SELF_CHECK_PROMPT = """\
Prüfe diese Antwort auf Basis der Quellen:

Antwort: {answer}

Quellen:
{context}

Ist jede Aussage der Antwort vollständig durch die Quellen belegt?
Antworte NUR mit "JA" oder "NEIN".
"""


async def _dense_retrieve(
    query_embedding: list[float], db: AsyncSession, top_k: int, threshold: float
) -> list[RetrievalResult]:
    rows = await db.execute(
        text("""
            SELECT c.id, c.content, c.document_id, c.page, c.heading,
                   d.filename,
                   1 - (c.embedding <=> CAST(:emb AS vector)) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.status = 'available'
              AND 1 - (c.embedding <=> CAST(:emb AS vector)) >= :threshold
            ORDER BY c.embedding <=> CAST(:emb AS vector)
            LIMIT :top_k
        """),
        {"emb": str(query_embedding), "threshold": threshold, "top_k": top_k},
    )
    return [
        RetrievalResult(
            chunk_id=str(r.id), content=r.content, score=float(r.score),
            document_id=str(r.document_id), filename=r.filename,
            page=r.page, heading=r.heading,
        )
        for r in rows
    ]


async def _sparse_retrieve(
    question: str, db: AsyncSession, top_k: int
) -> list[RetrievalResult]:
    rows = await db.execute(
        text("""
            SELECT c.id, c.content, c.document_id, c.page, c.heading,
                   d.filename,
                   ts_rank_cd(c.tsv, query) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id,
                 to_tsquery('german', :query) query
            WHERE d.status = 'available'
              AND c.tsv @@ query
            ORDER BY score DESC
            LIMIT :top_k
        """),
        {"query": _to_tsquery(question), "top_k": top_k},
    )
    return [
        RetrievalResult(
            chunk_id=str(r.id), content=r.content, score=float(r.score),
            document_id=str(r.document_id), filename=r.filename,
            page=r.page, heading=r.heading,
        )
        for r in rows
    ]


def _to_tsquery(text: str) -> str:
    words = re.findall(r"\w+", text)
    return " & ".join(words[:10]) if words else "placeholder"


def _reciprocal_rank_fusion(
    dense: list[RetrievalResult], sparse: list[RetrievalResult], k: int = 60
) -> list[RetrievalResult]:
    scores: dict[str, float] = {}
    by_id: dict[str, RetrievalResult] = {}

    for rank, r in enumerate(dense):
        scores[r.chunk_id] = scores.get(r.chunk_id, 0) + 1 / (k + rank + 1)
        by_id[r.chunk_id] = r

    for rank, r in enumerate(sparse):
        scores[r.chunk_id] = scores.get(r.chunk_id, 0) + 1 / (k + rank + 1)
        by_id.setdefault(r.chunk_id, r)

    ranked = sorted(scores.keys(), key=lambda cid: -scores[cid])
    results = []
    for cid in ranked:
        r = by_id[cid]
        r.score = round(scores[cid], 6)
        results.append(r)
    return results


def _build_context(chunks: list[RetrievalResult]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        header = f"[{i}] {c.filename}"
        if c.page:
            header += f", S.{c.page}"
        if c.heading:
            header += f" — {c.heading}"
        parts.append(f"{header}:\n{c.content[:800]}")
    return "\n\n".join(parts)


async def _llm_complete(prompt: str, model: str | None = None) -> str:
    kwargs = {
        "model": model or settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "api_key": settings.openai_api_key,
    }
    if settings.litellm_base_url:
        kwargs["api_base"] = settings.litellm_base_url
        kwargs["api_version"] = settings.litellm_api_version
        kwargs["api_key"] = settings.litellm_api_key

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content.strip()


async def process_query(
    question: str,
    db: AsyncSession,
    cfg: dict | None = None,
) -> QueryResult:
    cfg = cfg or {}
    threshold = float(cfg.get("similarity_threshold", settings.similarity_threshold))
    min_ret_conf = float(cfg.get("min_retrieval_confidence", settings.min_retrieval_confidence))
    min_cit_cov = float(cfg.get("min_citation_coverage", settings.min_citation_coverage))
    top_k = int(cfg.get("top_k", settings.top_k))
    top_n = int(cfg.get("top_n", settings.top_n))
    sc_low = float(cfg.get("self_check_band_low", settings.self_check_band_low))
    sc_high = float(cfg.get("self_check_band_high", settings.self_check_band_high))

    # 1. Embed query
    query_embedding = await emb_service.embed_one(question)

    # 2. Dense retrieval
    dense = await _dense_retrieve(query_embedding, db, top_k, threshold)

    # Stage 0: no chunk above threshold
    if not dense:
        return QueryResult(
            suppressed=True,
            suppression_reason="no_relevant_chunks",
            refinement_hint="Bitte formuliere die Frage konkreter oder nenne ein spezifisches Thema.",
        )

    # 3. Sparse retrieval + RRF fusion
    sparse = await _sparse_retrieve(question, db, top_k)
    fused = _reciprocal_rank_fusion(dense, sparse)
    top_chunks = fused[:top_n]

    # Stage 1: retrieval confidence
    retrieval_confidence = compute_retrieval_confidence(top_chunks)
    if retrieval_confidence < min_ret_conf:
        return QueryResult(
            suppressed=True,
            suppression_reason="low_retrieval_confidence",
            retrieval_score=retrieval_confidence,
        )

    # 4. Build context + generate answer
    context = _build_context(top_chunks)
    prompt = GROUNDING_PROMPT.format(context=context, question=question)
    answer = await _llm_complete(prompt)

    # Stage 2: citation coverage check
    citation_coverage = compute_citation_coverage(answer, [c.chunk_id for c in top_chunks])
    if citation_coverage < min_cit_cov:
        return QueryResult(
            suppressed=True,
            suppression_reason="low_citation_coverage",
            retrieval_score=retrieval_confidence,
            citation_coverage=citation_coverage,
        )

    # Stage 3: self-check for borderline answers
    if is_borderline(retrieval_confidence, citation_coverage, sc_low, sc_high):
        check_prompt = SELF_CHECK_PROMPT.format(answer=answer, context=context)
        verdict = await _llm_complete(check_prompt)
        if "NEIN" in verdict.upper():
            return QueryResult(
                suppressed=True,
                suppression_reason="self_check_failed",
                retrieval_score=retrieval_confidence,
                citation_coverage=citation_coverage,
            )

    # 5. Build citations from parsed indices
    cited_indices = parse_cited_indices(answer)
    citations = []
    for idx in set(cited_indices):
        if 0 <= idx < len(top_chunks):
            c = top_chunks[idx]
            citations.append(Citation(
                chunk_id=c.chunk_id, document_id=c.document_id,
                filename=c.filename, page=c.page,
                excerpt=c.content[:300], index=idx + 1,
            ))

    confidence_score, confidence_band = compute_composite_confidence(
        retrieval_confidence, citation_coverage
    )

    return QueryResult(
        suppressed=False,
        answer=answer,
        citations=citations,
        confidence_score=confidence_score,
        confidence_band=confidence_band,
        retrieval_score=retrieval_confidence,
        citation_coverage=citation_coverage,
    )
