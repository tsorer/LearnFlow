"""POST /query — hybrid retrieval, the deterministic gates, generation (T-17/T-18).

The order is the point. The question is embedded, both searches run, the
candidates are fused, and stages 0 and 1 decide whether the found sources are
solid enough to spend an LLM call on. Only then is an answer generated, and only
from those chunks — a question that fails either gate never reaches the provider
at all (ADR-007).

Two stages of ADR-008 are still missing: the citation/grounding check (stage 2,
T-19) and the self-check (stage 3, T-25). Until they land, `citation_coverage`
stays 0.0, `confidence.score` is the retrieval score alone, and a delivered
answer rests on the two gates in front of it plus the grounding prompt — which
is why T-19 follows directly on T-18.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.tables import Answer, QuerySession, User
from app.routers.documents import PILOT_AREA
from app.services.confidence import (
    WEIGHT_EVIDENCE_DENSITY,
    WEIGHT_MEAN_SCORE,
    WEIGHT_TOP_SCORE,
    compute_retrieval_confidence,
    passes_retrieval_gate,
)
from app.services.confidence import RetrievalDetail as ConfidenceDetail
from app.services.config import ConfigurationError, PipelineConfig, read_pipeline_config
from app.services.generation import GenerationResult, generate_answer
from app.services.retrieval import RANK_ABSENT, RetrievalHit, RetrievalOutcome, retrieve

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

# Long enough to judge whether a source is the right one, short enough that the
# full chunk text stays in the document rather than in every answer payload.
EXCERPT_MAX_CHARS = 400

# The standardised "Weiss ich nicht" of ADR-008. One text per reason, so the
# user can tell "nothing found" from "found something too weak to trust" —
# these lead to different next steps.
MESSAGE_NO_MATCH = (
    "Dazu finde ich nichts in den freigegebenen Unterlagen. "
    "Bitte formuliere die Frage anders oder wende dich an eine Fachperson."
)
MESSAGE_WEAK_EVIDENCE = (
    "Die gefundenen Stellen sind zu schwach belegt für eine verlässliche Antwort. "
    "Die nächstliegenden Quellen sind unten aufgeführt."
)
MESSAGE_GENERATION_REFUSED = (
    "Die gefundenen Stellen decken deine Frage nicht ab. "
    "Die nächstliegenden Quellen sind unten aufgeführt."
)
# A truncated answer is withheld whole rather than shown up to the cut: its last
# claim may have lost the citation that was about to back it. The hint is a
# different one than above — here the sources fit, the question was too broad.
MESSAGE_GENERATION_TRUNCATED = (
    "Die Antwort wurde unvollständig abgebrochen und deshalb zurückgehalten. "
    "Bitte stelle eine engere Frage; die gefundenen Quellen sind unten aufgeführt."
)
MESSAGE_CONFIGURATION_ERROR = (
    "Die Suche ist derzeit nicht korrekt konfiguriert und liefert deshalb keine "
    "Antwort. Bitte wende dich an die Administration."
)

# These are the wire values of `suppression_reason`; the spec declares them as
# an enum and the frontend maps them to German labels, so adding one means
# touching openapi.yaml and MessageBubble.tsx in the same PR.
REASON_NO_MATCH = "retrieval_gate"
REASON_WEAK_EVIDENCE = "retrieval_confidence"
REASON_GENERATION_REFUSED = "generation_refused"
REASON_GENERATION_TRUNCATED = "generation_truncated"
REASON_CONFIGURATION_ERROR = "configuration_error"

# Stage identifiers are the contract of the admin debug view; T-19 and T-25
# append "citation_coverage" and "self_check" to this sequence.
STAGE_RETRIEVAL_GATE = "retrieval_gate"
STAGE_RETRIEVAL_CONFIDENCE = "retrieval_confidence"

# The admin view matches this exact string to place the call inside the pipeline
# (MessageBubble.tsx); T-25 adds "self_check" beside it.
STEP_GROUNDING = "grounding"


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    session_id: uuid.UUID | None = None


class Citation(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    excerpt: str
    index: int


class ConfidenceInfo(BaseModel):
    score: float
    retrieval_score: float
    citation_coverage: float


class ChunkDebugInfo(BaseModel):
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
    value: float | str | None
    threshold: float | None
    detail: str


class LLMCallInfo(BaseModel):
    step: str
    label: str
    prompt: str
    response: str


class RetrievalDetail(BaseModel):
    top_score: float
    mean_score: float
    evidence_density: float
    result: float
    count: int


class DebugInfo(BaseModel):
    chunks: list[ChunkDebugInfo]
    stages: list[StageInfo]
    llm_calls: list[LLMCallInfo]
    similarity_threshold: float
    min_retrieval_confidence: float
    min_citation_coverage: float
    self_check_ran: bool
    self_check_verdict: str | None = None
    retrieval_detail: RetrievalDetail
    params_used: dict[str, float | None]
    dense_above_threshold: int
    total_dense_retrieved: int
    sparse_count: int
    top_n_used: int
    formula_breakdown: str


class QueryResponse(BaseModel):
    session_id: uuid.UUID
    answer_id: uuid.UUID
    suppressed: bool
    suppression_reason: str | None
    message: str | None
    refinement_hint: str | None
    citations: list[Citation]
    confidence: ConfidenceInfo | None
    debug: DebugInfo | None


@router.post("", response_model=QueryResponse)
async def create_query(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    session = await _resolve_session(request.session_id, user, db)

    try:
        config = await read_pipeline_config(db)
    except ConfigurationError:
        # A broken threshold row is an operator error, and ADR-008 (Nachtrag
        # 2026-08-16) is explicit that the caller turns it into "Weiss ich
        # nicht" rather than a 500: an unusable threshold must never be
        # answered with a different, looser one. Read after the session exists
        # so this path can still return a well-formed QueryResponse.
        logger.exception("Pipeline-Konfiguration unbrauchbar für user_id=%s", user.id)
        return await _persist_and_respond(
            db=db,
            session=session,
            question=request.question,
            reason=REASON_CONFIGURATION_ERROR,
            message=MESSAGE_CONFIGURATION_ERROR,
            answer_text=None,
            suppressed=True,
            citations=[],
            # No thresholds means no scores were computed — reporting 0.0 would
            # claim a measurement that never happened.
            confidence=None,
            debug=None,
        )

    try:
        outcome = await retrieve(db, request.question, config, PILOT_AREA)
    except (TypeError, AttributeError, NameError, ImportError):
        # A bug must not masquerade as a provider outage: these signal broken
        # code, not a broken dependency, and belong in the logs and the CI as a
        # 500 rather than behind "bitte später erneut versuchen".
        raise
    except Exception:
        # The provider message is logged, never returned: LiteLLM errors carry
        # api_base, deployment names and, on an auth failure, a fragment of the
        # key. A retrieval outage is also not a "Weiss ich nicht" — dressing it
        # up as one would hide an outage behind a plausible product behaviour.
        logger.exception("Retrieval fehlgeschlagen für user_id=%s", user.id)
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retrieval ist derzeit nicht verfügbar. Bitte später erneut versuchen.",
        )

    context_scores = [hit.score for hit in outcome.context]
    gate_passed = passes_retrieval_gate(context_scores, config.similarity_threshold)
    detail = compute_retrieval_confidence(
        context_scores, config.similarity_threshold, config.context_top_n
    )
    confidence_passed = gate_passed and detail.result >= config.min_retrieval_confidence

    # The one place an LLM is reached, and only from the third branch: the two
    # gates above are the deterministic, free part of the defence, and ADR-007
    # requires them to decide *before* a provider is called, not after.
    generation: GenerationResult | None = None
    reason: str | None
    message: str

    if not gate_passed:
        reason, message = REASON_NO_MATCH, MESSAGE_NO_MATCH
    elif not confidence_passed:
        reason, message = REASON_WEAK_EVIDENCE, MESSAGE_WEAK_EVIDENCE
    else:
        generation = await _generate(request.question, outcome.context, user)
        if generation.truncated:
            reason, message = REASON_GENERATION_TRUNCATED, MESSAGE_GENERATION_TRUNCATED
        elif generation.answer is None:
            # The model itself reported the context does not cover the question.
            # Its wording is dropped for the standardised text (ADR-008): a
            # refusal is a suppression, not a short answer.
            reason, message = REASON_GENERATION_REFUSED, MESSAGE_GENERATION_REFUSED
        else:
            reason, message = None, generation.answer

    # Nothing above the threshold means nothing worth pointing at — showing the
    # closest misses would invite reading them as an answer (ADR-008: no
    # generated content below the gate). The weak-evidence case keeps them:
    # there the sources are real, only the footing is thin.
    citations = [] if not gate_passed else _to_citations(outcome.context)

    # citation_coverage is 0.0, not null: the spec requires the field and stage
    # 2 has not run, so nothing about this answer is covered by a citation yet.
    # `score` is the retrieval score alone until T-23 combines the two — no
    # composite weight is invented here, there is no config key for one.
    confidence = ConfidenceInfo(
        score=detail.result, retrieval_score=detail.result, citation_coverage=0.0
    )

    return await _persist_and_respond(
        db=db,
        session=session,
        question=request.question,
        reason=reason,
        message=message,
        answer_text=generation.answer if generation else None,
        # A suppressed answer always names the stage that suppressed it, so the
        # two fields cannot drift apart into "suppressed without a reason".
        suppressed=reason is not None,
        citations=citations,
        confidence=confidence,
        # Only admins see the pipeline internals: chunk contents and the rendered
        # prompt would otherwise leak the full source text past the excerpt the
        # citation shows.
        debug=_to_debug(outcome, detail, config, gate_passed, confidence_passed, generation)
        if user.role == "admin"
        else None,
    )


async def _generate(
    question: str, context: list[RetrievalHit], user: User
) -> GenerationResult:
    """Call the provider, turning an outage into a 503 rather than a non-answer."""
    try:
        return await generate_answer(question, context)
    except (TypeError, AttributeError, NameError, ImportError):
        # Same split as the retrieval call above: broken code is a 500, a broken
        # dependency is a 503.
        raise
    except Exception:
        # The provider message is logged, never returned — it carries api_base,
        # deployment names and, on an auth failure, a fragment of the key.
        logger.exception("Antwortgenerierung fehlgeschlagen für user_id=%s", user.id)
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Die Antwortgenerierung ist derzeit nicht verfügbar. "
            "Bitte später erneut versuchen.",
        )


async def _persist_and_respond(
    *,
    db: AsyncSession,
    session: QuerySession,
    question: str,
    reason: str | None,
    message: str,
    answer_text: str | None,
    suppressed: bool,
    citations: list[Citation],
    confidence: ConfidenceInfo | None,
    debug: DebugInfo | None,
) -> QueryResponse:
    """Write the answer row and build the response around its id.

    Every exit of this endpoint goes through here, including the configuration
    error: `answer_id` is a required field and the target of the feedback
    foreign key, so a response without a persisted row would hand the client an
    id that POST /answers/{id}/feedback rejects.

    `answer_text` is the generated text and stays None for every suppressed
    answer: the column is what a later evaluation reads, and storing the
    standardised "Weiss ich nicht" there would make suppressions look like
    answers the pipeline produced.
    """
    answer = Answer(
        id=uuid.uuid4(),
        session_id=session.id,
        question=question,
        answer_text=answer_text,
        confidence_score=confidence.score if confidence else None,
        citation_coverage=None,
        retrieval_confidence=confidence.retrieval_score if confidence else None,
        suppressed=suppressed,
    )
    db.add(answer)
    await db.commit()

    return QueryResponse(
        session_id=session.id,
        answer_id=answer.id,
        suppressed=suppressed,
        suppression_reason=reason,
        message=message,
        # TODO (T-26): Requirements §71 asks for a refinement hint after a
        # "Weiss ich nicht". The field is in the contract for it; T-17 makes
        # this path live but does not yet produce the hint.
        refinement_hint=None,
        citations=citations,
        confidence=confidence,
        debug=debug,
    )


async def _resolve_session(
    session_id: uuid.UUID | None, user: User, db: AsyncSession
) -> QuerySession:
    """Continue the given session, or start a new one.

    An unknown or foreign session_id starts a new session rather than failing:
    the contract declares no 404 for it, and answering a question is more useful
    than rejecting it over a stale client-side id. Foreign ids are not honoured
    — a session is the thread of one user's questions.
    """
    if session_id is not None:
        existing = await db.get(QuerySession, session_id)
        if existing is not None and existing.user_id == user.id:
            return existing

    session = QuerySession(id=uuid.uuid4(), user_id=user.id)
    db.add(session)
    # Flushed here so the answer below can reference it; the commit that makes
    # both rows durable happens once, after the answer is added.
    await db.flush()
    return session


def _to_citations(hits: list[RetrievalHit]) -> list[Citation]:
    return [
        Citation(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            filename=hit.filename,
            page=hit.page,
            excerpt=_excerpt(hit.content),
            # 1-based: `index` is the footnote number the answer text cites as
            # [1], [2], … — build_prompt() numbers the same list the same way.
            index=position,
        )
        for position, hit in enumerate(hits, start=1)
    ]


def _excerpt(content: str) -> str:
    collapsed = " ".join(content.split())
    if len(collapsed) <= EXCERPT_MAX_CHARS:
        return collapsed
    return collapsed[:EXCERPT_MAX_CHARS].rstrip() + "…"


def _to_debug(
    outcome: RetrievalOutcome,
    detail: ConfidenceDetail,
    config: PipelineConfig,
    gate_passed: bool,
    confidence_passed: bool,
    generation: GenerationResult | None,
) -> DebugInfo:
    context_ids = {hit.chunk_id for hit in outcome.context}
    threshold = config.similarity_threshold
    above_threshold = [hit for hit in outcome.candidates if hit.score >= threshold]
    # The gate decides on the context, so the stage text has to count the same
    # set — otherwise the admin view shows "3 von 22 erreichen die Schwelle"
    # right next to passed: false, and the thresholds get calibrated against a
    # number that never entered the decision.
    context_above_threshold = [hit for hit in outcome.context if hit.score >= threshold]
    # Counted over the dense results only, to stay comparable with
    # total_dense_retrieved next to it: the pair answers "how much of what the
    # vector search returned was actually close enough".
    dense_above_threshold = [hit for hit in above_threshold if hit.dense_rank != RANK_ABSENT]

    return DebugInfo(
        chunks=[
            ChunkDebugInfo(
                filename=hit.filename,
                page=hit.page,
                heading=hit.heading,
                score=round(hit.score, 4),
                above_threshold=hit.score >= config.similarity_threshold,
                in_top_n=hit.chunk_id in context_ids,
                dense_rank=hit.dense_rank,
                content=hit.content,
            )
            for hit in outcome.candidates
        ],
        stages=[
            StageInfo(
                id=STAGE_RETRIEVAL_GATE,
                name="Retrieval-Gate (ADR-007)",
                ran=True,
                passed=gate_passed,
                value=detail.top_score,
                threshold=config.similarity_threshold,
                detail=(
                    f"{len(context_above_threshold)} von {len(outcome.context)} Kontext-Chunks "
                    f"erreichen die Similarity-Schwelle "
                    f"({len(above_threshold)} von {len(outcome.candidates)} Kandidaten insgesamt)"
                ),
            ),
            StageInfo(
                id=STAGE_RETRIEVAL_CONFIDENCE,
                name="Retrieval-Konfidenz (ADR-008, Stufe 1)",
                # Skipped when the gate already suppressed — the whole point of
                # the gate is that nothing downstream runs.
                ran=gate_passed,
                passed=confidence_passed,
                value=detail.result,
                threshold=config.min_retrieval_confidence,
                detail=(
                    "Nicht ausgeführt, Retrieval-Gate hat unterdrückt"
                    if not gate_passed
                    else f"Score {detail.result} gegen Schwelle {config.min_retrieval_confidence}"
                ),
            ),
        ],
        # Empty by construction below either gate, not by omission: that the
        # list is empty is what makes "kein LLM-Aufruf" (ADR-007) visible in the
        # admin view instead of merely asserted in a test.
        llm_calls=[]
        if generation is None
        else [
            LLMCallInfo(
                step=STEP_GROUNDING,
                label="Antwortgenerierung (Grounding-Prompt, ADR-007)",
                prompt=generation.prompt,
                response=generation.raw_response,
            )
        ],
        similarity_threshold=config.similarity_threshold,
        min_retrieval_confidence=config.min_retrieval_confidence,
        min_citation_coverage=config.min_citation_coverage,
        self_check_ran=False,
        self_check_verdict=None,
        retrieval_detail=RetrievalDetail(
            top_score=detail.top_score,
            mean_score=detail.mean_score,
            evidence_density=detail.evidence_density,
            result=detail.result,
            count=detail.count,
        ),
        params_used={
            "similarity_threshold": config.similarity_threshold,
            "min_retrieval_confidence": config.min_retrieval_confidence,
            "retrieval_top_k": config.retrieval_top_k,
            "context_top_n": config.context_top_n,
            "rrf_k": config.rrf_k,
        },
        dense_above_threshold=len(dense_above_threshold),
        total_dense_retrieved=outcome.dense_count,
        sparse_count=outcome.sparse_count,
        top_n_used=len(outcome.context),
        # Built from the weight constants, not from literals: a recalibration
        # that changes the weights must not leave the admin view explaining the
        # score with the old formula.
        formula_breakdown=(
            f"{WEIGHT_TOP_SCORE}*{detail.top_score} + {WEIGHT_MEAN_SCORE}*{detail.mean_score} "
            f"+ {WEIGHT_EVIDENCE_DENSITY}*{detail.evidence_density} = {detail.result}"
        ),
    )
