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
    compute_retrieval_confidence_detail,
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
class ChunkDebug:
    filename: str
    page: int | None
    heading: str | None
    score: float
    above_threshold: bool
    content: str
    in_top_n: bool = False
    dense_rank: int = 0


@dataclass
class QueryResult:
    suppressed: bool
    suppression_reason: str | None = None
    answer: str | None = None
    citations: list[Citation] = field(default_factory=list)
    confidence_score: float | None = None
    retrieval_score: float | None = None
    citation_coverage: float | None = None
    refinement_hint: str | None = None
    debug_chunks: list[ChunkDebug] = field(default_factory=list)
    similarity_threshold: float = 0.0
    stages: list[dict] = field(default_factory=list)
    self_check_ran: bool = False
    self_check_verdict: str | None = None
    retrieval_detail: dict = field(default_factory=dict)
    params_used: dict = field(default_factory=dict)
    dense_above_threshold: int = 0
    total_dense_retrieved: int = 0
    sparse_count: int = 0
    top_n_used: int = 0
    llm_calls: list[dict] = field(default_factory=list)


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


def _parse_opt_float(val: str | None) -> float | None:
    if not val:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_opt_int(val: str | None) -> int | None:
    if not val:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


async def _llm_complete(
    prompt: str, model: str | None = None, llm_cfg: dict | None = None
) -> str:
    kwargs = {
        "model": model or settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "api_key": settings.openai_api_key,
    }
    if settings.litellm_base_url:
        kwargs["api_base"] = settings.litellm_base_url
        kwargs["api_version"] = settings.litellm_api_version
        kwargs["api_key"] = settings.litellm_api_key
    if llm_cfg:
        for param in ("temperature", "max_tokens", "top_p", "seed"):
            if llm_cfg.get(param) is not None:
                kwargs[param] = llm_cfg[param]

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

    llm_temperature = _parse_opt_float(cfg.get("llm_temperature"))
    llm_max_tokens  = _parse_opt_int(cfg.get("llm_max_tokens"))
    llm_top_p       = _parse_opt_float(cfg.get("llm_top_p"))
    llm_seed        = _parse_opt_int(cfg.get("llm_seed"))
    llm_cfg = {
        "temperature": llm_temperature,
        "max_tokens":  llm_max_tokens,
        "top_p":       llm_top_p,
        "seed":        llm_seed,
    }

    params_used = {
        "similarity_threshold": threshold,
        "min_retrieval_confidence": min_ret_conf,
        "min_citation_coverage": min_cit_cov,
        "top_k": top_k,
        "top_n": top_n,
        "self_check_band_low": sc_low,
        "self_check_band_high": sc_high,
        "llm_temperature": llm_temperature,
        "llm_max_tokens":  llm_max_tokens,
        "llm_top_p":       llm_top_p,
        "llm_seed":        llm_seed,
    }

    # 1. Embed query
    query_embedding = await emb_service.embed_one(question)

    # 2. Dense retrieval — fetch all candidates for debug (no threshold), then filter
    all_dense = await _dense_retrieve(query_embedding, db, top_k * 2, 0.0)
    dense = [c for c in all_dense if c.score >= threshold]

    stages: list[dict] = [
        {
            "id": "stage0",
            "name": "Similarity-Schwellwert",
            "ran": True,
            "passed": len(dense) > 0,
            "value": len(dense),
            "threshold": 1,
            "detail": f"{len(dense)} von {len(all_dense)} Chunks ≥ Schwellwert ({round(threshold * 100)}%)",
        }
    ]

    debug_chunks = [
        ChunkDebug(
            filename=c.filename, page=c.page, heading=c.heading,
            score=round(c.score, 4), above_threshold=c.score >= threshold,
            content=c.content, dense_rank=i + 1,
        )
        for i, c in enumerate(all_dense)
    ]

    if not dense:
        stages.extend([
            {"id": "stage1", "name": "Min. Retrieval-Konfidenz", "ran": False, "passed": False,
             "value": None, "threshold": min_ret_conf, "detail": "Nicht ausgeführt — keine Chunks über Similarity-Schwellwert"},
            {"id": "stage2", "name": "Min. Citation-Coverage", "ran": False, "passed": False,
             "value": None, "threshold": min_cit_cov, "detail": "Nicht ausgeführt"},
            {"id": "stage3", "name": "Self-Check Zone", "ran": False, "passed": False,
             "value": None, "threshold": None, "detail": "Nicht ausgeführt"},
        ])
        return QueryResult(
            suppressed=False,
            suppression_reason="no_relevant_chunks",
            answer="Ich weiss es nicht. Es wurden keine relevanten Quellen im Korpus gefunden.",
            confidence_score=0.0,
            retrieval_score=0.0, citation_coverage=0.0,
            debug_chunks=debug_chunks, similarity_threshold=threshold,
            stages=stages, params_used=params_used,
            dense_above_threshold=0, total_dense_retrieved=len(all_dense),
            retrieval_detail={"top_score": 0.0, "mean_score": 0.0,
                              "evidence_density": 0.0, "result": 0.0, "count": 0},
        )

    # Stage 1: retrieval confidence — MUST be computed before RRF, which mutates scores in-place
    ret_detail = compute_retrieval_confidence_detail(dense[:top_n])
    retrieval_confidence = ret_detail["result"]

    # 3. Sparse retrieval + RRF fusion (mutates .score on RetrievalResult objects)
    sparse = await _sparse_retrieve(question, db, top_k)
    fused = _reciprocal_rank_fusion(dense, sparse)
    top_chunks = fused[:top_n]
    top_chunk_ids = {c.chunk_id for c in top_chunks}

    # debug_chunks[i] was built from all_dense[i] before RRF mutation, scores are cosine
    for i, dc in enumerate(debug_chunks):
        dc.in_top_n = all_dense[i].chunk_id in top_chunk_ids
    stage1_passed = retrieval_confidence >= min_ret_conf
    stages.append({
        "id": "stage1",
        "name": "Min. Retrieval-Konfidenz",
        "ran": True,
        "passed": stage1_passed,
        "value": retrieval_confidence,
        "threshold": min_ret_conf,
        "detail": (
            f"0.5×top({round(ret_detail['top_score']*100)}%) + "
            f"0.3×mean({round(ret_detail['mean_score']*100)}%) + "
            f"0.2×density({round(ret_detail['evidence_density']*100)}%) "
            f"= {round(retrieval_confidence*100)}%"
        ),
    })

    would_suppress: str | None = None
    if not stage1_passed:
        would_suppress = "low_retrieval_confidence"

    # 4. Build context + generate answer
    context = _build_context(top_chunks)
    prompt = GROUNDING_PROMPT.format(context=context, question=question)
    answer = await _llm_complete(prompt, llm_cfg=llm_cfg)
    llm_calls: list[dict] = [{"step": "grounding", "label": "Antwort generieren", "prompt": prompt, "response": answer}]

    # Stage 2: citation coverage
    citation_coverage = compute_citation_coverage(answer, [c.chunk_id for c in top_chunks])
    stage2_passed = citation_coverage >= min_cit_cov
    stages.append({
        "id": "stage2",
        "name": "Min. Citation-Coverage",
        "ran": True,
        "passed": stage2_passed,
        "value": citation_coverage,
        "threshold": min_cit_cov,
        "detail": f"{round(citation_coverage*100)}% der Sätze enthalten Quellenangaben [N]",
    })
    if would_suppress is None and not stage2_passed:
        would_suppress = "low_citation_coverage"

    # Composite needed before Stage 3 to decide if self-check should run
    confidence_score = compute_composite_confidence(retrieval_confidence, citation_coverage)

    # Composite below zone: clearly bad quality — flag STOPP without LLM call
    if would_suppress is None and confidence_score < sc_low:
        would_suppress = "low_composite_score"

    # Stage 3: self-check for borderline answers (only if composite is in zone)
    self_check_ran = False
    self_check_verdict: str | None = None
    borderline = is_borderline(retrieval_confidence, citation_coverage, sc_low, sc_high)
    if would_suppress is None and borderline:
        self_check_ran = True
        check_prompt = SELF_CHECK_PROMPT.format(answer=answer, context=context)
        raw_verdict = await _llm_complete(check_prompt, llm_cfg=llm_cfg)
        self_check_verdict = "NEIN" if "NEIN" in raw_verdict.upper() else "JA"
        if self_check_verdict == "NEIN":
            would_suppress = "self_check_failed"
        llm_calls.append({"step": "self_check", "label": "Self-Check", "prompt": check_prompt, "response": raw_verdict})

    if self_check_ran:
        sc_detail = f"Verdict: {self_check_verdict}"
    elif would_suppress == "low_composite_score":
        sc_detail = f"Nicht ausgeführt — Composite unter Self-Check Zone (STOPP bereits gesetzt)"
    elif would_suppress is not None:
        sc_detail = f"Nicht ausgeführt — vorherige Stage hat STOPP gesetzt"
    elif confidence_score >= sc_high:
        sc_detail = f"Nicht ausgeführt — Composite ({round(confidence_score*100)}%) über Self-Check Zone ({round(sc_low*100)}%–{round(sc_high*100)}%) → ausreichend"
    else:
        sc_detail = f"Nicht ausgeführt"

    stages.append({
        "id": "stage3",
        "name": "Self-Check Zone",
        "ran": self_check_ran,
        "passed": self_check_verdict != "NEIN" if self_check_ran else True,
        "value": self_check_verdict,
        "threshold": None,
        "detail": sc_detail,
    })

    # 5. Build citations
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

    return QueryResult(
        suppressed=False,
        suppression_reason=would_suppress,
        answer=answer,
        citations=citations,
        confidence_score=confidence_score,
        retrieval_score=retrieval_confidence,
        citation_coverage=citation_coverage,
        debug_chunks=debug_chunks,
        similarity_threshold=threshold,
        stages=stages,
        self_check_ran=self_check_ran,
        self_check_verdict=self_check_verdict,
        retrieval_detail=ret_detail,
        params_used=params_used,
        dense_above_threshold=len(dense),
        total_dense_retrieved=len(all_dense),
        sparse_count=len(sparse),
        top_n_used=len(top_chunks),
        llm_calls=llm_calls,
    )
