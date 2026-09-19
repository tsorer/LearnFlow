"""Trace two questions through the running LearnFlow pipeline, stage by stage.

Runs inside the api container. Two sources of truth, deliberately kept apart:

1. The authoritative run: a real POST /query against the running uvicorn, as
   the admin user, so `debug` is filled. Stages, LLM prompts and responses come
   from here — nothing about them is recomputed.
2. The deterministic intermediates the debug view does not expose: how the
   question is cut into search terms and tokens, the raw dense and sparse lists
   before fusion, how the document was chunked, how stage 2 segments the answer.
   These call the same service functions the handler calls and are checked
   against the authoritative run where the two overlap.

No production code is touched.
"""

import asyncio
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text

from app.auth.jwt import create_access_token
from app.database import AsyncSessionLocal
from app.models.tables import DocumentStatus
from app.services import confidence as C
from app.services import retrieval as R
from app.services.chunking import _encoding
from app.services.config import read_query_config
from app.services.embedding import embed_texts

API = "http://localhost:8000"
AREA = "default"
ADMIN_ID = "c43c8791-9c03-4ead-9a6d-c62194d78dd0"
OUT = Path("/tmp/pipeline-trace")

QUESTIONS = {
    "Q1": "Ich fahre innerorts 6 Km/h zu schnell wie hoch ist die Busse?",
    "Q2": "Ich wurde innerorts mit 6 zuschnell gebliztz was kostet mich das?",
}

# Where the answer actually is: OBV Anhang 1, Ziff. 303.1 (innerorts). Used only
# to locate the ground-truth chunks and report where they ranked — not by the
# pipeline.
GROUND_TRUTH_SQL = text(
    "SELECT c.id AS chunk_id, c.chunk_index, c.page, c.heading, c.content "
    "FROM chunks c JOIN documents d ON d.id = c.document_id "
    "WHERE d.filename LIKE 'fedlex%' AND c.content ILIKE '%innerorts%' "
    "AND c.content ~* 'km/h' ORDER BY c.chunk_index"
)

ALL_DENSE_SQL = text(
    "SELECT c.id AS chunk_id, 1 - (c.embedding <=> CAST(CAST(:embedding AS text) AS vector)) AS score "
    "FROM chunks c JOIN documents d ON d.id = c.document_id "
    "WHERE d.status = :status AND d.area = :area AND c.embedding IS NOT NULL "
    "ORDER BY c.embedding <=> CAST(CAST(:embedding AS text) AS vector)"
)

