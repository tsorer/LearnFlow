"""POST /quiz/generate — Stefan asks for question suggestions (US-07, T-33).

The endpoint is a proposal generator, not a publisher: everything it writes is
`pending` and invisible to learners until the review of T-35 says otherwise.
That is why there is no confidence pipeline here (ADR-008 covers the answer
path, where nobody stands between the model and the user) — the human gate does
that job, and the machine-checked source index of app/services/quiz.py does the
rest.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_knowledge_owner
from app.database import get_db
from app.limiter import account_key, limiter
from app.models.tables import QuizQuestion, QuizQuestionStatus, User
from app.routers.documents import PILOT_AREA
from app.services.quiz import CONTEXT_CHUNK_COUNT, GeneratedQuestion, generate_quiz
from app.services.retrieval import sample_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["quiz"])

# Lower than /query's ten: one click here is a batch of five questions out of a
# ten-chunk context, so it costs several times an answer. Per account rather
# than per address for the same reason as there — the pilot users share one NAT
# address (app/limiter.py).
QUIZ_RATE_LIMIT = "3/minute"


class QuizQuestionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_id: uuid.UUID | None
    question: str
    options: list[str]
    correct_answer: str
    explanation: str
    source_excerpt: str
    # As in DocumentResponse: the column is a plain varchar, so a value outside
    # the enum fails here instead of reaching a client that has no type for it.
    status: QuizQuestionStatus
    created_at: datetime
    approved_at: datetime | None


class QuizGenerationResponse(BaseModel):
    generated: int
    questions: list[QuizQuestionResponse]


@router.post(
    "/generate",
    response_model=QuizGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(QUIZ_RATE_LIMIT, key_func=account_key)
async def generate_questions(
    # slowapi reads its key off the raw request and insists the argument be
    # named `request`, exactly as in query.py. There is no body.
    request: Request,
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
) -> QuizGenerationResponse:
    sources = await sample_chunks(db, PILOT_AREA, CONTEXT_CHUNK_COUNT)
    if not sources:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Im Bereich ist kein indexiertes Dokument vorhanden.",
        )

    try:
        generated = await generate_quiz(sources)
    except (TypeError, AttributeError, NameError, ImportError):
        # A bug must not masquerade as a provider outage — same rule as
        # query.py: broken code belongs in the logs as a 500.
        raise
    except Exception:
        # The provider message is logged, never returned: LiteLLM errors carry
        # api_base, deployment names and, on an auth failure, a fragment of the
        # key. An unreadable response lands here too, through the ValueError of
        # generate_quiz.
        logger.exception("Quiz-Generierung fehlgeschlagen für user_id=%s", user.id)
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quiz-Generierung ist derzeit nicht verfügbar. Bitte später erneut versuchen.",
        )

    if not generated:
        # Every question failed validation. Not a successful run that happens to
        # be empty: the model returned something, and none of it was usable —
        # which is a failure of the call, and is reported as one (ADR-008).
        logger.warning("Quiz-Generierung ohne verwertbare Frage für user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quiz-Generierung ist derzeit nicht verfügbar. Bitte später erneut versuchen.",
        )

    rows = [_to_row(question) for question in generated]
    for row in rows:
        db.add(row)
    await db.commit()

    return QuizGenerationResponse(
        generated=len(rows), questions=[_to_response(row) for row in rows]
    )


def _to_row(question: GeneratedQuestion) -> QuizQuestion:
    return QuizQuestion(
        id=uuid.uuid4(),
        document_id=question.source.document_id,
        chunk_id=question.source.chunk_id,
        question=question.question,
        options=question.options,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        # The passage is copied, not just referenced: the chunk goes when the
        # document is replaced, and the review still has to show what the
        # question was built from (US-07, models/tables.py QuizQuestion).
        source_excerpt=question.source.content,
        status=QuizQuestionStatus.pending,
        # Assigned in Python rather than left to the column default, for the
        # same reason as in documents.py: with expire_on_commit=False the
        # response would otherwise carry no value at all.
        created_at=datetime.now(UTC),
    )


def _to_response(row: QuizQuestion) -> QuizQuestionResponse:
    return QuizQuestionResponse(
        id=row.id,
        document_id=row.document_id,
        chunk_id=row.chunk_id,
        question=row.question,
        options=row.options,
        correct_answer=row.correct_answer,
        explanation=row.explanation,
        source_excerpt=row.source_excerpt,
        status=QuizQuestionStatus(row.status),
        created_at=row.created_at,
        approved_at=row.approved_at,
    )
