"""T-09: login flow end-to-end against the running stack.

This file deliberately sits outside `tests/` (`testpaths = ["tests"]` in
pyproject.toml) and therefore does not run with the unit suite, only via
`make e2e` or the CI job `e2e`. It talks through nginx to the real API container
and the real database — nothing is mocked.

That covers exactly the seams `tests/` cannot see by construction:
  * nginx's `/api` rewrite (the frontend calls `/api/auth/login`, FastAPI listens
    on `/auth/login`),
  * the SPA fallback (a reload on `/login` must serve `index.html`, otherwise the
    redirect from AK 2 ends in a 404),
  * the real bcrypt hash from the `users` table instead of a fixture.

Precondition: a running stack with seeded users (`make up && make seed`).
"""

import os
import uuid
from collections.abc import Iterator

import httpx
import pytest

# The default is the service name on the edge network: the test runs inside the
# api container and reaches nginx at http://webapp — identical locally and in CI.
BASE_URL = os.environ.get("E2E_BASE_URL", "http://webapp")

# Seed user from seed_users.py. These are throwaway credentials of a throwaway
# stack (CI container or local development environment).
EMAIL = "lara@learnflow.local"
PASSWORD = "changeme6"
ROLE = "learner"

# Fixed instead of uuid4(): the value ends up in the test id, which must stay
# stable across runs (--last-failed, flakiness history in CI).
MISSING_DOCUMENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ff")


@pytest.fixture(scope="module")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def login(client: httpx.Client) -> httpx.Response:
    """The only login of this module.

    /auth/login is limited to 5 attempts per minute and IP (app/limiter.py), and
    the counter lives in the running api process — so the window outlives the test
    run. At one login per run that allows five runs per minute; adding further
    logins here shortens that accordingly.
    """
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 429:
        pytest.fail(
            "Rate limit exhausted (5 logins/minute/IP). The window outlives the "
            "test run: wait a minute or run `docker compose restart api`."
        )
    return r


@pytest.fixture(scope="module")
def token(login: httpx.Response) -> str:
    assert login.status_code == 200, login.text
    return str(login.json()["access_token"])


def test_root_serves_the_spa(client: httpx.Client) -> None:
    r = client.get("/")

    assert r.status_code == 200
    assert '<div id="root">' in r.text


def test_deep_link_to_login_serves_the_spa(client: httpx.Client) -> None:
    """A reload on /login must not 404 — otherwise the redirect from AK 2 leads
    nowhere in production."""
    r = client.get("/login")

    assert r.status_code == 200
    assert '<div id="root">' in r.text


def test_login_returns_token_and_role(login: httpx.Response) -> None:
    """AK 1, first part: login through nginx against the real users table."""
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["access_token"]
    assert body["role"] == ROLE


def test_token_opens_protected_route(client: httpx.Client, token: str) -> None:
    """AK 1, second part: the token makes the protected route reachable."""
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200
    assert r.json()["email"] == EMAIL
    assert r.json()["role"] == ROLE


def test_token_is_accepted_outside_the_auth_router(client: httpx.Client, token: str) -> None:
    """403 rather than 401: authentication works, but the route requires knowledge_owner
    (T-14) and this token's role is learner.

    Shows that the token and the /api rewrite also work for business routes, not just
    for the auth router's own endpoint — and that the role from a real token reaches
    require_role, not just the unit-mocked dependency in tests/test_documents.py.
    """
    r = client.get(
        f"/api/documents/{MISSING_DOCUMENT_ID}", headers={"Authorization": f"Bearer {token}"}
    )

    assert r.status_code == 403


@pytest.mark.parametrize("path", ["/api/auth/me", f"/api/documents/{MISSING_DOCUMENT_ID}"])
def test_protected_route_without_token_returns_401(client: httpx.Client, path: str) -> None:
    """Without a token the API answers 401 on protected routes.

    This is the API side of AK 2. The redirect to `/login` hangs on React state
    (`ProtectedRoute`), not on this status — it is checked in
    `frontend/src/auth.test.tsx`, not here.
    """
    r = client.get(path)

    assert r.status_code == 401
