import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
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
    band: str
    score: float
    retrieval_score: float
    citation_coverage: float


class QueryResponse(BaseModel):
    session_id: str
    answer_id: str
    suppressed: bool
    suppression_reason: str | None = None
    message: str | None = None
    refinement_hint: str | None = None
    citations: list[CitationOut] = []
    confidence: ConfidenceInfo | None = None


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
        confidence_band=result.confidence_band,
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

    return QueryResponse(
        session_id=str(session.id),
        answer_id=str(answer.id),
        suppressed=result.suppressed,
        suppression_reason=result.suppression_reason,
        message=result.answer if not result.suppressed else "Ich weiss es nicht.",
        refinement_hint=result.refinement_hint,
        citations=[
            CitationOut(**{k: getattr(c, k) for k in CitationOut.model_fields})
            for c in result.citations
        ],
        confidence=ConfidenceInfo(
            band=result.confidence_band or "low",
            score=result.confidence_score or 0.0,
            retrieval_score=result.retrieval_score or 0.0,
            citation_coverage=result.citation_coverage or 0.0,
        ) if not result.suppressed else None,
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
