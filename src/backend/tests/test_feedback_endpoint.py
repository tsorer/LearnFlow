import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import Answer, User


def make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()  # AsyncSession.add() is synchronous on the real session
    return db


def make_user(role: str = "learner") -> User:
    return User(
        id=uuid.uuid4(),
        email="learner@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def make_answer() -> Answer:
    return Answer(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        question="Wie funktioniert X?",
        answer_text="X funktioniert so.",
        confidence_score=0.8,
        citation_coverage=0.9,
        retrieval_confidence=0.7,
        suppressed=False,
        created_at=datetime.now(UTC),
    )


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
    db = make_db()
    db.get = AsyncMock(return_value=answer)

    r = await _post_feedback(answer.id, {"helpful": True, "category": None, "comment": None}, db)

    assert r.status_code == 204
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


async def test_feedback_without_optional_fields_returns_204() -> None:
    answer = make_answer()
    db = make_db()
    db.get = AsyncMock(return_value=answer)

    r = await _post_feedback(answer.id, {"helpful": False}, db)

    assert r.status_code == 204


async def test_feedback_positive_category_with_helpful_true_returns_204() -> None:
    answer = make_answer()
    db = make_db()
    db.get = AsyncMock(return_value=answer)

    r = await _post_feedback(
        answer.id, {"helpful": True, "category": "vollstaendig", "comment": "Danke!"}, db
    )

    assert r.status_code == 204


async def test_feedback_unknown_answer_returns_404() -> None:
    db = make_db()
    db.get = AsyncMock(return_value=None)

    r = await _post_feedback(uuid.uuid4(), {"helpful": True}, db)

    assert r.status_code == 404
    db.add.assert_not_called()


async def test_feedback_no_auth_returns_401() -> None:
    db = make_db()
    r = await _post_feedback(uuid.uuid4(), {"helpful": True}, db, role=None)
    assert r.status_code == 401


async def test_feedback_positive_category_with_helpful_false_returns_400() -> None:
    answer = make_answer()
    db = make_db()
    db.get = AsyncMock(return_value=answer)

    r = await _post_feedback(
        answer.id, {"helpful": False, "category": "vollstaendig"}, db
    )

    assert r.status_code == 400
    db.add.assert_not_called()


async def test_feedback_negative_category_with_helpful_true_returns_400() -> None:
    answer = make_answer()
    db = make_db()
    db.get = AsyncMock(return_value=answer)

    r = await _post_feedback(
        answer.id, {"helpful": True, "category": "veraltet"}, db
    )

    assert r.status_code == 400


async def test_feedback_unknown_category_returns_422() -> None:
    answer = make_answer()
    db = make_db()
    db.get = AsyncMock(return_value=answer)

    r = await _post_feedback(answer.id, {"helpful": True, "category": "nicht_im_enum"}, db)

    assert r.status_code == 422


async def test_feedback_comment_over_500_chars_returns_422() -> None:
    answer = make_answer()
    db = make_db()
    db.get = AsyncMock(return_value=answer)

    r = await _post_feedback(answer.id, {"helpful": True, "comment": "x" * 501}, db)

    assert r.status_code == 422
