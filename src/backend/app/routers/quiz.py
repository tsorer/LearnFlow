"""Generating quiz questions, and the human gate in front of them (US-07, US-08).

`POST /quiz/generate` (T-33) is a proposal generator, not a publisher:
everything it writes is `pending` and invisible to learners. That is why there
is no confidence pipeline here (ADR-008 covers the answer path, where nobody
stands between the model and the user) — the human gate does that job, and the
machine-checked source index of app/services/quiz.py does the rest.

`GET /quiz/questions` and `PATCH /quiz/questions/{question_id}` (T-49) are that
gate: the board of T-35 reads the first and writes through the second. What a
caller may see is decided here by role and never by the query string, which is
why the same GET also answers a learner — narrowed to approved questions.

`GET /quiz/questions/sample` (T-49) is the quiz run itself (T-36). It is a
separate path rather than a flag on the list because a sample and a page are
different things: the list is ordered and pageable so a board can show columns,
and bending it towards randomness would serve neither well.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_knowledge_owner
from app.database import get_db
from app.limiter import account_key, limiter
from app.models.tables import QuizQuestion, QuizQuestionStatus, User, UserRole
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


# --- review: reading and judging the generated questions (T-49) -------------

# Who is allowed to see a question that is not approved. Everything else — the
# learner, and any role added later without a thought spared for this list —
# sees approved questions only (ADR-008, fail-closed).
REVIEWER_ROLES = frozenset({UserRole.knowledge_owner.value, UserRole.admin.value})

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Laenge eines Quiz-Durchlaufs (US-08). Ein Parameter statt der Konstante waere
# Vorrat: die Story nennt fuenf, und niemand ausser T-36 ruft den Endpoint auf.
QUIZ_LENGTH = 5

# The writable fields that are the question's *content*, as opposed to the
# verdict on it. The distinction is what the reset rule of apply_update turns
# on. `document_id`, `chunk_id` and `source_excerpt` are on neither list: they
# are the evidence, not the content, and QuizQuestionUpdate refuses them.
CONTENT_FIELDS = ("question", "options", "correct_answer", "explanation")


class QuizQuestionPage(BaseModel):
    items: list[QuizQuestionResponse]
    # Counts the whole filter, not the page: the board shows a number per
    # column while loading one page per column.
    total: int


class QuizQuestionUpdate(BaseModel):
    """What a reviewer may change about a question (US-07).

    `extra="forbid"` is what rejects `document_id`, `chunk_id` and
    `source_excerpt` with a 422 instead of ignoring them in silence — they are
    the question's evidence, and a request that tries to rewrite the evidence
    is a misunderstanding worth reporting, not a no-op.

    Every field is optional because a PATCH is partial, but none of them is
    nullable: the columns behind them are NOT NULL, and `{"status": null}` is a
    contract violation rather than a way to clear a value. Both that and the
    empty body are rejected below, matching `minProperties: 1` and the absent
    `nullable` in openapi.yaml.
    """

    model_config = ConfigDict(extra="forbid")

    status: QuizQuestionStatus | None = None
    question: str | None = Field(None, min_length=1)
    options: list[Annotated[str, Field(min_length=1)]] | None = Field(
        None, min_length=4, max_length=4
    )
    correct_answer: Literal["A", "B", "C", "D"] | None = None
    explanation: str | None = Field(None, min_length=1)

    @model_validator(mode="after")
    def _reject_empty_and_null(self) -> "QuizQuestionUpdate":
        if not self.model_fields_set:
            raise ValueError("Mindestens ein Feld muss gesetzt sein.")
        nulled = sorted(field for field in self.model_fields_set if getattr(self, field) is None)
        if nulled:
            raise ValueError(f"Kein Feld ist nullbar: {', '.join(nulled)}")
        return self


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


def visible_statuses(
    role: str, requested: QuizQuestionStatus | None
) -> set[QuizQuestionStatus]:
    """Which statuses this role may see, narrowed by an optional filter.

    The filter can only cut the allowed set, never widen it: a learner asking
    for `pending` gets the intersection, which is empty, and therefore an empty
    page rather than a 403. That keeps the parameter a view onto one's own
    permitted rows instead of a request for permission (ADR-008, fail-closed),
    and it is what lets T-36 use this endpoint with the same query string as
    the board of T-35.
    """
    allowed = (
        set(QuizQuestionStatus)
        if role in REVIEWER_ROLES
        else {QuizQuestionStatus.approved}
    )
    return allowed if requested is None else allowed & {requested}


@router.get("/questions", response_model=QuizQuestionPage)
async def list_questions(
    # `status` is taken by the fastapi import above, hence the alias — the wire
    # name is what openapi.yaml declares, the local name only avoids shadowing.
    status_filter: QuizQuestionStatus | None = Query(None, alias="status"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizQuestionPage:
    statuses = visible_statuses(user.role, status_filter)
    if not statuses:
        # A learner asking for a status they may not see. Answered without
        # touching the database: there is provably nothing to return, and an
        # `IN ()` would only spell that out to Postgres.
        return QuizQuestionPage(items=[], total=0)

    values = [status_value.value for status_value in statuses]
    # Counted separately and without limit/offset — the board needs the size of
    # the column, not the size of the page it happens to be showing.
    total = await db.scalar(
        select(func.count()).select_from(QuizQuestion).where(QuizQuestion.status.in_(values))
    )
    result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.status.in_(values))
        # `id` as the tie-breaker, not decoration: the five questions of one
        # generation run are written in the same instant, and equal timestamps
        # leave the order of a paged query undefined — a row could then appear
        # on two pages or on none.
        .order_by(QuizQuestion.created_at.desc(), QuizQuestion.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return QuizQuestionPage(
        items=[_to_response(row) for row in result.scalars().all()], total=total or 0
    )


@router.get("/questions/sample", response_model=QuizQuestionPage)
async def sample_questions(
    # Deliberately declared before PATCH /questions/{question_id}: FastAPI takes
    # the first route that matches, and a future GET on that path would
    # otherwise swallow "sample" and fail to parse it as a UUID.
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizQuestionPage:
    """Five approved questions at random — the pool T-36 quizzes from (US-08).

    Not a page of `list_questions` with a different sort: that endpoint orders
    by `created_at` and would hand out the same five newest questions every
    time. The draw happens in SQL, as in `sample_chunks` of
    app/services/retrieval.py, because the alternative is shipping the whole
    approved pool to the browser so it can keep five of them.

    `approved` regardless of role, unlike the list: here a reviewer sees what a
    learner sees, which is the point of looking (ADR-008, fail-closed). Fewer
    than five is a normal result — the area holds what it holds — and no join
    to `documents` is needed to keep a stale question out, because replacing a
    document drops its questions back to `pending` (documents.py `_replace`).
    """
    approved = QuizQuestion.status == QuizQuestionStatus.approved.value
    total = await db.scalar(select(func.count()).select_from(QuizQuestion).where(approved))
    result = await db.execute(
        select(QuizQuestion).where(approved).order_by(func.random()).limit(QUIZ_LENGTH)
    )
    return QuizQuestionPage(
        items=[_to_response(row) for row in result.scalars().all()], total=total or 0
    )


def apply_update(row: QuizQuestion, patch: QuizQuestionUpdate, now: datetime) -> None:
    """Write the reviewer's changes onto the row, in the order the rules need.

    Content first, verdict second, because the second rule depends on whether
    the first one actually changed anything:

    - an explicit `status` wins. Every status but `approved` clears
      `approved_at` (a withdrawn approval has no moment); `approved` stamps it
      only when the approval is actually new — a re-sent `approved` on an
      unchanged, already approved question is not a second approval;
    - otherwise a content change to an approved question withdraws the
      approval. A request that edits *and* sends `status: approved` therefore
      stays approved — it is one step, and the reviewer saw the new text. One
      that only edits does not, because the approval on file would otherwise
      cover a text nobody approved (ADR-008).

    A field counts as changed only when its value differs from the stored one,
    not merely because it was sent: the board round-trips all four content
    fields when saving one of them, and a re-sent identical text is not an edit
    (same reasoning as the PUT of app/routers/admin.py).
    """
    changed_content = False
    for field in CONTENT_FIELDS:
        if field not in patch.model_fields_set:
            continue
        value = getattr(patch, field)
        if getattr(row, field) != value:
            setattr(row, field, value)
            changed_content = True

    if patch.status is not None:
        was_approved = row.status == QuizQuestionStatus.approved.value
        row.status = patch.status.value
        if patch.status is not QuizQuestionStatus.approved:
            row.approved_at = None
        elif changed_content or not was_approved or row.approved_at is None:
            # Only a *new* approval gets a new timestamp. Re-sending
            # `status: approved` for a question that already carries it is the
            # same non-event as re-sending its unchanged text above, and the
            # board round-trips both: without this, opening an approved
            # question in August and saving it unchanged would move its
            # approval date there, and US-07 asks for the moment of the
            # approval. `not was_approved` is kept next to the NULL check on
            # purpose — a row whose stamp was lost by hand is repaired rather
            # than carried forward.
            row.approved_at = now
    elif changed_content and row.status == QuizQuestionStatus.approved.value:
        row.status = QuizQuestionStatus.pending.value
        row.approved_at = None


@router.patch(
    "/questions/{question_id}",
    response_model=QuizQuestionResponse,
    dependencies=[Depends(require_knowledge_owner)],
)
async def update_question(
    question_id: uuid.UUID,
    patch: QuizQuestionUpdate,
    db: AsyncSession = Depends(get_db),
) -> QuizQuestionResponse:
    row = await db.get(QuizQuestion, question_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frage nicht gefunden")

    apply_update(row, patch, datetime.now(UTC))
    await db.commit()
    return _to_response(row)


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
