from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.auth.jwt import DUMMY_PASSWORD_HASH
from app.database import get_db
from app.limiter import limiter
from app.main import app


def make_db() -> AsyncMock:
    """DB that finds no user for any login attempt."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    return db


def make_db_with_user() -> AsyncMock:
    """DB that returns an active learner for any login attempt."""
    user = MagicMock()
    user.id = uuid4()
    user.role = "learner"
    user.hashed_password = "$2b$12$irrelevant"
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.fixture(autouse=True)
def _reset_state() -> Iterator[None]:
    limiter.reset()
    yield
    app.dependency_overrides.clear()
    limiter.reset()


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


async def test_login_wrong_credentials_returns_401() -> None:
    r = await _login(make_db())
    assert r.status_code == 401


async def test_login_success_returns_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routers.auth.verify_password", AsyncMock(return_value=True))

    r = await _login(make_db_with_user(), "lara@example.com")

    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["role"] == "learner"


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
    assert r.json()["detail"].startswith("Rate limit exceeded")


async def test_rate_limit_counts_per_ip_not_per_account(no_bcrypt: AsyncMock) -> None:
    """Switching the e-mail must not buy a fresh budget — the key is the client IP."""
    db = make_db()
    for i in range(5):
        assert (await _login(db, f"user{i}@example.com")).status_code == 401

    assert (await _login(db, "someone-else@example.com")).status_code == 429
