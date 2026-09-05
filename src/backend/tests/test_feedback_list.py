"""GET /feedback -- Stefan's area overview (T-32).

Wiring tests only, following test_quiz_review.py's pattern: auth is bypassed
via app.dependency_overrides, and the mocked session answers the count query
then the page query. The real token path is covered once, for every endpoint,
in test_rbac.py.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import Feedback, User

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)


def make_user(role: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role}@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=NOW,
    )


def make_row(
    helpful: bool = True,
    category: str | None = "verstaendlich",
    comment: str | None = "Danke!",
) -> Feedback:
    return Feedback(
        id=uuid.uuid4(),
        answer_id=uuid.uuid4(),
        helpful=helpful,
        category=category,
        comment=comment,
        created_at=NOW - timedelta(minutes=5),
    )


def override(user: User, db: AsyncMock) -> None:
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db


def make_list_db(rows: list[Feedback], total: int | None = None) -> AsyncMock:
    """Session answering the two queries of the GET: the count, then the page."""
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=len(rows) if total is None else total)
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=result)
    return db


def compiled(call: Any) -> str:
    return str(call.args[0].compile(compile_kwargs={"literal_binds": True}))


def assert_validation_error_body(payload: Any) -> None:
    detail = payload["detail"]
    assert isinstance(detail, list), detail
    assert all({"loc", "msg", "type"} <= set(error) for error in detail), detail


async def test_get_returns_a_page_with_its_total() -> None:
    rows = [make_row(), make_row()]
    override(make_user("knowledge_owner"), make_list_db(rows, total=7))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["total"] == 7


async def test_unknown_category_value_degrades_the_row_instead_of_500ing_the_page() -> None:
    """`category` has no DB CHECK (unlike quiz_questions.status): a value that
    no longer matches the current FeedbackCategory enum -- e.g. after a rename
    or removal -- must not fail the whole dashboard for every other row."""
    rows = [make_row(category="ein_alter_wert_ausserhalb_des_enums"), make_row()]
    override(make_user("knowledge_owner"), make_list_db(rows, total=2))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["category"] is None
    assert body["items"][1]["category"] == "verstaendlich"


async def test_item_has_no_personal_reference() -> None:
    """AK 'ohne Personenbezug': the wire shape carries no answer_id, session_id
    or user_id -- only the fields FeedbackItem declares (openapi.yaml)."""
    override(make_user("knowledge_owner"), make_list_db([make_row()]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback")
    item = r.json()["items"][0]
    assert set(item) == {"id", "helpful", "category", "comment", "created_at"}


async def test_total_is_independent_of_limit() -> None:
    db = make_list_db([make_row()], total=42)
    override(make_user("knowledge_owner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback?limit=1")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    assert r.json()["total"] == 42
    assert "LIMIT" not in compiled(db.scalar.await_args).upper()


async def test_helpful_filter_reaches_the_sql() -> None:
    db = make_list_db([make_row(helpful=False, category="veraltet")])
    override(make_user("knowledge_owner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback?helpful=false")
    assert r.status_code == 200
    for call in (db.scalar.await_args, db.execute.await_args):
        assert "helpful = false" in compiled(call).lower()


async def test_category_filter_reaches_the_sql() -> None:
    db = make_list_db([make_row(category="veraltet", helpful=False)])
    override(make_user("knowledge_owner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback?category=veraltet")
    assert r.status_code == 200
    for call in (db.scalar.await_args, db.execute.await_args):
        assert "'veraltet'" in compiled(call)


async def test_contradictory_filters_still_query_the_database() -> None:
    """helpful=true + category=faktisch_falsch is not rejected -- filters cut
    the result set, they are not validated against each other. The endpoint
    still queries; an empty result is what makes the page empty."""
    db = make_list_db([])
    override(make_user("knowledge_owner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback?helpful=true&category=faktisch_falsch")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0}
    db.execute.assert_awaited_once()


async def test_admin_is_authorized() -> None:
    override(make_user("admin"), make_list_db([make_row()]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback")
    assert r.status_code == 200


async def test_learner_is_403() -> None:
    db = make_list_db([])
    override(make_user("learner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback")
    assert r.status_code == 403
    db.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "query", ["?limit=201", "?limit=0", "?offset=-1", "?category=nicht_im_enum"]
)
async def test_invalid_query_parameters_are_422(query: str) -> None:
    override(make_user("knowledge_owner"), make_list_db([]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/feedback{query}")
    assert r.status_code == 422
    assert_validation_error_body(r.json())


async def test_get_without_token_is_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/feedback")
    assert r.status_code == 401
