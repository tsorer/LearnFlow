"""POST /query — the contract T-17…T-19 owe the frontend (US-01, ADR-008)."""

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import User
from app.routers.query import (
    REASON_CITATION_COVERAGE,
    REASON_CITATION_INVALID,
    REASON_CONFIGURATION_ERROR,
    REASON_GENERATION_REFUSED,
    REASON_GENERATION_TRUNCATED,
    REASON_NO_MATCH,
    REASON_WEAK_EVIDENCE,
    STEP_GROUNDING,
)
from app.services.config import ConfigurationError, PipelineConfig
from app.services.generation import GenerationResult, build_prompt
from app.services.retrieval import RetrievalHit, RetrievalOutcome

ANSWER = "Der AI Act regelt Hochrisiko-Systeme [1]."

CONFIG = PipelineConfig(
    similarity_threshold=0.35,
    min_retrieval_confidence=0.40,
    min_citation_coverage=0.50,
    retrieval_top_k=20,
    context_top_n=5,
    rrf_k=60,
)


def make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()  # AsyncSession.add() is synchronous on the real session
    return db


def make_user(role: str = "learner") -> User:
    return User(
        id=uuid.uuid4(),
        email="lara@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def make_hit(score: float, dense_rank: int = 1, filename: str = "skos.pdf") -> RetrievalHit:
    return RetrievalHit(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename=filename,
        content="  Ein   Chunk\nmit Inhalt.  ",
        page=7,
        heading="Kapitel 1",
        score=score,
        dense_rank=dense_rank,
        sparse_rank=0,
        rrf_score=1 / (60 + dense_rank),
    )


def make_outcome(*scores: float) -> RetrievalOutcome:
    hits = [make_hit(score, dense_rank=rank) for rank, score in enumerate(scores, start=1)]
    return RetrievalOutcome(
        candidates=hits, context=hits, dense_count=len(hits), sparse_count=0
    )


def make_generate(answer: str | None = ANSWER, truncated: bool = False) -> AsyncMock:
    """A stand-in for the generation step; `answer=None` is the model refusing."""
    return AsyncMock(
        return_value=GenerationResult(
            answer=answer,
            truncated=truncated,
            prompt="SYSTEM … Kontext … Frage …",
            raw_response=answer or "WEISS_NICHT",
        )
    )


async def post_query(
    monkeypatch: pytest.MonkeyPatch,
    outcome: RetrievalOutcome | Exception,
    role: str = "learner",
    question: str = "Was regelt der EU AI Act?",
    generate: AsyncMock | None = None,
) -> Any:
    monkeypatch.setattr(
        "app.routers.query.read_pipeline_config", AsyncMock(return_value=CONFIG)
    )
    retrieve = (
        AsyncMock(side_effect=outcome)
        if isinstance(outcome, Exception)
        else AsyncMock(return_value=outcome)
    )
    monkeypatch.setattr("app.routers.query.retrieve", retrieve)
    monkeypatch.setattr(
        "app.routers.query.generate_answer", generate if generate is not None else make_generate()
    )

    app.dependency_overrides[get_current_user] = lambda: make_user(role)
    app.dependency_overrides[get_db] = lambda: make_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/query", json={"question": question, "session_id": None})


async def test_nothing_above_the_threshold_suppresses_without_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 0: below the gate there is nothing worth pointing the user at."""
    r = await post_query(monkeypatch, make_outcome(0.30, 0.21))

    assert r.status_code == 200
    body = r.json()
    assert body["suppressed"] is True
    assert body["suppression_reason"] == REASON_NO_MATCH
    assert body["citations"] == []
    assert body["message"]


async def test_weak_evidence_keeps_the_sources_it_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 1: the sources are real, only the footing is too thin to answer on."""
    r = await post_query(monkeypatch, make_outcome(0.36, 0.35))

    body = r.json()
    assert body["suppression_reason"] == REASON_WEAK_EVIDENCE
    assert len(body["citations"]) == 2
    assert body["confidence"]["retrieval_score"] < CONFIG.min_retrieval_confidence


async def test_strong_retrieval_returns_numbered_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r = await post_query(monkeypatch, make_outcome(0.9, 0.8, 0.7, 0.6, 0.5))

    body = r.json()
    assert body["suppression_reason"] is None
    assert [c["index"] for c in body["citations"]] == [1, 2, 3, 4, 5]
    assert body["confidence"]["retrieval_score"] >= CONFIG.min_retrieval_confidence
    # Whitespace collapsed so the excerpt is readable next to the answer.
    assert body["citations"][0]["excerpt"] == "Ein Chunk mit Inhalt."
    assert body["citations"][0]["page"] == 7


async def test_a_generated_answer_is_delivered_with_its_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Past both gates the answer is the message — no placeholder text (T-18)."""
    r = await post_query(monkeypatch, make_outcome(0.95, 0.94, 0.93, 0.92, 0.91))

    body = r.json()
    assert body["suppressed"] is False
    assert body["message"] == ANSWER
    assert body["citations"]
    # Stage 2 ran and found the one statement backed. `score` is still the
    # retrieval score alone — T-23 turns it into the composite.
    assert body["confidence"]["citation_coverage"] == 1.0
    assert body["confidence"]["score"] == body["confidence"]["retrieval_score"]
    assert body["answer_id"]
    assert body["session_id"]


async def test_debug_is_hidden_from_a_learner(monkeypatch: pytest.MonkeyPatch) -> None:
    r = await post_query(monkeypatch, make_outcome(0.9, 0.8), role="learner")

    assert r.json()["debug"] is None


async def test_debug_shows_the_pipeline_to_an_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    r = await post_query(monkeypatch, make_outcome(0.9, 0.8), role="admin")

    debug = r.json()["debug"]
    assert [stage["id"] for stage in debug["stages"]] == [
        "retrieval_gate",
        "retrieval_confidence",
        "citation_coverage",
    ]
    assert all(stage["passed"] for stage in debug["stages"])
    assert [call["step"] for call in debug["llm_calls"]] == [STEP_GROUNDING]
    assert debug["self_check_ran"] is False  # stage 3 arrives with T-25
    assert debug["similarity_threshold"] == CONFIG.similarity_threshold
    assert debug["min_citation_coverage"] == CONFIG.min_citation_coverage
    assert debug["dense_above_threshold"] == 2
    assert len(debug["chunks"]) == 2


async def test_debug_marks_the_confidence_stage_as_skipped_below_the_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The point of the gate is that nothing downstream runs."""
    r = await post_query(monkeypatch, make_outcome(0.1), role="admin")

    stages = {stage["id"]: stage for stage in r.json()["debug"]["stages"]}
    assert stages["retrieval_gate"]["passed"] is False
    assert stages["retrieval_confidence"]["ran"] is False
    assert stages["citation_coverage"]["ran"] is False


async def test_too_short_question_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    r = await post_query(monkeypatch, make_outcome(0.9), question="ab")

    assert r.status_code == 422


async def test_retrieval_failure_is_an_outage_not_a_dont_know(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider outage must not be dressed up as a suppressed answer."""
    r = await post_query(monkeypatch, RuntimeError("api_base=https://secret.internal key=sk-123"))

    assert r.status_code == 503
    assert "sk-123" not in r.text


async def test_a_broken_threshold_suppresses_instead_of_returning_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-008, Nachtrag 2026-08-16: the caller turns ConfigurationError into
    "Weiss ich nicht", never into a 500 — and never into a looser threshold."""
    monkeypatch.setattr(
        "app.routers.query.read_pipeline_config",
        AsyncMock(side_effect=ConfigurationError("config: similarity_threshold ist keine Zahl")),
    )
    # Must not be reached: without usable thresholds nothing may be retrieved.
    retrieve = AsyncMock()
    monkeypatch.setattr("app.routers.query.retrieve", retrieve)

    app.dependency_overrides[get_current_user] = lambda: make_user("admin")
    app.dependency_overrides[get_db] = lambda: make_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/query", json={"question": "Was regelt der EU AI Act?"})

    assert r.status_code == 200
    body = r.json()
    assert body["suppressed"] is True
    assert body["suppression_reason"] == REASON_CONFIGURATION_ERROR
    assert body["citations"] == []
    # No thresholds means no scores were computed — reporting 0.0 would claim a
    # measurement that never happened.
    assert body["confidence"] is None
    assert body["debug"] is None
    # answer_id is the feedback foreign key, so this path persists a row too.
    assert uuid.UUID(body["answer_id"])
    retrieve.assert_not_awaited()


async def test_a_programming_error_is_not_dressed_up_as_a_provider_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A TypeError is a bug, not an outage — it must not become a polite 503."""
    with pytest.raises(TypeError):
        await post_query(monkeypatch, TypeError("kaputt"))
# --- generation (T-18) -----------------------------------------------------


async def test_no_llm_call_below_the_retrieval_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """The gate exists to spend nothing on an out-of-corpus question (ADR-007)."""
    generate = make_generate()
    await post_query(monkeypatch, make_outcome(0.30, 0.21), generate=generate)

    generate.assert_not_awaited()


async def test_no_llm_call_when_the_confidence_stage_suppresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 1 decides before the provider is reached, not after."""
    generate = make_generate()
    await post_query(monkeypatch, make_outcome(0.36, 0.35), generate=generate)

    generate.assert_not_awaited()


async def test_a_refusal_is_suppressed_and_keeps_its_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model reported no coverage: standardised text, never its own wording."""
    r = await post_query(
        monkeypatch, make_outcome(0.9, 0.8, 0.7), generate=make_generate(answer=None)
    )

    body = r.json()
    assert body["suppressed"] is True
    assert body["suppression_reason"] == REASON_GENERATION_REFUSED
    assert "WEISS_NICHT" not in body["message"]
    # The sources are real, only the coverage is missing.
    assert len(body["citations"]) == 3


async def test_generation_failure_is_an_outage_not_a_dont_know(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dead provider must not look like a suppressed answer — and must not leak."""
    generate = AsyncMock(side_effect=RuntimeError("api_base=https://secret.internal key=sk-123"))
    r = await post_query(monkeypatch, make_outcome(0.9, 0.8), generate=generate)

    assert r.status_code == 503
    assert "sk-123" not in r.text
    assert "secret.internal" not in r.text


async def test_the_admin_debug_carries_the_grounding_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r = await post_query(monkeypatch, make_outcome(0.9, 0.8), role="admin")

    call = r.json()["debug"]["llm_calls"][0]
    assert call["step"] == STEP_GROUNDING
    assert call["prompt"]
    assert call["response"] == ANSWER


async def test_the_prompt_numbers_the_chunks_like_the_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[1] in the answer has to mean citations[0] — one list, numbered once."""
    captured: dict[str, str] = {}

    async def render(question: str, context: list[RetrievalHit]) -> GenerationResult:
        system, user = build_prompt(question, context)
        captured["user"] = user
        joined = system + chr(10) + chr(10) + user
        return GenerationResult(
            answer=ANSWER, truncated=False, prompt=joined, raw_response=ANSWER
        )

    r = await post_query(
        monkeypatch, make_outcome(0.9, 0.8, 0.7), generate=AsyncMock(side_effect=render)
    )

    for citation in r.json()["citations"]:
        assert f"[{citation['index']}] ({citation['filename']}" in captured["user"]


async def test_a_truncated_answer_is_withheld_whole(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cut off at the token cap, the last claim may have lost its [n] (ADR-008)."""
    r = await post_query(
        monkeypatch,
        make_outcome(0.9, 0.8),
        generate=make_generate(answer=None, truncated=True),
    )

    body = r.json()
    assert body["suppressed"] is True
    assert body["suppression_reason"] == REASON_GENERATION_TRUNCATED
    # Distinguishable from a refusal: the sources fit, the question was too broad.
    assert body["suppression_reason"] != REASON_GENERATION_REFUSED
    assert len(body["citations"]) == 2


# ── Stage 2: Grounding-/Citation-Check (T-19) ───────────────────────────────


async def test_a_thinly_backed_answer_is_suppressed_and_keeps_its_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Below min_citation_coverage the answer is withheld, the sources are not.

    The user is meant to be able to sharpen the question — which needs the
    sources that were found, just not the text that failed to use them.
    """
    answer = (
        "Eine erste belegte Aussage [1]. Eine zweite Aussage ohne jeden Beleg. "
        "Eine dritte Aussage ebenfalls ganz ohne Beleg."
    )

    r = await post_query(
        monkeypatch, make_outcome(0.9, 0.8, 0.7), generate=make_generate(answer=answer)
    )

    body = r.json()
    assert body["suppressed"] is True
    assert body["suppression_reason"] == REASON_CITATION_COVERAGE
    assert body["message"] != answer  # the standardised text, never the draft
    assert body["citations"]
    assert body["confidence"]["citation_coverage"] == 0.3333


async def test_a_fabricated_reference_is_suppressed(monkeypatch: pytest.MonkeyPatch) -> None:
    """AK 2: [9] out of three delivered chunks is a source that never existed."""
    answer = "Das ergibt sich unmittelbar aus dem Dokument [9]."

    r = await post_query(
        monkeypatch, make_outcome(0.9, 0.8, 0.7), generate=make_generate(answer=answer)
    )

    body = r.json()
    assert body["suppressed"] is True
    assert body["suppression_reason"] == REASON_CITATION_INVALID
    assert body["message"] != answer


async def test_a_four_digit_reference_is_suppressed_like_any_other(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AK 2 must not depend on how many digits the invented number has.

    Review of PR #86: with a three-digit bound this exact answer was delivered —
    coverage 0.5 met the threshold and the "[2026]" was invisible to the check,
    so it shipped with a citation pointing at nothing.
    """
    answer = "Die Frist betraegt 30 Tage [1]. Der Anhang nennt weitere Ausnahmen [2026]."

    r = await post_query(
        monkeypatch, make_outcome(0.9, 0.8, 0.7), generate=make_generate(answer=answer)
    )

    body = r.json()
    assert body["suppressed"] is True
    assert body["suppression_reason"] == REASON_CITATION_INVALID
    assert body["message"] != answer


async def test_an_invented_reference_beats_a_perfect_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No threshold makes a fabricated source deliverable — validity comes first."""
    answer = "Eine erste belegte Aussage [1]. Eine zweite mit erfundenem Beleg [9]."

    r = await post_query(
        monkeypatch, make_outcome(0.9, 0.8, 0.7), generate=make_generate(answer=answer)
    )

    assert r.json()["suppression_reason"] == REASON_CITATION_INVALID


async def test_an_answer_citing_nothing_is_suppressed(monkeypatch: pytest.MonkeyPatch) -> None:
    """AK 1: an answer without a single source reference is not delivered."""
    answer = "Der EU AI Act regelt Hochrisiko-Systeme umfassend und im Detail."

    r = await post_query(
        monkeypatch, make_outcome(0.9, 0.8, 0.7), generate=make_generate(answer=answer)
    )

    body = r.json()
    assert body["suppressed"] is True
    assert body["suppression_reason"] == REASON_CITATION_COVERAGE
    assert body["confidence"]["citation_coverage"] == 0.0


async def test_a_coverage_exactly_on_the_threshold_is_delivered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-008 tripwire: the comparison is >=, never >.

    Half the segments backed is exactly the seeded `min_citation_coverage`, and
    tightening the comparison here would silently diverge from the value an
    operator reads in the config table — the same rule stage 0 follows.
    """
    answer = "Eine erste belegte Aussage [1]. Eine zweite Aussage voellig ohne Beleg."

    r = await post_query(
        monkeypatch, make_outcome(0.95, 0.94, 0.93), generate=make_generate(answer=answer)
    )

    body = r.json()
    assert body["confidence"]["citation_coverage"] == CONFIG.min_citation_coverage
    assert body["suppressed"] is False
    assert body["message"] == answer


async def test_a_suppressed_answer_is_not_stored_as_an_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 2 is the first stage that suppresses text that actually exists.

    `answer_text` is what a later evaluation reads as "the answer the pipeline
    produced" (ADR-009); a withheld draft stored there would count as one.
    """
    db = make_db()
    monkeypatch.setattr("app.routers.query.read_pipeline_config", AsyncMock(return_value=CONFIG))
    monkeypatch.setattr(
        "app.routers.query.retrieve", AsyncMock(return_value=make_outcome(0.9, 0.8, 0.7))
    )
    monkeypatch.setattr(
        "app.routers.query.generate_answer",
        make_generate(answer="Eine Aussage ganz ohne jeden Beleg dazu."),
    )
    app.dependency_overrides[get_current_user] = lambda: make_user("learner")
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/query", json={"question": "Was regelt der EU AI Act?"})

    answer = next(
        row for call in db.add.call_args_list for row in call.args if hasattr(row, "suppressed")
    )
    assert answer.suppressed is True
    assert answer.answer_text is None
    assert answer.citation_coverage == 0.0  # measured, not skipped


async def test_the_coverage_column_stays_null_when_the_stage_never_ran(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """0.0 would read as "measured, nothing covered" and pollute the calibration."""
    db = make_db()
    monkeypatch.setattr("app.routers.query.read_pipeline_config", AsyncMock(return_value=CONFIG))
    monkeypatch.setattr("app.routers.query.retrieve", AsyncMock(return_value=make_outcome(0.1)))
    monkeypatch.setattr("app.routers.query.generate_answer", make_generate())
    app.dependency_overrides[get_current_user] = lambda: make_user("learner")
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/query", json={"question": "Was regelt der EU AI Act?"})

    answer = next(
        row for call in db.add.call_args_list for row in call.args if hasattr(row, "suppressed")
    )
    assert answer.citation_coverage is None


async def test_stage_two_does_not_run_on_a_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    """There is no text to measure, and the refusal already suppressed."""
    r = await post_query(
        monkeypatch, make_outcome(0.9, 0.8), role="admin", generate=make_generate(answer=None)
    )

    body = r.json()
    assert body["suppression_reason"] == REASON_GENERATION_REFUSED
    stages = {stage["id"]: stage for stage in body["debug"]["stages"]}
    assert stages["citation_coverage"]["ran"] is False


async def test_stage_two_does_not_run_on_a_truncated_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r = await post_query(
        monkeypatch,
        make_outcome(0.9, 0.8),
        role="admin",
        generate=make_generate(answer=ANSWER, truncated=True),
    )

    body = r.json()
    assert body["suppression_reason"] == REASON_GENERATION_TRUNCATED
    stages = {stage["id"]: stage for stage in body["debug"]["stages"]}
    assert stages["citation_coverage"]["ran"] is False


async def test_stage_two_costs_no_extra_llm_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stage 2 is deterministic — the grounding call stays the only one (ADR-008)."""
    r = await post_query(monkeypatch, make_outcome(0.9, 0.8), role="admin")

    assert [call["step"] for call in r.json()["debug"]["llm_calls"]] == [STEP_GROUNDING]


async def test_the_admin_debug_names_the_invented_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An operator has to see *which* source was invented, not just that one was."""
    r = await post_query(
        monkeypatch,
        make_outcome(0.9, 0.8, 0.7),
        role="admin",
        generate=make_generate(answer="Das ergibt sich unmittelbar aus dem Dokument [9]."),
    )

    stage = next(s for s in r.json()["debug"]["stages"] if s["id"] == "citation_coverage")
    assert stage["ran"] is True
    assert stage["passed"] is False
    assert "[9]" in stage["detail"]
    assert stage["threshold"] == CONFIG.min_citation_coverage


async def test_the_debug_stage_agrees_with_the_suppression_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The admin panel must never show "passed" for an answer that was withheld.

    Both readings used to compare the coverage against the threshold on their
    own. A coverage sitting exactly on the threshold is where a `<`/`>=` drift
    between them would surface first, so that is the case pinned here.
    """
    on_threshold = "Eine erste belegte Aussage [1]. Eine zweite Aussage voellig ohne Beleg."

    r = await post_query(
        monkeypatch,
        make_outcome(0.95, 0.94, 0.93),
        role="admin",
        generate=make_generate(answer=on_threshold),
    )

    body = r.json()
    stage = next(s for s in body["debug"]["stages"] if s["id"] == "citation_coverage")
    assert body["suppressed"] is False
    assert stage["passed"] is True
    assert stage["value"] == CONFIG.min_citation_coverage
