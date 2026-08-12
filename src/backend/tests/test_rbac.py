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
from app.config import settings
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
    """Yield (served path, APIRoute) for every route the app exposes.

    FastAPI resolves included routers lazily behind an internal
    `_IncludedRouter` wrapper rather than copying their routes onto the app
    eagerly, so `app.routes` alone only ever shows routes declared directly
    on `app` (e.g. /health) plus one wrapper per `include_router` call.

    The wrapper's `effective_route_contexts()` is what the path has to come
    from: recursing into `.original_router.routes` and reading their own
    `.path` drops any `prefix=` passed to `include_router` itself. A router
    included as `include_router(v2, prefix="/v2")` serves /v2/foo while its
    route still calls itself /foo, and both checks below compare that path
    against the spec — they would fail on correct code and the assertion
    messages would send the next person to change the spec instead.
    """
    for route in routes:
        if isinstance(route, APIRoute):
            yield route.path, route
        elif hasattr(route, "original_router"):
            for context in route.effective_route_contexts():
                original = context.original_route
                if isinstance(original, APIRoute):
                    yield context.path, original


# The only routes the app serves that are not APIRoutes. FastAPI registers them
# through Starlette's add_route, so the spec checks below — which walk APIRoutes
# — cannot see them, and openapi.yaml does not describe them either: they are
# framework infrastructure, not API surface.
#
# They are named here rather than left to the isinstance filter, because that
# filter would just as silently swallow a future app.mount("/metrics") or
# app.add_route("/internal/reindex") — reachable through nginx, unauthenticated
# and undeclared, with the suite green.
FRAMEWORK_DOC_ROUTES = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def test_only_api_routes_and_known_framework_routes_are_served() -> None:
    """Nothing on app.routes reaches the network that the two checks below
    cannot see.

    Both of them walk APIRoute instances. Anything registered at the Starlette
    level is invisible to them, so it is enumerated here instead — and the docs
    routes are additionally tied to the flag that is supposed to control them.

    Known gap, top level only: a non-APIRoute registered on an *included*
    router sits behind the _IncludedRouter wrapper, which the comprehension
    below skips via `original_router` and which _iter_api_routes narrows to
    APIRoute again. Such a route is served, unauthenticated and undeclared,
    with all three conformance checks green. Accepted as a residual risk — it
    takes registering a route past FastAPI's decorators to get there. Do not
    read this test as covering it.
    """
    non_api = {
        getattr(route, "path", repr(route))
        for route in app.routes
        if not isinstance(route, APIRoute) and not hasattr(route, "original_router")
    }

    unexpected = non_api - FRAMEWORK_DOC_ROUTES
    assert not unexpected, (
        f"routes outside the spec checks: {sorted(unexpected)} -- an APIRoute is "
        "covered by the conformance checks, anything else (mount, websocket, "
        "add_route) is not and must be justified here"
    )

    docs_served = non_api & FRAMEWORK_DOC_ROUTES
    assert bool(docs_served) is settings.expose_api_docs, (
        f"docs routes {sorted(docs_served)} served with EXPOSE_API_DOCS="
        f"{settings.expose_api_docs} -- the flag must decide, not a default"
    )


def test_all_spec_protected_routes_require_auth() -> None:
    """T-07 AK 'alle geschuetzten Routen pruefen die korrekte Rolle' as a
    structural guarantee, checked in both directions:

    - every implemented route must be documented in openapi.yaml -- /health
      used to be allowlisted here and is declared since T-39, so no exception
      remains. Routes that are not APIRoutes are covered by
      test_only_api_routes_and_known_framework_routes_are_served above;
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
    for path, route in _iter_api_routes(app.routes):
        spec_path = "/api" + path
        operations = paths.get(spec_path)
        for method in route.methods:
            assert operations is not None and method.lower() in operations, (
                f"{method} {path} is not declared in openapi.yaml "
                f"({spec_path}) -- every route the app serves must be in the "
                "spec first (ADR-010). Add it there, then implement it."
            )
            op = operations[method.lower()]
            if op.get("security", default_security) == []:
                continue  # explicitly public per spec
            checked += 1
            assert _requires_get_current_user(route.dependant), (
                f"{method} {path} requires auth per openapi.yaml "
                f"({spec_path}) but has no get_current_user dependency"
            )

    assert checked >= 4, "expected at least the 4 currently known protected routes"


HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def test_every_declared_endpoint_is_implemented() -> None:
    """The other direction, and the reason there is no allowlist here either.

    Spec-first is not spec-only: a declared path that nobody serves is a 404 for
    the client generated from it, and the frontend cannot tell "not built yet"
    from "broken". A new endpoint therefore ships with at least a placeholder in
    the same PR -- see app/routers/query.py for the shape (auth dependency, 501,
    TODO naming the ticket).
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    implemented = {
        ("/api" + path, method.lower())
        for path, route in _iter_api_routes(app.routes)
        for method in route.methods
    }

    missing = sorted(
        f"{method.upper()} {path}"
        for path, operations in spec["paths"].items()
        for method in operations
        if method in HTTP_METHODS and (path, method) not in implemented
    )
    assert not missing, (
        "declared in openapi.yaml but not served by the app:\n  "
        + "\n  ".join(missing)
        + "\n\nAdd a placeholder route (501) in the same PR as the spec change."
    )
