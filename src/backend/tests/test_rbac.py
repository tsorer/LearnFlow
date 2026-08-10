"""End-to-end RBAC tests (T-07).

Unlike test_documents.py's role tests (which bypass auth via
`app.dependency_overrides[get_current_user]`), these tests send real bearer
tokens through the actual HTTP stack and exercise the real
`get_current_user` / `decode_token` / `HTTPBearer` code path. Only `get_db`
is mocked, so the JWT decoding, expiry check, and role check are all real.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from openapi_spec_validator.readers import read_from_filename

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.database import get_db
from app.main import app
from app.models.tables import User

SPEC_PATH = Path(__file__).parent.parent / "openapi.yaml"


def make_active_user_db(user_id: str, role: str = "learner") -> AsyncMock:
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
    return create_access_token(subject, role, expires_delta=timedelta(hours=-1))


# ---- /auth/me ----------------------------------------------------------


async def test_me_without_token_returns_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_with_garbage_token_returns_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


async def test_me_with_non_uuid_subject_returns_401() -> None:
    """A validly-signed token whose `sub` isn't a UUID must still be treated
    as an invalid token (401), not reach the DB query and blow up as a 500 --
    User.id is a UUID column, and asyncpg raises an unhandled DataError for a
    malformed UUID literal if the subject is passed through unvalidated."""
    token = create_access_token("not-a-uuid", "learner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_me_with_expired_token_returns_401() -> None:
    user_id = str(uuid4())
    token = expired_token(user_id, "learner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_me_with_valid_token_returns_200() -> None:
    user_id = str(uuid4())
    app.dependency_overrides[get_db] = lambda: make_active_user_db(user_id, "learner")
    token = create_access_token(user_id, "learner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["id"] == user_id


# ---- /auth/logout -------------------------------------------------------


async def test_logout_without_token_returns_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/auth/logout")
    assert r.status_code == 401


async def test_logout_with_garbage_token_returns_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/auth/logout", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


async def test_logout_with_expired_token_returns_401() -> None:
    user_id = str(uuid4())
    token = expired_token(user_id, "learner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_logout_with_valid_token_returns_204_with_empty_body() -> None:
    user_id = str(uuid4())
    app.dependency_overrides[get_db] = lambda: make_active_user_db(user_id, "learner")
    token = create_access_token(user_id, "learner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
    assert r.content == b""


# ---- POST /documents (role-gated) ---------------------------------------


async def test_documents_post_without_token_returns_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/documents", files={"file": ("a.pdf", b"x", "application/pdf")})
    assert r.status_code == 401


async def test_documents_post_with_wrong_role_returns_403() -> None:
    user_id = str(uuid4())
    app.dependency_overrides[get_db] = lambda: make_active_user_db(user_id, "learner")
    token = create_access_token(user_id, "learner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
    db = make_active_user_db(user_id, "knowledge_owner")
    db.add = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    token = create_access_token(user_id, "knowledge_owner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("a.pdf", b"x", "application/pdf")},
        )
    assert r.status_code not in (401, 403)


# ---- structural: every spec-protected route actually enforces auth ------


def _requires_get_current_user(dependant: Dependant) -> bool:
    return any(
        sub.call is get_current_user or _requires_get_current_user(sub)
        for sub in dependant.dependencies
    )


def _iter_api_routes(routes: list[Any]) -> Any:
    """Flatten app.routes into APIRoute leaves.

    FastAPI resolves included routers lazily behind an internal
    `_IncludedRouter` wrapper rather than copying their routes onto the app
    eagerly, so `app.routes` alone only ever shows routes declared directly
    on `app` (e.g. /health) plus one wrapper per `include_router` call. The
    wrapper exposes the sub-router as `.original_router`, which is the
    documented-enough seam to recurse through.
    """
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):
            yield from _iter_api_routes(route.original_router.routes)


# Routes that intentionally live outside openapi.yaml (ADR-010 covers the
# public API surface, not infra endpoints like health checks) and are not
# auth-gated by design. Anything not in openapi.yaml and not listed here
# fails the structural check below instead of silently passing through it.
PUBLIC_NON_SPEC_ROUTES = {("GET", "/health")}


def test_all_spec_protected_routes_require_auth() -> None:
    """T-07 AK 'alle geschuetzten Routen pruefen die korrekte Rolle' as a
    structural guarantee, checked in both directions:

    - every implemented route must be either documented in openapi.yaml or
      explicitly allowlisted as intentionally public and undocumented
      (PUBLIC_NON_SPEC_ROUTES) -- otherwise a route missing from both would
      be invisible to this check entirely, e.g. a new endpoint that is
      neither added to the spec nor given an auth dependency;
    - every documented route that isn't explicitly public (`security: []`)
      must carry get_current_user (or a dependency built on it, e.g.
      require_role) somewhere in its FastAPI dependency tree.

    This only verifies that *some* authenticated user is required, not that
    the *correct* role is -- openapi.yaml states role requirements as prose
    in a response description, not as a machine-checkable field, so the
    finer-grained role check for e.g. POST /documents still lives in
    test_documents_post_with_wrong_role_returns_403 above.
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    default_security = spec.get("security", [])
    paths: dict[str, Any] = spec["paths"]

    checked = 0
    for route in _iter_api_routes(app.routes):
        spec_path = "/api" + route.path
        operations = paths.get(spec_path)
        for method in route.methods:
            if (method, route.path) in PUBLIC_NON_SPEC_ROUTES:
                continue
            assert operations is not None and method.lower() in operations, (
                f"{method} {route.path} is not declared in openapi.yaml "
                f"({spec_path}) and is not in PUBLIC_NON_SPEC_ROUTES -- every "
                "route must be either documented (so the auth check below "
                "applies to it) or explicitly allowlisted as intentionally public"
            )
            op = operations[method.lower()]
            if op.get("security", default_security) == []:
                continue  # explicitly public per spec
            checked += 1
            assert _requires_get_current_user(route.dependant), (
                f"{method} {route.path} requires auth per openapi.yaml "
                f"({spec_path}) but has no get_current_user dependency"
            )

    assert checked >= 4, "expected at least the 4 currently known protected routes"
