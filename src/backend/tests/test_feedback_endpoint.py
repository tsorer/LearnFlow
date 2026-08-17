import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import Answer, QuerySession, User

USER_ID = uuid.uuid4()


def make_db(*, answer: Answer | None, session: QuerySession | None = None) -> AsyncMock:
    db = AsyncMock()

    async def _get(model: type, _id: uuid.UUID) -> object | None:
        if model is Answer:
            return answer
        if model is QuerySession:
            return session
        raise AssertionError(f"unexpected db.get({model!r})")

    db.get = AsyncMock(side_effect=_get)
    return db


def make_user(role: str = "learner") -> User:
    return User(
        id=USER_ID,
        email="learner@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def make_answer(session_id: uuid.UUID | None = None) -> Answer:
    return Answer(
        id=uuid.uuid4(),
        session_id=session_id or uuid.uuid4(),
        question="Wie funktioniert X?",
        answer_text="X funktioniert so.",
        confidence_score=0.8,
        citation_coverage=0.9,
        retrieval_confidence=0.7,
        suppressed=False,
        created_at=datetime.now(UTC),
    )


def make_session(session_id: uuid.UUID, user_id: uuid.UUID | None = USER_ID) -> QuerySession:
    return QuerySession(id=session_id, user_id=user_id, created_at=datetime.now(UTC))


def bound_params(db: AsyncMock) -> dict:
    stmt = db.execute.await_args[0][0]
    return stmt.compile().params


async def _post_feedback(
    answer_id: uuid.UUID,
    body: dict,
    db: AsyncMock,
    role: str | None = "learner",
) -> "object":
    if role is not None:
        app.dependency_overrides[get_current_user] = lambda: make_user(role)
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(f"/answers/{answer_id}/feedback", json=body)


async def test_feedback_success_returns_204() -> None:
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id))

    r = await _post_feedback(answer.id, {"helpful": True, "category": None, "comment": None}, db)

    assert r.status_code == 204
    db.commit.assert_awaited_once()

    params = bound_params(db)
    assert params["answer_id"] == answer.id
    assert params["helpful"] is True
    assert params["category"] is None
    assert params["comment"] is None
    assert set(params) == {"id", "answer_id", "helpful", "category", "comment", "created_at"}


async def test_feedback_negative_category_with_helpful_false_returns_204() -> None:
    """The endpoint's main path per US-03 (👎 with a reason) — the other three
    category/helpful combinations are covered below, but without this one a
    wrong or empty NEGATIVE_CATEGORIES would 400 every real thumbs-down
    submission while the full suite stayed green."""
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id))

    r = await _post_feedback(
        answer.id, {"helpful": False, "category": "veraltet", "comment": "Nicht mehr aktuell"}, db
    )

    assert r.status_code == 204
    params = bound_params(db)
    assert params["helpful"] is False
    assert params["category"] == "veraltet"
    assert params["comment"] == "Nicht mehr aktuell"


async def test_feedback_without_optional_fields_returns_204() -> None:
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id))

    r = await _post_feedback(answer.id, {"helpful": False}, db)

    assert r.status_code == 204


async def test_feedback_positive_category_with_helpful_true_returns_204() -> None:
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id))

    r = await _post_feedback(
        answer.id, {"helpful": True, "category": "vollstaendig", "comment": "Danke!"}, db
    )

    assert r.status_code == 204
    params = bound_params(db)
    assert params["helpful"] is True
    assert params["category"] == "vollstaendig"
    assert params["comment"] == "Danke!"


async def test_feedback_anonymous_session_returns_204() -> None:
    """A session with no owner (user_id NULL) has no one specific to protect —
    any authenticated user may rate it."""
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id, user_id=None))

    r = await _post_feedback(answer.id, {"helpful": True}, db)

    assert r.status_code == 204


async def test_feedback_unknown_answer_returns_404() -> None:
    db = make_db(answer=None)

    r = await _post_feedback(uuid.uuid4(), {"helpful": True}, db)

    assert r.status_code == 404
    db.execute.assert_not_called()


async def test_feedback_other_users_answer_returns_404() -> None:
    """Same 404 as 'does not exist' (documents.py's PILOT_AREA pattern) — a
    different status here would itself leak which answer_ids belong to
    someone else's session."""
    answer = make_answer()
    other_user_id = uuid.uuid4()
    db = make_db(answer=answer, session=make_session(answer.session_id, user_id=other_user_id))

    r = await _post_feedback(answer.id, {"helpful": True}, db)

    assert r.status_code == 404
    db.execute.assert_not_called()


async def test_feedback_no_auth_returns_401() -> None:
    db = make_db(answer=None)
    r = await _post_feedback(uuid.uuid4(), {"helpful": True}, db, role=None)
    assert r.status_code == 401


async def test_feedback_positive_category_with_helpful_false_returns_400() -> None:
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id))

    r = await _post_feedback(answer.id, {"helpful": False, "category": "vollstaendig"}, db)

    assert r.status_code == 400
    db.execute.assert_not_called()


async def test_feedback_negative_category_with_helpful_true_returns_400() -> None:
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id))

    r = await _post_feedback(answer.id, {"helpful": True, "category": "veraltet"}, db)

    assert r.status_code == 400


async def test_feedback_unknown_category_returns_422() -> None:
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id))

    r = await _post_feedback(answer.id, {"helpful": True, "category": "nicht_im_enum"}, db)

    assert r.status_code == 422


async def test_feedback_comment_over_500_chars_returns_422() -> None:
    answer = make_answer()
    db = make_db(answer=answer, session=make_session(answer.session_id))

    r = await _post_feedback(answer.id, {"helpful": True, "comment": "x" * 501}, db)

    assert r.status_code == 422
