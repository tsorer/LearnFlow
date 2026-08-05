from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

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


@pytest.fixture(autouse=True)
def _reset_state():
    limiter.reset()
    yield
    app.dependency_overrides.clear()
    limiter.reset()


async def _login(db: AsyncMock) -> "object":
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )


async def test_login_wrong_credentials_returns_401() -> None:
    r = await _login(make_db())
    assert r.status_code == 401


async def test_login_rate_limited_after_five_attempts_per_minute() -> None:
    db = make_db()
    for _ in range(5):
        r = await _login(db)
        assert r.status_code == 401

    r = await _login(db)
    assert r.status_code == 429
