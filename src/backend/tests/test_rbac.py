"""End-to-end RBAC tests (T-07).

Unlike test_documents.py's role tests (which bypass auth via
`app.dependency_overrides[get_current_user]`), these tests send real bearer
tokens through the actual HTTP stack and exercise the real
`get_current_user` / `decode_token` / `HTTPBearer` code path. Only `get_db`
is mocked, so the JWT decoding, expiry check, and role check are all real.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.auth.jwt import create_access_token
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.main import app
from app.models.tables import User


@pytest.fixture(autouse=True)
def _reset_state() -> Iterator[None]:
    limiter.reset()
    yield
    app.dependency_overrides.clear()
    limiter.reset()


def make_db_with_user(user_id: str, role: str = "learner") -> AsyncMock:
    """DB whose lookup in get_current_user resolves to a real, active User."""
    user = User(
        id=user_id,
        email="rbac-test@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


def expired_token(subject: str, role: str) -> str:
    payload = {
        "sub": subject,
        "role": role,
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---- /auth/me ----------------------------------------------------------


async def test_me_without_token_returns_401() -> None:
    async with await _client() as client:
        r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_with_garbage_token_returns_401() -> None:
    async with await _client() as client:
        r = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


async def test_me_with_expired_token_returns_401() -> None:
    user_id = str(uuid4())
    token = expired_token(user_id, "learner")
    async with await _client() as client:
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_me_with_valid_token_returns_200() -> None:
    user_id = str(uuid4())
    app.dependency_overrides[get_db] = lambda: make_db_with_user(user_id, "learner")
    token = create_access_token(user_id, "learner")
    async with await _client() as client:
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["id"] == user_id


# ---- /auth/logout -------------------------------------------------------


async def test_logout_without_token_returns_401() -> None:
    async with await _client() as client:
        r = await client.post("/auth/logout")
    assert r.status_code == 401


async def test_logout_with_garbage_token_returns_401() -> None:
    async with await _client() as client:
        r = await client.post("/auth/logout", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


async def test_logout_with_expired_token_returns_401() -> None:
    user_id = str(uuid4())
    token = expired_token(user_id, "learner")
    async with await _client() as client:
        r = await client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_logout_with_valid_token_returns_204_with_empty_body() -> None:
    user_id = str(uuid4())
    app.dependency_overrides[get_db] = lambda: make_db_with_user(user_id, "learner")
    token = create_access_token(user_id, "learner")
    async with await _client() as client:
        r = await client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
    assert r.content == b""


# ---- POST /documents (role-gated) ---------------------------------------


async def test_documents_post_without_token_returns_401() -> None:
    async with await _client() as client:
        r = await client.post("/documents", files={"file": ("a.pdf", b"x", "application/pdf")})
    assert r.status_code == 401


async def test_documents_post_with_wrong_role_returns_403() -> None:
    user_id = str(uuid4())
    app.dependency_overrides[get_db] = lambda: make_db_with_user(user_id, "learner")
    token = create_access_token(user_id, "learner")
    async with await _client() as client:
        r = await client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("a.pdf", b"x", "application/pdf")},
        )
    assert r.status_code == 403


async def test_documents_post_with_correct_role_is_authorized() -> None:
    """Proves the happy path is not blocked — asserts past the 401/403 auth
    gate, not full upload semantics (already covered by test_documents.py)."""
    user_id = str(uuid4())
    db = make_db_with_user(user_id, "knowledge_owner")
    db.add = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    token = create_access_token(user_id, "knowledge_owner")
    async with await _client() as client:
        r = await client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("a.pdf", b"x", "application/pdf")},
        )
    assert r.status_code not in (401, 403)
