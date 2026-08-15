"""POST /query — the contract T-17 owes the frontend (US-01, ADR-008)."""

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
    REASON_CONFIGURATION_ERROR,
    REASON_GENERATION_PENDING,
    REASON_NO_MATCH,
    REASON_WEAK_EVIDENCE,
)
from app.services.config import ConfigurationError, PipelineConfig
from app.services.retrieval import RetrievalHit, RetrievalOutcome

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


async def post_query(
    monkeypatch: pytest.MonkeyPatch,
    outcome: RetrievalOutcome | Exception,
    role: str = "learner",
    question: str = "Was regelt der EU AI Act?",
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
    assert body["suppression_reason"] == REASON_GENERATION_PENDING
    assert [c["index"] for c in body["citations"]] == [1, 2, 3, 4, 5]
    assert body["confidence"]["retrieval_score"] >= CONFIG.min_retrieval_confidence
    # Whitespace collapsed so the excerpt is readable next to the answer.
    assert body["citations"][0]["excerpt"] == "Ein Chunk mit Inhalt."
    assert body["citations"][0]["page"] == 7


async def test_answer_stays_suppressed_until_generation_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-17 must never deliver an answer text — there is no generation yet."""
    r = await post_query(monkeypatch, make_outcome(0.95, 0.94, 0.93, 0.92, 0.91))

    body = r.json()
    assert body["suppressed"] is True
    assert body["confidence"]["citation_coverage"] == 0.0
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
    ]
    assert all(stage["passed"] for stage in debug["stages"])
    assert debug["llm_calls"] == []  # T-17 reaches no LLM at all
    assert debug["self_check_ran"] is False
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
