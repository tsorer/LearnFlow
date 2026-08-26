"""POST /quiz/generate — what Stefan's click writes and what it refuses to (T-33).

Auth is bypassed here via `app.dependency_overrides`; the real token path is
covered once, for every endpoint, in test_rbac.py. What this file is about is
the row that reaches the table: `status` and `chunk_id` are what the review of
T-35 and the replace path of T-15 read, and neither of them is visible in the
response body alone.
"""

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.database import get_db
from app.main import app
from app.models.tables import QuizQuestion, QuizQuestionStatus, User
from app.routers.quiz import QUIZ_RATE_LIMIT
from app.services.quiz import GeneratedQuestion
from app.services.retrieval import SourceChunk


def make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()  # AsyncSession.add() is synchronous on the real session
    return db


def make_user(role: str) -> User:
    return User(
        id=uuid.uuid4(),
        email="owner@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def make_chunk(content: str = "Der AI Act regelt Hochrisiko-Systeme.") -> SourceChunk:
    return SourceChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="ai_act.pdf",
        content=content,
        page=7,
        heading="Kapitel 1",
    )


def make_question(source: SourceChunk | None = None) -> GeneratedQuestion:
    return GeneratedQuestion(
        question="Was regelt der AI Act?",
        options=["Hochrisiko-Systeme", "Steuerrecht", "Baurecht", "Seerecht"],
        correct_answer="A",
        explanation="Der Abschnitt nennt Hochrisiko-Systeme.",
        source=source or make_chunk(),
    )


def patch_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    chunks: list[SourceChunk] | None = None,
    generate: Any = None,
) -> None:
    """Replace both steps of the endpoint.

    `generate_quiz` is patched in every test, not only where it matters: an
    unpatched one reaches the real provider the moment a test gets as far as the
    call, which is the normal case here.
    """
    monkeypatch.setattr(
        "app.routers.quiz.sample_chunks",
        AsyncMock(return_value=[make_chunk()] if chunks is None else chunks),
    )
    monkeypatch.setattr(
        "app.routers.quiz.generate_quiz",
        generate if generate is not None else AsyncMock(return_value=[make_question()]),
    )


async def _post(db: AsyncMock, role: str | None = "knowledge_owner") -> Any:
    if role is not None:
        app.dependency_overrides[get_current_user] = lambda: make_user(role)
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/quiz/generate")


LIMIT = int(QUIZ_RATE_LIMIT.split("/")[0])


async def _post_as(user: User) -> Any:
    """Post with a real bearer token, so the limiter keys on the account.

    `account_key` reads the raw Authorization header and never sees the
    dependency override, so without a token the limit would silently fall back
    to counting per address — which is the policy this endpoint does not have.
    """
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: make_db()
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id), user.role)}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/quiz/generate", headers=headers)


def added_rows(db: AsyncMock) -> list[QuizQuestion]:
    return [row for call in db.add.call_args_list for row in call.args]


# --- the happy path ---


async def test_generation_returns_201_with_the_questions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_pipeline(monkeypatch)
    db = make_db()

    response = await _post(db)

    assert response.status_code == 201
    body = response.json()
    assert body["generated"] == 1
    assert body["questions"][0]["question"] == "Was regelt der AI Act?"
    assert len(body["questions"][0]["options"]) == 4
    db.commit.assert_awaited_once()


async def test_a_generated_question_is_stored_as_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The row, not the response, because this is what US-07 hangs on: nothing
    generated is visible to a learner until someone approves it (ADR-008 —
    here the human is the gate)."""
    patch_pipeline(monkeypatch)
    db = make_db()

    await _post(db)

    row = added_rows(db)[0]
    assert row.status == QuizQuestionStatus.pending
    assert row.approved_at is None


async def test_the_row_keeps_both_the_chunk_and_its_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reference dies with the chunk when the document is replaced; the
    excerpt is what the review still has to show (US-07)."""
    chunk = make_chunk(content="Der AI Act regelt Hochrisiko-Systeme.")
    patch_pipeline(
        monkeypatch, chunks=[chunk], generate=AsyncMock(return_value=[make_question(chunk)])
    )
    db = make_db()

    await _post(db)

    row = added_rows(db)[0]
    assert row.chunk_id == chunk.chunk_id
    assert row.document_id == chunk.document_id
    assert row.source_excerpt == "Der AI Act regelt Hochrisiko-Systeme."


