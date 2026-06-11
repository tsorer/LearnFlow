import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.models.tables import Answer, QuerySession, User
from app.services.rag import process_query

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    session_id: str | None = None


class CitationOut(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page: int | None
    excerpt: str
    index: int


class ConfidenceInfo(BaseModel):
    score: float
    retrieval_score: float
    citation_coverage: float


class ChunkDebugOut(BaseModel):
    filename: str
    page: int | None
    heading: str | None
    score: float
    above_threshold: bool
    in_top_n: bool
    dense_rank: int
    content: str


class StageInfo(BaseModel):
    id: str
    name: str
    ran: bool
    passed: bool
    value: Any
    threshold: float | int | None
    detail: str


class LLMCallOut(BaseModel):
    step: str
    label: str
    prompt: str
    response: str


class DebugInfo(BaseModel):
    chunks: list[ChunkDebugOut]
    stages: list[StageInfo]
    llm_calls: list[LLMCallOut]
    similarity_threshold: float
    min_retrieval_confidence: float
    min_citation_coverage: float
    self_check_ran: bool
    self_check_verdict: str | None
    retrieval_detail: dict
    params_used: dict
    dense_above_threshold: int
    total_dense_retrieved: int
    sparse_count: int
    top_n_used: int
    formula_breakdown: str


class QueryResponse(BaseModel):
    session_id: str
    answer_id: str
    suppressed: bool
    suppression_reason: str | None = None
    message: str | None = None
    refinement_hint: str | None = None
    citations: list[CitationOut] = []
    confidence: ConfidenceInfo | None = None
    debug: DebugInfo | None = None


async def _load_config(db: AsyncSession) -> dict:
    rows = await db.execute(text("SELECT key, value FROM config"))
    return {r.key: r.value for r in rows}


@router.post("", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await _load_config(db)

    # Get or create session
    if body.session_id:
        result = await db.execute(
            select(QuerySession).where(
                QuerySession.id == body.session_id,
                QuerySession.user_id == user.id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = QuerySession(id=uuid.uuid4(), user_id=user.id)
        db.add(session)
        await db.flush()

    result = await process_query(body.question, db, cfg)

    answer = Answer(
        id=uuid.uuid4(),
        session_id=session.id,
        question=body.question,
        answer_text=result.answer,
        suppressed=result.suppressed,
        suppression_reason=result.suppression_reason,
        confidence_score=result.confidence_score,
        retrieval_score=result.retrieval_score,
        citation_coverage=result.citation_coverage,
        citations=[
            {"chunk_id": c.chunk_id, "document_id": c.document_id,
             "filename": c.filename, "page": c.page, "excerpt": c.excerpt, "index": c.index}
            for c in result.citations
        ],
    )
    db.add(answer)
    await db.commit()

    min_ret_conf = float(cfg.get("min_retrieval_confidence", settings.min_retrieval_confidence))
    min_cit_cov = float(cfg.get("min_citation_coverage", settings.min_citation_coverage))

    return QueryResponse(
        session_id=str(session.id),
        answer_id=str(answer.id),
        suppressed=result.suppressed,
        suppression_reason=result.suppression_reason,
        message=result.answer,
        refinement_hint=result.refinement_hint,
        citations=[
            CitationOut(**{k: getattr(c, k) for k in CitationOut.model_fields})
            for c in result.citations
        ],
        confidence=ConfidenceInfo(
            score=result.confidence_score or 0.0,
            retrieval_score=result.retrieval_score or 0.0,
            citation_coverage=result.citation_coverage or 0.0,
        ),
        debug=DebugInfo(
            chunks=[
                ChunkDebugOut(
                    filename=c.filename, page=c.page, heading=c.heading,
                    score=c.score, above_threshold=c.above_threshold,
                    in_top_n=c.in_top_n, dense_rank=c.dense_rank,
                    content=c.content,
                )
                for c in result.debug_chunks
            ],
            stages=[StageInfo(**s) for s in result.stages],
            llm_calls=[LLMCallOut(**c) for c in result.llm_calls],
            similarity_threshold=result.similarity_threshold,
            min_retrieval_confidence=min_ret_conf,
            min_citation_coverage=min_cit_cov,
            self_check_ran=result.self_check_ran,
            self_check_verdict=result.self_check_verdict,
            retrieval_detail=result.retrieval_detail,
            params_used=result.params_used,
            dense_above_threshold=result.dense_above_threshold,
            total_dense_retrieved=result.total_dense_retrieved,
            sparse_count=result.sparse_count,
            top_n_used=result.top_n_used,
            formula_breakdown=(
                f"0.6 × Retrieval({round((result.retrieval_score or 0) * 100)}%) "
                f"+ 0.4 × Citation({round((result.citation_coverage or 0) * 100)}%) "
                f"= {round((result.confidence_score or 0) * 100)}%"
            ),
        ),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuerySession).where(
            QuerySession.id == session_id,
            QuerySession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return {"message": "deleted"}
