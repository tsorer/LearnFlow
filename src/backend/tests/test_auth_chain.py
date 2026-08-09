"""T-09: the auth chain in-process, without a running stack.

The existing tests each cover one end of the chain only: test_auth.py stops at the
issued token, and test_documents.py replaces `get_current_user` via
`dependency_overrides`, bypassing exactly the part that connects login to a
protected route. Here the whole path runs — login -> JWT -> decode -> user lookup
-> protected route — through the real dependency chain; only the database is
replaced.

This is an integration test, not an end-to-end test: browser, nginx and Postgres
are missing. Those seams are covered by `e2e/test_login_flow.py`. The value of
this file is that it runs in seconds without containers and exercises the failure
cases (expired, foreign signature, deleted user, deactivated account) cheaply.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from jose import jwt
from sqlalchemy import Select

from app.auth.jwt import create_access_token, hash_password
from app.config import settings
from app.database import get_db
from app.main import app
from app.models.tables import User

EMAIL = "lara@learnflow.ch"
PASSWORD = "correct-horse-battery-staple"
# A single real bcrypt hash for the whole module: the login endpoint has to verify
# against a genuine hash, but at cost 12 each call takes ~0.3 s.
PASSWORD_HASH = asyncio.run(hash_password(PASSWORD))
# Fixed instead of uuid4(): the value ends up in the test id, which must stay
# stable across runs (--last-failed, flakiness history in CI).
MISSING_DOCUMENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ff")


class _Result:
    """Stand-in for the SQLAlchemy result; the flow only uses scalar_one_or_none()."""

    def __init__(self, user: User | None) -> None:
        self._user = user

    def scalar_one_or_none(self) -> User | None:
        return self._user


class FakeDb:
    """AsyncSession stand-in answering the two SELECTs of the login flow.

    Lookups are resolved from the statement's bound parameters — by e-mail for the
    login, by id for the token lookup. That way the JWT really has to carry the
    right subject for the protected route to answer; a mock that returns the same
    user for every SELECT would hide exactly that.

    `User.is_active` is part of both queries but renders as a bare column predicate
    without a bind parameter. It is therefore detected on the compiled WHERE clause
    and reproduced here — otherwise the deactivation guard would silently drop out
    of the tests while still being enforced in the application.
    """

    def __init__(self, *users: User) -> None:
        self._users = users

    async def execute(self, stmt: Select[Any]) -> _Result:
        compiled = stmt.compile()
        params = compiled.params
        if "email_1" not in params and "id_1" not in params:
            # Fail loudly rather than return a misleading 401: SQLAlchemy assigns
            # these parameter names, and reworking the query renames them.
            raise AssertionError(f"FakeDb does not know this statement's criteria: {compiled}")

        # Only look at the WHERE clause: `select(User)` always lists the
        # `users.is_active` column in the SELECT list, so matching against the full
        # SQL would be constantly true — and the guard unverified again.
        enforces_active = "is_active" in str(stmt.whereclause)
        for user in self._users:
            hit = params.get("email_1") == user.email or str(params.get("id_1")) == str(user.id)
            if hit and (user.is_active or not enforces_active):
                return _Result(user)
        return _Result(None)


def make_user(role: str = "learner", is_active: bool = True) -> User:
    return User(
        id=uuid.uuid4(),
        email=EMAIL,
        hashed_password=PASSWORD_HASH,
        role=role,
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


def _client(db: FakeDb) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _login(client: AsyncClient, password: str = PASSWORD) -> Response:
    return await client.post("/auth/login", json={"email": EMAIL, "password": password})


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_login_issues_token_that_opens_protected_route() -> None:
    """AK 1: happy path — the protected route is reachable after login.

    `/auth/me` is the route the frontend calls right after login. That the token
    also works outside the auth router is checked by the e2e test against the
    running stack; in-process that would only prove another fake.
    """
    user = make_user()

    async with _client(FakeDb(user)) as client:
        login = await _login(client)
        assert login.status_code == 200
        token = login.json()["access_token"]

        me = await client.get("/auth/me", headers=_auth(token))
        assert me.status_code == 200
        assert me.json() == {"id": str(user.id), "email": EMAIL, "role": "learner"}


async def test_wrong_password_issues_no_token() -> None:
    """Counter-check to the happy path: no valid password, no token."""
    async with _client(FakeDb(make_user())) as client:
        r = await _login(client, password="wrong")

        assert r.status_code == 401
        assert "access_token" not in r.json()


@pytest.mark.parametrize("path", ["/auth/me", f"/documents/{MISSING_DOCUMENT_ID}"])
async def test_protected_route_without_token_returns_401(path: str) -> None:
    """Without a token the API answers 401 on protected routes.

    This is the API side of AK 2. The redirect to `/login` itself hangs on React
    state (`ProtectedRoute`), not on this status — it is checked in
    `frontend/src/auth.test.tsx`, not here.
    """
    async with _client(FakeDb(make_user())) as client:
        r = await client.get(path)

    assert r.status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        # Well-formed and unexpired, but signed with a foreign secret.
        jwt.encode(
            {"sub": str(uuid.uuid4()), "role": "admin"},
            "an-attackers-secret-that-is-long-enough",
            algorithm=settings.jwt_algorithm,
        ),
    ],
    ids=["malformed", "foreign-signature"],
)
async def test_protected_route_with_invalid_token_returns_401(token: str) -> None:
    async with _client(FakeDb(make_user())) as client:
        r = await client.get("/auth/me", headers=_auth(token))

    assert r.status_code == 401


async def test_token_of_unknown_user_returns_401() -> None:
    """A valid signature is not enough — the user must still exist on access."""
    token = create_access_token(str(uuid.uuid4()), "learner")

    async with _client(FakeDb(make_user())) as client:
        r = await client.get("/auth/me", headers=_auth(token))

    assert r.status_code == 401


async def test_deactivated_user_cannot_log_in() -> None:
    """A deactivated account gets no token — otherwise offboarding has no effect."""
    async with _client(FakeDb(make_user(is_active=False))) as client:
        r = await _login(client)

    assert r.status_code == 401


async def test_token_of_deactivated_user_returns_401() -> None:
    """Deactivation takes effect immediately, not once the token expires."""
    user = make_user(is_active=False)
    token = create_access_token(str(user.id), user.role)

    async with _client(FakeDb(user)) as client:
        r = await client.get("/auth/me", headers=_auth(token))

    assert r.status_code == 401


async def test_expired_token_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """The expiry (T-06: 1 h) is enforced on access, not merely set on issue."""
    user = make_user()
    monkeypatch.setattr(settings, "jwt_expire_hours", -1)
    expired = create_access_token(str(user.id), user.role)

    async with _client(FakeDb(user)) as client:
        r = await client.get("/auth/me", headers=_auth(expired))

    assert r.status_code == 401