async def test_generated_counts_the_rows_that_were_written(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run that lost two questions to validation reports three, not five —
    the count is a fact about the database, not a repetition of the request."""
    patch_pipeline(
        monkeypatch, generate=AsyncMock(return_value=[make_question() for _ in range(3)])
    )
    db = make_db()

    response = await _post(db)

    assert response.json()["generated"] == 3
    assert len(added_rows(db)) == 3


# --- who may ask ---


async def test_a_learner_may_not_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generation is knowledge-owner work (US-07): the questions it produces
    are proposals for the review, and a learner has no review to do."""
    patch_pipeline(monkeypatch)

    response = await _post(make_db(), role="learner")

    assert response.status_code == 403


async def test_without_a_token_there_is_no_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_pipeline(monkeypatch)

    response = await _post(make_db(), role=None)

    assert response.status_code == 401


# --- when there is nothing to deliver ---


async def test_an_area_without_indexed_documents_answers_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No material means no questions. Deliberately a conflict with the state
    and not an empty 201: the caller asked for something the system cannot
    produce yet, and saying "created nothing" hides that."""
    generate = AsyncMock()
    patch_pipeline(monkeypatch, chunks=[], generate=generate)
    db = make_db()

    response = await _post(db)

    assert response.status_code == 409
    generate.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_a_provider_outage_answers_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """And the provider's own message stays in the log: LiteLLM errors carry
    api_base and, on an auth failure, a fragment of the key."""
    patch_pipeline(
        monkeypatch,
        generate=AsyncMock(side_effect=RuntimeError("api_base=https://secret.internal key=sk-123")),
    )
    db = make_db()

    response = await _post(db)

    assert response.status_code == 503
    assert "secret.internal" not in response.text
    db.commit.assert_not_awaited()


async def test_an_unreadable_response_answers_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ValueError of parse_quiz_response arrives here."""
    patch_pipeline(monkeypatch, generate=AsyncMock(side_effect=ValueError("kein gültiges JSON")))

    response = await _post(make_db())

    assert response.status_code == 503


async def test_a_run_without_a_single_valid_question_answers_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Not a successful run that happens to be empty: the model answered, and
    none of it survived validation. Reported as the failure it is."""
    patch_pipeline(monkeypatch, generate=AsyncMock(return_value=[]))
    db = make_db()

    response = await _post(db)

    assert response.status_code == 503
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


async def test_a_bug_is_not_disguised_as_an_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    """AttributeError and friends signal broken code, not a broken dependency —
    they belong in CI as a 500, not behind "bitte später erneut versuchen"."""
    patch_pipeline(monkeypatch, generate=AsyncMock(side_effect=AttributeError("tippfehler")))

    with pytest.raises(AttributeError):
        await _post(make_db())


# --- how often ---


async def test_generation_is_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    """One click is a batch of five questions out of a ten-chunk context, so it
    costs several times an answer — and nothing else caps what a held-down
    button spends (the spec promises 429 here)."""
    patch_pipeline(monkeypatch)
    user = make_user("knowledge_owner")

    codes = [(await _post_as(user)).status_code for _ in range(LIMIT + 1)]

    assert codes[:LIMIT] == [201] * LIMIT
    assert codes[LIMIT] == 429


async def test_the_budget_belongs_to_the_account_not_the_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pilot users share one NAT address (Docs/03_QualityAttributes.md), so
    counting per address would let one owner lock the others out."""
    patch_pipeline(monkeypatch)
    for _ in range(LIMIT):
        await _post_as(make_user("knowledge_owner"))

    assert (await _post_as(make_user("knowledge_owner"))).status_code == 201
