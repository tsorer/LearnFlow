"""POST /query counts per account, not per address (T-45, #79).

The limit exists because this is the only endpoint that spends provider money:
one embedding per question, plus one or two LLM calls once both gates pass
(ADR-004, ADR-005). What is asserted here is the policy — the number, the key,
and the shape of the refusal — not slowapi's counting, which is its own.

`conftest.py` resets the limiter around every test, so the window never leaks
into the next one.
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.database import get_db
from app.limiter import account_key
from app.main import app
from app.models.tables import User
from app.routers.query import QUERY_RATE_LIMIT
from app.services.config import ConfidenceThresholds, PipelineConfig
from app.services.retrieval import RetrievalOutcome
from tests.test_query import make_db, make_user

LIMIT = int(QUERY_RATE_LIMIT.split("/")[0])

CONFIG = PipelineConfig(
    similarity_threshold=0.35,
    min_retrieval_confidence=0.40,
    min_citation_coverage=0.50,
    # Carried only because PipelineConfig reads the whole config table at once —
    # nothing in this file gets far enough for stage 3 to matter.
    self_check_band_low=0.50,
    self_check_band_high=0.75,
    retrieval_top_k=20,
    context_top_n=5,
    rrf_k=60,
)


def bearer(user: User) -> dict[str, str]:
    """A real token for `user` — `account_key` reads the subject out of it."""
    return {"Authorization": f"Bearer {create_access_token(str(user.id), user.role)}"}


@pytest.fixture
def stub_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retrieval finds nothing, so no question reaches a provider in this file."""
    monkeypatch.setattr(
        "app.routers.query.read_pipeline_config", AsyncMock(return_value=CONFIG)
    )
    monkeypatch.setattr(
        "app.routers.query.read_confidence_thresholds",
        AsyncMock(return_value=ConfidenceThresholds(high=0.75, medium=0.45)),
    )
    monkeypatch.setattr(
        "app.routers.query.retrieve",
        AsyncMock(return_value=RetrievalOutcome(
            candidates=[], context=[], dense_count=0, sparse_count=0
        )),
    )


async def ask(client: AsyncClient, headers: dict[str, str]) -> Any:
    return await client.post(
        "/query", json={"question": "Was regelt der EU AI Act?"}, headers=headers
    )


async def test_the_question_after_the_limit_is_refused(stub_pipeline: None) -> None:
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: make_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        allowed = [await ask(client, bearer(user)) for _ in range(LIMIT)]
        refused = await ask(client, bearer(user))

    assert [r.status_code for r in allowed] == [200] * LIMIT
    assert refused.status_code == 429
    # The Error schema of openapi.yaml is a `detail` string — slowapi's own
    # handler would have answered `{"error": ...}`, which nothing else here uses.
    body = refused.json()
    assert list(body) == ["detail"]
    assert body["detail"] == (
        "Zu viele Anfragen. Bitte warte einen Moment und versuche es erneut."
    )


async def test_the_budget_belongs_to_the_account_not_the_connection(
    stub_pipeline: None,
) -> None:
    """Two accounts from one address: the second must not inherit the first's window.

    This is the difference to /auth/login, which counts per IP on purpose. Both
    requests here come from the same test client — only the token differs.
    """
    heavy, quiet = make_user(), make_user()
    app.dependency_overrides[get_db] = lambda: make_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: heavy
        for _ in range(LIMIT):
            await ask(client, bearer(heavy))
        exhausted = await ask(client, bearer(heavy))

        app.dependency_overrides[get_current_user] = lambda: quiet
        untouched = await ask(client, bearer(quiet))

    assert exhausted.status_code == 429
    assert untouched.status_code == 200


def make_request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/query",
        "headers": headers,
        "client": ("10.0.0.7", 51234),
    })


def test_the_key_is_the_token_subject() -> None:
    subject = str(uuid.uuid4())
    token = create_access_token(subject, "learner")

    key = account_key(make_request([(b"authorization", f"Bearer {token}".encode())]))

    assert key == f"account:{subject}"


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param([], id="no header"),
        pytest.param([(b"authorization", b"Bearer not-a-jwt")], id="undecodable token"),
        pytest.param([(b"authorization", b"Basic bGFyYTp4")], id="wrong scheme"),
    ],
)
def test_without_a_usable_token_the_key_falls_back_to_the_address(
    headers: list[tuple[bytes, bytes]],
) -> None:
    """Defensive only: the endpoint's dependency answers 401 before the limiter
    counts. The fallback exists so the key is always defined."""
    assert account_key(make_request(headers)) == "address:10.0.0.7"
