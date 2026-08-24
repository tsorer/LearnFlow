from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.auth.jwt import DUMMY_PASSWORD_HASH, decode_token, hash_password
from app.database import get_db
from app.main import app


def make_db() -> AsyncMock:
    """DB that finds no user for any login attempt."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    return db


def make_db_with_user(
    hashed_password: str = "$2b$12$irrelevant",
    user_id: UUID | None = None,
) -> AsyncMock:
    """DB that returns an active learner for any login attempt.

    The default hash is a placeholder for tests that mock `verify_password` away;
    pass a real bcrypt hash to exercise the actual verification.
    """
    user = MagicMock()
    user.id = user_id or uuid4()
    user.role = "learner"
    user.hashed_password = hashed_password
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.fixture
def no_bcrypt(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Skip the real bcrypt round (~0.3 s) in tests that fire many logins."""
    spy = AsyncMock(return_value=False)
    monkeypatch.setattr("app.routers.auth.verify_password", spy)
    return spy


async def _login(db: AsyncMock, email: str = "nobody@example.com") -> Response:
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/auth/login", json={"email": email, "password": "wrong"})


async def test_login_unknown_email_returns_401() -> None:
    r = await _login(make_db())
    assert r.status_code == 401


async def test_login_wrong_password_for_existing_user_returns_401() -> None:
    """AK 2: the account exists and is active, only the password is wrong.

    Runs the real bcrypt comparison rather than mocking it away — this is the one
    test that proves a genuine hash mismatch is rejected.
    """
    hashed = await hash_password("the-correct-password")

    r = await _login(make_db_with_user(hashed_password=hashed), "lara@example.com")

    assert r.status_code == 401


async def test_login_success_returns_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routers.auth.verify_password", AsyncMock(return_value=True))

    r = await _login(make_db_with_user(), "lara@example.com")

    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["role"] == "learner"


async def test_issued_token_carries_role_and_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    """AK 4: the role must be in the token itself, not just in the response body.

    `sub` is asserted too because `create_access_token(subject, role)` takes two
    positional strings — swapping them would still produce a valid-looking body.
    """
    monkeypatch.setattr("app.routers.auth.verify_password", AsyncMock(return_value=True))
    user_id = uuid4()

    r = await _login(make_db_with_user(user_id=user_id), "lara@example.com")

    claims = decode_token(r.json()["access_token"])
    assert claims["role"] == "learner"
    assert claims["sub"] == str(user_id)


async def test_login_verifies_dummy_hash_for_unknown_email(no_bcrypt: AsyncMock) -> None:
    """No bcrypt shortcut for unknown accounts — otherwise timing enumerates users."""
    r = await _login(make_db())

    assert r.status_code == 401
    no_bcrypt.assert_awaited_once_with("wrong", DUMMY_PASSWORD_HASH)


async def test_login_rate_limited_after_five_attempts_per_ip(no_bcrypt: AsyncMock) -> None:
    db = make_db()
    for _ in range(5):
        assert (await _login(db)).status_code == 401

    r = await _login(db)
    assert r.status_code == 429
    # Shared with /query (T-45): one German sentence for both, because both are
    # shown to a user. The limit itself travels in the response headers.
    assert r.json()["detail"] == (
        "Zu viele Anfragen. Bitte warte einen Moment und versuche es erneut."
    )


async def test_rate_limit_counts_per_ip_not_per_account(no_bcrypt: AsyncMock) -> None:
    """Switching the e-mail must not buy a fresh budget — the key is the client IP."""
    db = make_db()
    for i in range(5):
        assert (await _login(db, f"user{i}@example.com")).status_code == 401

    assert (await _login(db, "someone-else@example.com")).status_code == 429
