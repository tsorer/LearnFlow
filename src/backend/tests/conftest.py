"""Shared fixtures for the backend test suite.

The state the tests share lives in module globals: the rate limiter's in-memory
window (`app.limiter`) and FastAPI's dependency overrides. Both outlive a single
test, so they are reset centrally here — otherwise a test's outcome depends on
which file it happens to sit in and what ran before it.
"""

from collections.abc import Iterator

import pytest

from app.limiter import limiter
from app.main import app


@pytest.fixture(autouse=True)
def _reset_state() -> Iterator[None]:
    limiter.reset()
    yield
    app.dependency_overrides.clear()
    limiter.reset()
