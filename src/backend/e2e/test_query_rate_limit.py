"""T-45: the rate limit on POST /api/query, end-to-end against the running stack.

`tests/test_rate_limit.py` already pins the policy against the ASGI app. What
only this file can see is the path the browser takes: through nginx, where the
`/api` prefix is stripped, and into the real api process, whose counter is a
module global rather than a fixture — the seam where a limiter that works in a
test client can still be missing in the deployed app.

What the pre-limit questions answer with is deliberately not asserted. With a
real provider key they come back as suppressed answers (no chunk clears the
retrieval gate for a question this far outside the corpus, so nothing reaches
the LLM); in CI the key is a dummy and they come back 503. Both count towards
the limit, which is the property under test.

Precondition: a running stack with seeded users (`make up && make seed`).
"""

import os
from collections.abc import Iterator

import httpx
import pytest

from app.routers.query import QUERY_RATE_LIMIT

BASE_URL = os.environ.get("E2E_BASE_URL", "http://webapp")

# Seed user from seed_users.py — a learner, which is all this needs.
EMAIL = "lara@learnflow.local"
PASSWORD = "changeme6"

LIMIT = int(QUERY_RATE_LIMIT.split("/")[0])


@pytest.fixture(scope="module")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def token(client: httpx.Client) -> str:
    """The only login of this module — the fourth in the e2e suite.

    /auth/login allows 5 per minute and IP and the counter outlives the run, so
    the number of logging-in modules is the number of runs that fit in a minute
    (see test_login_flow.py).
    """
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 429:
        pytest.fail(
            "Rate limit exhausted (5 logins/minute/IP). The window outlives the "
            "test run: wait a minute or run `docker compose restart api`."
        )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def test_the_question_past_the_limit_is_refused(client: httpx.Client, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    statuses = []

    for i in range(LIMIT + 1):
        r = client.post(
            "/api/query",
            json={"question": f"Frage {i} ausserhalb des Korpus zum Zaehlerstand?"},
            headers=headers,
        )
        statuses.append(r.status_code)
        if r.status_code == 429:
            break

    # Not "exactly the eleventh": the window lives in the api process and a run
    # started within a minute of the previous one inherits its count. What must
    # hold either way is that the limit bites, and no later than one over it.
    assert 429 in statuses, f"no request was refused within {LIMIT + 1} attempts: {statuses}"
    assert len(statuses) <= LIMIT + 1
    assert r.json() == {
        "detail": "Zu viele Anfragen. Bitte warte einen Moment und versuche es erneut."
    }
