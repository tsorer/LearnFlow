"""T-37: PUT /admin/config against the running stack.

Covers what tests/test_admin_config.py's mocked db cannot show: that
mutating the attached ORM object and committing really does flush an UPDATE
against the real table, and that the deferred band-order trigger (migration
0009, issue #73) is reachable through this HTTP endpoint -- not just through
direct SQL, which is all e2e/test_config_threshold_constraints.py exercises.

Precondition: a running stack (`make up && make seed`).
"""

import os
from collections.abc import Iterator

import httpx
import pytest

# Same rationale as e2e/test_login_flow.py: the test runs inside the api
# container and reaches nginx at http://webapp, identical locally and in CI.
BASE_URL = os.environ.get("E2E_BASE_URL", "http://webapp")

# Seed user from seed_users.py -- the only admin among the seeded accounts.
EMAIL = "niklaus@learnflow.local"
PASSWORD = "changeme2"

HIGH = "confidence_threshold_high"
MEDIUM = "confidence_threshold_medium"
# The seeded start values (migration 0008) -- restored after every test that
# changes them, so this module leaves the stack the way it found it for
# whichever e2e module runs next.
SEEDED_HIGH = "0.75"
SEEDED_MEDIUM = "0.45"


@pytest.fixture(scope="module")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def headers(client: httpx.Client) -> dict[str, str]:
    """The only login of this module -- see test_login_flow.py's `login`
    fixture for why that matters (5 logins/minute/IP, counter outlives the
    run)."""
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 429:
        pytest.fail(
            "Rate limit exhausted (5 logins/minute/IP). The window outlives the "
            "test run: wait a minute or run `docker compose restart api`."
        )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def restore_thresholds(client: httpx.Client, headers: dict[str, str]) -> Iterator[None]:
    """Every test below may leave the two confidence thresholds changed.
    Restoring them here, once per test, keeps the tests independent of each
    other's outcome and leaves the seeded defaults intact afterwards."""
    yield
    r = client.put(
        "/api/admin/config",
        headers=headers,
        json={"config": {HIGH: SEEDED_HIGH, MEDIUM: SEEDED_MEDIUM}},
    )
    assert r.status_code == 200, r.text


def test_get_returns_the_seeded_confidence_thresholds(
    client: httpx.Client, headers: dict[str, str]
) -> None:
    r = client.get("/api/admin/config", headers=headers)

    assert r.status_code == 200
    assert HIGH in r.json()["config"]


def test_put_writes_a_real_threshold_and_it_is_visible_immediately(
    client: httpx.Client, headers: dict[str, str]
) -> None:
    """Proves the ORM-mutate-then-commit write path actually flushes an
    UPDATE against the real table -- tests/test_admin_config.py only asserts
    this against a mock db."""
    r = client.put("/api/admin/config", headers=headers, json={"config": {HIGH: "0.80"}})

    assert r.status_code == 200, r.text
    assert r.json()["config"][HIGH] == "0.80"

    r2 = client.get("/api/admin/config", headers=headers)
    assert r2.json()["config"][HIGH] == "0.80"


def test_put_band_order_violation_returns_422_with_a_readable_message(
    client: httpx.Client, headers: dict[str, str]
) -> None:
    """PUT `high` below the current `medium` -- valid per this endpoint's own
    per-key shape check, only the deferred cross-row trigger catches it, at
    commit."""
    setup = client.put(
        "/api/admin/config", headers=headers, json={"config": {HIGH: "0.60", MEDIUM: "0.60"}}
    )
    assert setup.status_code == 200, setup.text

    r = client.put("/api/admin/config", headers=headers, json={"config": {HIGH: "0.50"}})

    assert r.status_code == 422, r.text
    assert "darf nicht über" in r.json()["detail"]

    # The violating write must not have gone through.
    r2 = client.get("/api/admin/config", headers=headers)
    assert r2.json()["config"][HIGH] == "0.60"


def test_put_unchanged_non_writable_key_passes_through(
    client: httpx.Client, headers: dict[str, str]
) -> None:
    """The round-trip fix from the PR review: an admin UI that sends GET's
    whole response back through PUT must not have every save rejected just
    because it echoes a non-writable key it never touched."""
    current = client.get("/api/admin/config", headers=headers).json()["config"]

    r = client.put(
        "/api/admin/config",
        headers=headers,
        json={"config": {**current, HIGH: "0.80"}},
    )

    assert r.status_code == 200, r.text
    assert r.json()["config"][HIGH] == "0.80"
