"""POST /query — hybrid retrieval and the full confidence pipeline (T-17…T-26).

The order is the point, and ADR-008 fixes it: the question is embedded, both
searches run, the candidates are fused, and stages 0 and 1 decide whether the
found sources are solid enough to spend an LLM call on. Only then is an answer
generated, and only from those chunks — a question that fails either gate never
reaches the provider at all (ADR-007). Stage 2 reads the generated text back and
checks that it cites the chunks it was given. The composite of stages 1 and 2 is
the confidence the user sees; below the `Mittel` band it suppresses. Only what
survives all of that, and only in the narrow band where the score is close to
the threshold, pays for the second LLM call of stage 3.

Every stage can suppress, and each one has its own reason and its own
standardised text, because the next step differs: a question that is too broad
is the user's to sharpen, an invented reference is not. Nothing below a
suppression is generated prose — that is the whole promise of the pipeline.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.limiter import account_key, limiter
from app.models.tables import Answer, QuerySession, User
from app.routers.documents import PILOT_AREA
from app.services.confidence import (
    BAND_LOW,
    WEIGHT_CITATION_COVERAGE,
    WEIGHT_EVIDENCE_DENSITY,
    WEIGHT_MEAN_SCORE,
    WEIGHT_RETRIEVAL_CONFIDENCE,
    WEIGHT_TOP_SCORE,
    Band,
    CitationDetail,
    CompositeDetail,
    band_for,
    check_citations,
    compute_composite,
    compute_retrieval_confidence,
    in_self_check_band,
    passes_retrieval_gate,
)
from app.services.confidence import RetrievalDetail as ConfidenceDetail
from app.services.config import (
    ConfidenceThresholds,
    ConfigurationError,
    PipelineConfig,
    read_query_config,
)
from app.services.generation import GenerationResult, generate_answer
from app.services.retrieval import RANK_ABSENT, RetrievalHit, RetrievalOutcome, retrieve
from app.services.self_check import (
    VERDICT_COVERED,
    VERDICT_UNCOVERED,
    SelfCheckResult,
    run_self_check,
)

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
# Stage 2. Two texts, because the two cases send the user somewhere different:
# thin coverage is a question that can be sharpened, an invented reference is a
# fault the user cannot do anything about and that an admin has to see.
MESSAGE_CITATION_COVERAGE = (
    "Die erzeugte Antwort war nicht ausreichend durch die gefundenen Stellen belegt "
    "und wird deshalb zurückgehalten. Die Quellen sind unten aufgeführt."
)
MESSAGE_CITATION_INVALID = (
    "Die erzeugte Antwort hat sich auf eine Quelle berufen, die es nicht gibt, "
    "und wird deshalb zurückgehalten. Die gefundenen Quellen sind unten aufgeführt."
)
# The composite band. Every single stage passed here — the sources were close
# enough, the answer cited them — and the combined confidence still lands below
# the lowest band, which is what "defense in depth" is supposed to catch.
MESSAGE_CONFIDENCE_BAND = (
    "Die Antwort war insgesamt zu wenig belastbar und wird deshalb "
    "zurückgehalten. Die gefundenen Quellen sind unten aufgeführt."
)
# Stage 3. Deliberately does not repeat what the verification found: the
# uncovered statements are quotes from an answer that was withheld, and printing
# them would deliver the content through the suppression notice.
MESSAGE_SELF_CHECK = (
    "Die Prüfung der Antwort hat Aussagen gefunden, die die Quellen nicht "
    "hergeben; die Antwort wird deshalb zurückgehalten. "
    "Die gefundenen Quellen sind unten aufgeführt."
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
REASON_CITATION_COVERAGE = "citation_coverage"
REASON_CITATION_INVALID = "citation_invalid"
REASON_CONFIDENCE_BAND = "confidence_band"
REASON_SELF_CHECK = "self_check"
REASON_CONFIGURATION_ERROR = "configuration_error"

# Requirements §71: a "Weiss ich nicht" owes the user a next step. One text per
# reason rather than one for all of them — the useful move after "the question
# was too broad" is not the useful move after "the model invented a source", and
# a hint that fits every case tells nobody anything.
#
# Static, not generated: the hint follows from the reason alone, and asking a
# provider for it would put an LLM call on the one path that exists because the
# pipeline decided not to trust one. `configuration_error` has no entry — there
# is nothing the user can rephrase, and its message already sends them to the
# administration.
REFINEMENT_HINTS = {
    REASON_NO_MATCH: (
        "Nenne einen konkreten Prozess, ein Dokument oder einen Artikel — "
        "etwa «Welche Pflichten gelten nach Art. 6 für Hochrisiko-Systeme?»"
    ),
    REASON_WEAK_EVIDENCE: (
        "Die Unterlagen streifen das Thema nur. Verwende die Begriffe aus den "
        "unten aufgeführten Quellen, dann findet die Suche die passende Stelle."
    ),
    REASON_GENERATION_REFUSED: (
        "Frage nach einem einzelnen Aspekt statt nach dem ganzen Thema, oder "
        "prüfe an den Quellen unten, ob die Unterlagen die Frage überhaupt abdecken."
    ),
    REASON_GENERATION_TRUNCATED: (
        "Die Frage war zu breit für eine Antwort. Teile sie in Einzelfragen auf "
        "und stelle sie nacheinander."
    ),
    REASON_CITATION_COVERAGE: (
        "Grenze die Frage auf einen Punkt ein — je enger die Frage, desto eher "
        "lässt sich die Antwort vollständig belegen."
    ),
    REASON_CITATION_INVALID: (
        "Das lag an der Antwort, nicht an deiner Frage. Stelle sie noch einmal; "
        "wiederholt sich das, melde die Frage der Administration."
    ),
    REASON_CONFIDENCE_BAND: (
        "Die Belege reichten in der Summe nicht. Nenne das Dokument oder den "
        "Abschnitt, auf den du zielst, dann steht die Antwort auf festerem Grund."
    ),
    REASON_SELF_CHECK: (
        "Die Unterlagen decken die Frage nur teilweise. Frage nach dem Teil, den "
        "die unten aufgeführten Quellen behandeln."
    ),
}

# Stage identifiers are the contract of the admin debug view: MessageBubble.tsx
# matches them by name to place the LLM calls and the composite breakdown inside
# the pipeline, so the values are not free.
STAGE_RETRIEVAL_GATE = "retrieval_gate"
STAGE_RETRIEVAL_CONFIDENCE = "retrieval_confidence"
STAGE_CITATION_COVERAGE = "citation_coverage"
STAGE_CONFIDENCE_BAND = "confidence_band"
STAGE_SELF_CHECK = "self_check"

# The admin view matches these exact strings to place each call inside the
# pipeline (MessageBubble.tsx).
STEP_GROUNDING = "grounding"
STEP_SELF_CHECK = "self_check"

# Every question costs an embedding call and, past both gates, one or two LLM
# calls (ADR-004, ADR-005) — this is the only endpoint that spends provider
# money. Ten a minute is out of reach for someone typing questions at the p95 of
# 10 s the NFA sets (T-22), and stops a loop long before it becomes a bill.
# Counted per account, not per address: see `account_key` and
# Docs/03_QualityAttributes.md, Security.
QUERY_RATE_LIMIT = "10/minute"


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    session_id: uuid.UUID | None = None


class Citation(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    heading: str | None
    excerpt: str
    index: int


class ConfidenceInfo(BaseModel):
    score: float
    retrieval_score: float
    citation_coverage: float
    band: Band


class ChunkDebugInfo(BaseModel):
    """One fused candidate, exactly as `fuse()` left it.

    Every field is copied from the `RetrievalHit`; nothing here is recomputed.
    `dense_rank`/`sparse_rank`/`rrf_score` travel together because they are the
    three values that produce the order of this list — showing the order without
    them made a correctly ranked sparse hit look like a bug (T-54).

    `chunk_id` and `document_id` cost nothing to carry and are what a view needs
    to link a row to something else: `chunk_id` is the same value as
    `Citation.chunk_id`, `document_id` is what the document viewer (T-21) opens.
    """

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    heading: str | None
    score: float
    above_threshold: bool
    in_top_n: bool
    dense_rank: int
    sparse_rank: int
    rrf_score: float
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
@limiter.limit(QUERY_RATE_LIMIT, key_func=account_key)
async def create_query(
    # slowapi reads its key off the raw request and insists the argument be
    # named `request`, so the body is `body` — the name auth.py already uses.
    request: Request,
    body: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    session = await _resolve_session(body.session_id, user, db)

    try:
        # One round-trip for both halves: the band limits decide suppression too
        # (T-23), so an unusable one is no more answerable than an unusable
        # threshold — same table, same handler, no reason to ask twice.
        query_config = await read_query_config(db)
        config, thresholds = query_config.pipeline, query_config.thresholds
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
            question=body.question,
            reason=REASON_CONFIGURATION_ERROR,
            message=MESSAGE_CONFIGURATION_ERROR,
            answer_text=None,
            suppressed=True,
            citations=[],
            # No thresholds means no scores were computed — reporting 0.0 would
            # claim a measurement that never happened.
            confidence=None,
            citation=None,
            self_check=None,
            debug=None,
        )

    try:
        outcome = await retrieve(db, body.question, config, PILOT_AREA)
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
    # None means stage 2 did not run — which is not the same as "ran and found
    # nothing". Only a text that was actually generated has segments that could
    # be covered, so the distinction is kept all the way into the answers row.
    citation: CitationDetail | None = None
    citation_passed = False
    # None means stage 3 was skipped, which is the normal case — it only runs
    # for a score inside the trigger band, and that is what keeps the second
    # provider call off the common path (ADR-008).
    self_check: SelfCheckResult | None = None
    reason: str | None
    message: str

    if not gate_passed:
        reason, message = REASON_NO_MATCH, MESSAGE_NO_MATCH
    elif not confidence_passed:
        reason, message = REASON_WEAK_EVIDENCE, MESSAGE_WEAK_EVIDENCE
    else:
        generation = await _generate(body.question, outcome.context, user)
        if generation.truncated:
            reason, message = REASON_GENERATION_TRUNCATED, MESSAGE_GENERATION_TRUNCATED
        elif generation.answer is None:
            # The model itself reported the context does not cover the question.
            # Its wording is dropped for the standardised text (ADR-008): a
            # refusal is a suppression, not a short answer.
            reason, message = REASON_GENERATION_REFUSED, MESSAGE_GENERATION_REFUSED
        else:
            # Stage 2 (ADR-008). The validity check comes first and stands apart
            # from the threshold: a reference to a chunk that was never handed to
            # the model is a fabricated source, and no coverage figure — not even
            # a perfect one — makes that deliverable.
            citation = check_citations(generation.answer, len(outcome.context))
            # One evaluation, reused by the debug view below — the same shape as
            # `gate_passed` and `confidence_passed` above. Recomputing it there
            # would let the admin panel and the actual decision drift apart on
            # the next change to the threshold semantics.
            #
            # `>=`, so that a coverage exactly on the threshold still passes —
            # the same reading of the configured value as stages 0 and 1.
            citation_passed = (
                citation.valid and citation.coverage >= config.min_citation_coverage
            )
            if not citation.valid:
                reason, message = REASON_CITATION_INVALID, MESSAGE_CITATION_INVALID
            elif not citation_passed:
                reason, message = REASON_CITATION_COVERAGE, MESSAGE_CITATION_COVERAGE
            else:
                reason, message = None, generation.answer

    # The composite (T-23), computed once for every exit of the pipeline — a
    # suppressed answer is shown its confidence too, and `None` for the coverage
    # is what keeps a stage that never ran out of the score.
    composite = compute_composite(detail.result, citation.coverage if citation else None)
    band = band_for(composite.result, thresholds.medium, thresholds.high)

    # Stages 2b and 3 judge an answer, so they only apply where there is one.
    # `reason is None` at this point means every stage so far passed; the two
    # further conditions are what mypy needs to see the same thing.
    if reason is None and generation is not None and generation.answer is not None:
        if band == BAND_LOW:
            # Every individual stage passed and the combination still does not
            # carry. This is the case defense-in-depth exists for: two signals
            # that are each just barely acceptable do not add up to a reliable
            # answer (ADR-008).
            reason, message = REASON_CONFIDENCE_BAND, MESSAGE_CONFIDENCE_BAND
        elif in_self_check_band(
            composite.result, config.self_check_band_low, config.self_check_band_high
        ):
            # Stage 3, and the only branch that spends a second LLM call. Above
            # the band the footing is clear enough that the call buys nothing;
            # below it the answer is already suppressed.
            self_check = await _self_check(
                body.question, generation.answer, outcome.context, user
            )
            if not self_check.passed:
                reason, message = REASON_SELF_CHECK, MESSAGE_SELF_CHECK

    # Nothing above the threshold means nothing worth pointing at — showing the
    # closest misses would invite reading them as an answer (ADR-008: no
    # generated content below the gate). The weak-evidence case keeps them:
    # there the sources are real, only the footing is thin.
    citations = [] if not gate_passed else _to_citations(outcome.context)

    # 0.0 where stage 2 never ran: the spec requires the field and declares it
    # non-nullable, so "not measured" and "measured as zero" share a value here.
    # Which of the two it was is readable in debug.stages, and the answers row
    # keeps them apart properly (NULL vs 0.0).
    confidence = ConfidenceInfo(
        score=composite.result,
        retrieval_score=detail.result,
        citation_coverage=citation.coverage if citation else 0.0,
        band=band,
    )

    return await _persist_and_respond(
        db=db,
        session=session,
        question=body.question,
        reason=reason,
        message=message,
        # Suppressed at stage 2 or later means there *is* generated text — and it
        # still must not be stored: the column is what a later evaluation reads
        # as "the answer the pipeline produced", and a withheld answer was not
        # produced. Hence `reason is None`, not just `generation`.
        answer_text=generation.answer if generation and reason is None else None,
        # A suppressed answer always names the stage that suppressed it, so the
        # two fields cannot drift apart into "suppressed without a reason".
        suppressed=reason is not None,
        citations=citations,
        confidence=confidence,
        citation=citation,
        self_check=self_check,
        # Only admins see the pipeline internals: chunk contents and the rendered
        # prompt would otherwise leak the full source text past the excerpt the
        # citation shows.
        debug=_to_debug(
            outcome=outcome,
            detail=detail,
            config=config,
            thresholds=thresholds,
            gate_passed=gate_passed,
            confidence_passed=confidence_passed,
            generation=generation,
            citation=citation,
            citation_passed=citation_passed,
            composite=composite,
            band=band,
            self_check=self_check,
        )
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


async def _self_check(
    question: str, answer: str, context: list[RetrievalHit], user: User
) -> SelfCheckResult:
    """Stage 3, with the same outage handling as the generation above.

    An unreachable provider is a 503, not a suppression — even though this stage
    suppresses on every other kind of failure. The difference is what the two
    say: "the verification found unsupported claims" is a statement about the
    answer, "the provider did not respond" is a statement about the system, and
    ADR-008 keeps an outage from hiding behind a product behaviour. An unreadable
    *verdict* is the first kind and handled inside run_self_check().
    """
    try:
        return await run_self_check(question, answer, context)
    except (TypeError, AttributeError, NameError, ImportError):
        raise
    except Exception:
        # Logged, never returned — LiteLLM errors carry api_base, deployment
        # names and, on an auth failure, a fragment of the key.
        logger.exception("Self-Check fehlgeschlagen für user_id=%s", user.id)
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Die Prüfung der Antwort ist derzeit nicht verfügbar. "
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
    citation: CitationDetail | None,
    self_check: SelfCheckResult | None,
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
        # NULL where stage 2 did not run, unlike the response field above: a
        # stored 0.0 would read as "measured, nothing covered" and quietly
        # pollute the calibration this column exists for (ADR-009).
        citation_coverage=citation.coverage if citation else None,
        retrieval_confidence=confidence.retrieval_score if confidence else None,
        # NULL for the same reason as the coverage above: stage 3 runs only
        # inside the trigger band, so "did not run" is the common case and must
        # not be stored as "ran and failed" (ADR-009 reads this column).
        self_check_passed=self_check.passed if self_check else None,
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
        # Requirements §71: the hint belongs to the suppression, so it is looked
        # up from the reason rather than passed in — a new reason without a hint
        # then shows up as a missing hint, not as a wrong one. None on a
        # delivered answer: there is nothing to refine.
        refinement_hint=REFINEMENT_HINTS.get(reason) if reason else None,
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
            heading=hit.heading,
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


def _citation_detail_text(citation: CitationDetail | None, context_size: int) -> str:
    """The stage-2 line of the admin view, in the terms an operator calibrates in."""
    if citation is None:
        return "Nicht ausgeführt, es wurde keine Antwort erzeugt"
    if not citation.valid:
        return (
            f"Erfundene Referenz {_as_footnotes(citation.fabricated)} bei "
            f"{context_size} Kontext-Chunks — unterdrückt unabhängig von der Coverage"
        )
    if citation.segments == 0:
        return "Kein wertbares Antwort-Segment gefunden"
    return (
        f"{citation.covered} von {citation.segments} Segmenten belegt; "
        f"verwendete Referenzen {_as_footnotes(citation.referenced) or '—'}"
    )


def _as_footnotes(indices: tuple[int, ...]) -> str:
    return "".join(f"[{index}]" for index in indices)


def _band_detail_text(
    composite: CompositeDetail, band: Band, thresholds: ConfidenceThresholds, ran: bool
) -> str:
    """The stage-2b line: where the composite came from and which band it hit."""
    if not ran:
        return "Nicht ausgeführt, eine frühere Stufe hat unterdrückt"
    return (
        f"Band «{band}» bei Score {composite.result} "
        f"(Mittel ab {thresholds.medium}, Hoch ab {thresholds.high})"
    )


def _self_check_detail_text(
    self_check: SelfCheckResult | None,
    composite: CompositeDetail,
    config: PipelineConfig,
    reached: bool,
) -> str:
    """The stage-3 line, including *why* the stage was skipped.

    That the stage did not run is the normal case and the admin needs to see the
    reason: a band that never triggers is a misconfiguration that would otherwise
    look exactly like a pipeline working as intended.

    `reached` is what keeps that honest. Without it every skip reads as "outside
    the trigger band", including the skips where the pipeline never got this far
    — and a score that *is* inside the band would then be printed next to the
    claim that it is not.
    """
    if self_check is None and not reached:
        return "Nicht ausgeführt, eine frühere Stufe hat unterdrückt"
    if self_check is None:
        return (
            f"Nicht ausgeführt, Score {composite.result} liegt ausserhalb des Grenzbands "
            f"{config.self_check_band_low}–{config.self_check_band_high}"
        )
    if not self_check.verdict_parsed:
        return (
            "Kein lesbares Urteil erhalten — unterdrückt, weil eine Prüfung, "
            "die sich nicht auswerten lässt, nicht stattgefunden hat"
        )
    if self_check.passed:
        return "Alle Aussagen durch den Kontext gedeckt"
    return f"Nicht gedeckt: {self_check.uncovered or '(ohne Angabe)'}"


def _self_check_value(self_check: SelfCheckResult | None) -> str | None:
    if self_check is None:
        return None
    if not self_check.verdict_parsed:
        return "unlesbar"
    return VERDICT_COVERED if self_check.passed else VERDICT_UNCOVERED


def _to_debug(
    *,
    outcome: RetrievalOutcome,
    detail: ConfidenceDetail,
    config: PipelineConfig,
    thresholds: ConfidenceThresholds,
    gate_passed: bool,
    confidence_passed: bool,
    generation: GenerationResult | None,
    citation: CitationDetail | None,
    citation_passed: bool,
    composite: CompositeDetail,
    band: Band,
    self_check: SelfCheckResult | None,
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

    # Whether the pipeline got as far as stage 3's decision point — which is not
    # the same as stage 3 having run. It is the difference between "skipped
    # because the score was clear" and "skipped because there was nothing left
    # to check", and the admin view has to name the right one.
    band_passed = citation_passed and band != BAND_LOW

    return DebugInfo(
        chunks=[
            ChunkDebugInfo(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                filename=hit.filename,
                page=hit.page,
                heading=hit.heading,
                score=round(hit.score, 4),
                above_threshold=hit.score >= config.similarity_threshold,
                in_top_n=hit.chunk_id in context_ids,
                dense_rank=hit.dense_rank,
                sparse_rank=hit.sparse_rank,
                # Six digits, not the four `score` gets: the gap between
                # consecutive RRF values is ~1/(rrf_k + rank)², which at the
                # default top_k of 20 is still visible at four digits but falls
                # below it around rank 40. `retrieval_top_k` goes to 100 in the
                # admin panel, so four digits would silently collapse the tail
                # of a widened candidate list onto one value — and telling the
                # ranks apart is the whole point of showing the score (T-54).
                rrf_score=round(hit.rrf_score, 6),
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
            StageInfo(
                id=STAGE_CITATION_COVERAGE,
                name="Citation-Coverage (ADR-008, Stufe 2)",
                # Runs on generated text only — the stage is skipped whenever an
                # earlier one suppressed, and also after a refusal or a
                # truncation, where there is no answer to measure.
                ran=citation is not None,
                # Taken from the handler, not recomputed — see the note there.
                passed=citation_passed,
                value=citation.coverage if citation else None,
                threshold=config.min_citation_coverage,
                detail=_citation_detail_text(citation, len(outcome.context)),
            ),
            StageInfo(
                id=STAGE_CONFIDENCE_BAND,
                name="Komposit-Konfidenz (ADR-008, US-02)",
                ran=citation_passed,
                passed=band_passed,
                value=composite.result,
                # The lower band limit is the one that suppresses; `high` only
                # separates two bands that are both delivered.
                threshold=thresholds.medium,
                detail=_band_detail_text(composite, band, thresholds, citation_passed),
            ),
            StageInfo(
                id=STAGE_SELF_CHECK,
                name="Self-Check (ADR-008, Stufe 3)",
                ran=self_check is not None,
                passed=self_check is not None and self_check.passed,
                value=_self_check_value(self_check),
                # No threshold: the verdict is a judgement, not a measurement
                # compared against a number (ADR-008 rejects the LLM's own score).
                threshold=None,
                detail=_self_check_detail_text(self_check, composite, config, band_passed),
            ),
        ],
        # Empty by construction below either gate, not by omission: that the
        # list is empty is what makes "kein LLM-Aufruf" (ADR-007) visible in the
        # admin view instead of merely asserted in a test. That it holds one
        # entry rather than two is the same evidence for stage 3 being the
        # exception ADR-008 says it is.
        llm_calls=_llm_calls(generation, self_check),
        similarity_threshold=config.similarity_threshold,
        min_retrieval_confidence=config.min_retrieval_confidence,
        min_citation_coverage=config.min_citation_coverage,
        self_check_ran=self_check is not None,
        # The model's wording, not the parsed decision: what the stage decided is
        # in the `self_check` entry of `stages`, and an admin looking at a
        # suppression needs to see what it actually answered.
        self_check_verdict=self_check.raw_response if self_check else None,
        retrieval_detail=RetrievalDetail(
            top_score=detail.top_score,
            mean_score=detail.mean_score,
            evidence_density=detail.evidence_density,
            result=detail.result,
            count=detail.count,
        ),
        # Every threshold this request was decided against, including those of
        # stages that did not run: an operator calibrating the pipeline needs the
        # whole set, and the frontend used to invent the missing ones.
        params_used={
            "similarity_threshold": config.similarity_threshold,
            "min_retrieval_confidence": config.min_retrieval_confidence,
            "min_citation_coverage": config.min_citation_coverage,
            "confidence_threshold_medium": thresholds.medium,
            "confidence_threshold_high": thresholds.high,
            "self_check_band_low": config.self_check_band_low,
            "self_check_band_high": config.self_check_band_high,
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
        # score with the old formula. Both levels, because the composite hides
        # the retrieval breakdown that produced half of it.
        formula_breakdown=_formula_breakdown(detail, composite),
    )


def _llm_calls(
    generation: GenerationResult | None, self_check: SelfCheckResult | None
) -> list[LLMCallInfo]:
    calls = []
    if generation is not None:
        calls.append(
            LLMCallInfo(
                step=STEP_GROUNDING,
                label="Antwortgenerierung (Grounding-Prompt, ADR-007)",
                prompt=generation.prompt,
                response=generation.raw_response,
            )
        )
    if self_check is not None:
        calls.append(
            LLMCallInfo(
                step=STEP_SELF_CHECK,
                label="Self-Check (Verifikations-Prompt, ADR-008 Stufe 3)",
                prompt=self_check.prompt,
                response=self_check.raw_response,
            )
        )
    return calls


def _formula_breakdown(detail: ConfidenceDetail, composite: CompositeDetail) -> str:
    retrieval = (
        f"Retrieval {WEIGHT_TOP_SCORE}*{detail.top_score} "
        f"+ {WEIGHT_MEAN_SCORE}*{detail.mean_score} "
        f"+ {WEIGHT_EVIDENCE_DENSITY}*{detail.evidence_density} = {detail.result}"
    )
    if composite.citation_coverage is None:
        # Stage 2 never ran, so there is no second term to show. Saying so beats
        # printing a weighted sum whose other half was never measured.
        return f"{retrieval} · Komposit = {composite.result} (Stufe 2 nicht gelaufen)"
    return (
        f"{retrieval} · Komposit {WEIGHT_RETRIEVAL_CONFIDENCE}*{detail.result} "
        f"+ {WEIGHT_CITATION_COVERAGE}*{composite.citation_coverage} = {composite.result}"
    )