ALL_SPARSE_SQL = text(
    "SELECT c.id AS chunk_id, ts_rank_cd(c.tsv, to_tsquery('german', :tsquery)) AS ts_rank, "
    "tsvector_to_array(c.tsv) AS lexemes "
    "FROM chunks c JOIN documents d ON d.id = c.document_id "
    "WHERE d.status = :status AND d.area = :area AND c.embedding IS NOT NULL "
    "AND c.tsv @@ to_tsquery('german', :tsquery) "
    "ORDER BY ts_rank_cd(c.tsv, to_tsquery('german', :tsquery)) DESC"
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


async def authoritative_run(question: str) -> dict[str, Any]:
    token = create_access_token(ADMIN_ID, "admin")
    async with httpx.AsyncClient(base_url=API, timeout=120) as client:
        r = await client.post(
            "/query", json={"question": question}, headers={"Authorization": f"Bearer {token}"}
        )
        r.raise_for_status()
        return r.json()


def query_cutting(question: str) -> dict[str, Any]:
    raw = re.findall(r"\w+", question)
    per_token = []
    for tok in raw:
        if len(tok) < R.MIN_TSQUERY_TERM_LENGTH:
            reason = f"zu kurz (< {R.MIN_TSQUERY_TERM_LENGTH} Zeichen)"
        elif tok.lower() in R.STOP_WORDS:
            reason = "Stoppwort"
        else:
            reason = None
        per_token.append({"token": tok, "kept": reason is None, "dropped_because": reason})
    kept = [t["token"] for t in per_token if t["kept"]]
    enc = _encoding()
    ids = enc.encode(question)
    return {
        "regex_tokens": raw,
        "per_token": per_token,
        "kept_terms": kept,
        "cut_by_max_terms": kept[R.MAX_TSQUERY_TERMS:],
        "tsquery_input": R.to_tsquery_terms(question),
        "bpe_tokens_for_embedding": {
            "encoding": enc.name,
            "count": len(ids),
            "pieces": [enc.decode([i]) for i in ids],
        },
    }


async def trace(key: str, question: str) -> dict[str, Any]:
    print(f"[{key}] authoritative run …", flush=True)
    api = await authoritative_run(question)
    debug = api.get("debug") or {}

    async with AsyncSessionLocal() as db:
        cfg = await read_query_config(db)
        p, th = cfg.pipeline, cfg.thresholds

        cutting = query_cutting(question)
        tsq = cutting["tsquery_input"]
        pg = (
            await db.execute(
                text(
                    "SELECT to_tsquery('german', :q)::text AS tsquery, "
                    "to_tsvector('german', :question)::text AS question_tsvector"
                ),
                {"q": tsq or "''", "question": question},
            )
        ).mappings().one()
        query_lexemes = sorted(set(re.findall(r"'([^']+)'", pg["tsquery"])))
        cutting["postgres_tsquery"] = pg["tsquery"]
        cutting["postgres_question_tsvector"] = pg["question_tsvector"]
        cutting["query_lexemes"] = query_lexemes

        print(f"[{key}] embedding + searches …", flush=True)
        embedding = (await embed_texts([question]))[0]
        params = {
            "embedding": json.dumps(embedding),
            "area": AREA,
            "top_k": p.retrieval_top_k,
            "status": DocumentStatus.available,
        }
        emb_info = {
            "dimensions": len(embedding),
            "l2_norm": math.sqrt(sum(x * x for x in embedding)),
            "first_8": embedding[:8],
        }

        dense_rows = await R._fetch(db, R.DENSE_SQL, params)
        sparse_rows = (
            await R._fetch(db, R.SPARSE_SQL, {**params, "tsquery": tsq}) if tsq else []
        )

        # Full rankings over the whole corpus — to say where a chunk stood even
        # when it did not make the top_k cut.
        all_dense = await R._fetch(db, ALL_DENSE_SQL, params)
        all_sparse = (
            await R._fetch(db, ALL_SPARSE_SQL, {**params, "tsquery": tsq}) if tsq else []
        )
        dense_pos = {r["chunk_id"]: (i, float(r["score"])) for i, r in enumerate(all_dense, 1)}
        sparse_pos = {
            r["chunk_id"]: (i, float(r["ts_rank"]), sorted(set(r["lexemes"]) & set(query_lexemes)))
            for i, r in enumerate(all_sparse, 1)
        }

        idx = {
            r["chunk_id"]: r
            for r in (
                await db.execute(
                    text("SELECT id AS chunk_id, chunk_index FROM chunks")
                )
            ).mappings()
        }

        def row_view(row: dict[str, Any], rank: int) -> dict[str, Any]:
            cid = row["chunk_id"]
            sp = sparse_pos.get(cid)
            return {
                "rank": rank,
                "chunk_id": cid,
                "filename": row["filename"],
                "chunk_index": idx[cid]["chunk_index"],
                "page": row["page"],
                "heading": row["heading"],
                "cosine": float(row["score"]),
                "ts_rank_cd": sp[1] if sp else None,
                "matched_lexemes": sp[2] if sp else [],
                "content_preview": row["content"][:220],
            }

        dense_list = [row_view(r, i) for i, r in enumerate(dense_rows, 1)]
        sparse_list = [row_view(r, i) for i, r in enumerate(sparse_rows, 1)]

        fused = R.fuse(dense_rows, sparse_rows, p.rrf_k)
        fusion = []
        for pos, h in enumerate(fused, 1):
            fusion.append(
                {
                    "fused_rank": pos,
                    "in_context": pos <= p.context_top_n,
                    "chunk_id": h.chunk_id,
                    "filename": h.filename,
                    "chunk_index": idx[h.chunk_id]["chunk_index"],
                    "page": h.page,
                    "heading": h.heading,
                    "cosine": h.score,
                    "above_similarity_threshold": h.score >= p.similarity_threshold,
                    "dense_rank": h.dense_rank,
                    "sparse_rank": h.sparse_rank,
                    "rrf_dense_part": 1 / (p.rrf_k + h.dense_rank) if h.dense_rank else 0.0,
                    "rrf_sparse_part": 1 / (p.rrf_k + h.sparse_rank) if h.sparse_rank else 0.0,
                    "rrf_score": h.rrf_score,
                }
            )
        context = fused[: p.context_top_n]

        # Consistency with the authoritative run: same context, same order?
        api_context = [c["chunk_id"] for c in debug.get("chunks", []) if c.get("in_top_n")]
        trace_context = [str(h.chunk_id) for h in context]

        scores = [h.score for h in context]
        gate = C.passes_retrieval_gate(scores, p.similarity_threshold)
        conf = C.compute_retrieval_confidence(scores, p.similarity_threshold, p.context_top_n)

        # Stage 2 on the text the model actually produced in the authoritative run.
        gen_calls = [c for c in debug.get("llm_calls", []) if c.get("step") != "self_check"]
        answer_text = gen_calls[0]["response"] if gen_calls else None
        seg_rows = []
        cit = None
        if answer_text is not None:
            for s in C._segments(answer_text):
                refs = sorted(C._references(s))
                legal = [r for r in refs if 1 <= r <= len(context)]
                words = C._word_count(C._REFERENCE.sub(" ", s))
                counted = words >= C.MIN_SEGMENT_WORDS
                seg_rows.append(
                    {
                        "segment": s,
                        "references": refs,
                        "legal_references": legal,
                        "fabricated": [r for r in refs if r not in legal],
                        "words_without_refs": words,
                        "counted": counted,
                        "covered": counted and bool(legal),
                    }
                )
            cit = C.check_citations(answer_text, len(context))

        composite = C.compute_composite(conf.result, cit.coverage if cit else None)
        band = C.band_for(composite.result, th.medium, th.high)
        in_sc_band = C.in_self_check_band(composite.result, p.self_check_band_low, p.self_check_band_high)

        # Chunking: how the documents behind the context were cut.
        enc = _encoding()
        docs = sorted({h.document_id for h in context})
        chunking = []
        for doc_id in docs:
            rows = (
                await db.execute(
                    text(
                        "SELECT c.id AS chunk_id, c.chunk_index, c.page, c.heading, c.content, d.filename "
                        "FROM chunks c JOIN documents d ON d.id = c.document_id "
                        "WHERE c.document_id = :d ORDER BY c.chunk_index"
                    ),
                    {"d": doc_id},
                )
            ).mappings().all()
            tokens = [len(enc.encode(r["content"])) for r in rows]
            by_index = {r["chunk_index"]: r for r in rows}
            ctx_chunks = []
            for h in context:
                if h.document_id != doc_id:
                    continue
                me = next(r for r in rows if r["chunk_id"] == h.chunk_id)
                prev = by_index.get(me["chunk_index"] - 1)
                overlap = _overlap_text(prev["content"], me["content"]) if prev else ""
                ctx_chunks.append(
                    {
                        "chunk_id": h.chunk_id,
                        "chunk_index": me["chunk_index"],
                        "page": me["page"],
                        "heading": me["heading"],
                        "tokens": len(enc.encode(me["content"])),
                        "overlap_with_previous": {"chars": len(overlap), "text": overlap},
                        "previous": {"chunk_index": prev["chunk_index"], "heading": prev["heading"], "page": prev["page"]} if prev else None,
                        "content": me["content"],
                    }
                )
            chunking.append(
                {
                    "document_id": doc_id,
                    "filename": rows[0]["filename"] if rows else None,
                    "chunk_count": len(rows),
                    "tokens_min": min(tokens) if tokens else None,
                    "tokens_median": statistics.median(tokens) if tokens else None,
                    "tokens_max": max(tokens) if tokens else None,
                    
                    "context_chunks": ctx_chunks,
                }
            )

        # Ground truth: where did the chunks that actually hold the answer rank?
        gt_rows = (await db.execute(GROUND_TRUTH_SQL)).mappings().all()
        ground_truth = []
        for r in gt_rows:
            cid = r["chunk_id"]
            d = dense_pos.get(cid)
            s = sparse_pos.get(cid)
            fused_rank = next((f["fused_rank"] for f in fusion if f["chunk_id"] == cid), None)
            ground_truth.append(
                {
                    "chunk_id": cid,
                    "chunk_index": r["chunk_index"],
                    "page": r["page"],
                    "heading": r["heading"],
                    "dense_rank_in_corpus": d[0] if d else None,
                    "cosine": d[1] if d else None,
                    "sparse_rank_in_corpus": s[0] if s else None,
                    "ts_rank_cd": s[1] if s else None,
                    "matched_lexemes": s[2] if s else [],
                    "fused_rank": fused_rank,
                    "in_context": fused_rank is not None and fused_rank <= p.context_top_n,
                    "content": r["content"],
                }
            )

    return _jsonable(
        {
            "key": key,
            "question": question,
            "config": {
                "pipeline": p.__dict__,
                "thresholds": th.__dict__,
            },
            "1_query_cutting": cutting,
            "2_embedding": emb_info,
            "3_dense_top_k": dense_list,
            "4_sparse_top_k": sparse_list,
            "4b_corpus_size": {"chunks_ranked_dense": len(all_dense), "chunks_matching_sparse": len(all_sparse)},
            "5_fusion": fusion,
            "6_stage0_gate": {
                "context_scores": scores,
                "threshold": p.similarity_threshold,
                "rule": "any(score >= similarity_threshold)",
                "passed": gate,
            },
            "7_stage1_confidence": {
                "detail": conf.__dict__,
                "formula": f"{C.WEIGHT_TOP_SCORE}*top + {C.WEIGHT_MEAN_SCORE}*mean + {C.WEIGHT_EVIDENCE_DENSITY}*density",
                "threshold": p.min_retrieval_confidence,
                "passed": conf.result >= p.min_retrieval_confidence,
            },
            "8_stage2_segments": seg_rows,
            "8_stage2_result": cit.__dict__ if cit else None,
            "9_composite": {"detail": composite.__dict__, "band": band,
                             "self_check_band": [p.self_check_band_low, p.self_check_band_high], "in_self_check_band": in_sc_band},
            "10_chunking": chunking,
            "11_ground_truth_chunks": ground_truth,
            "consistency": {
                "api_context_chunk_ids": api_context,
                "trace_context_chunk_ids": trace_context,
                "same_context_same_order": api_context == trace_context,
            },
            "api_response": api,
        }
    )


def _overlap_text(prev: str, cur: str) -> str:
    """Longest text that ends `prev` and starts `cur`, whitespace-normalised.

    Not token-exact: the chunker overlaps whole parts (sentences, lines) and
    re-joins them with the splitter's joiner, so the same text can carry a
    different line break on either side of the border.
    """
    a, b = " ".join(prev.split()), " ".join(cur.split())
    for n in range(min(len(a), len(b)), 0, -1):
        if a[-n:] == b[:n]:
            return a[-n:]
    return ""


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = sys.argv[1:] or list(QUESTIONS)
    for key in keys:
        result = await trace(key, QUESTIONS[key])
        (OUT / f"{key}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{key}] written, consistency={result['consistency']['same_context_same_order']}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
