"""The API's startup guard (ADR-005, T-42).

`AsyncClient(transport=ASGITransport(app=app), ...)`, the pattern the rest of
the suite uses (`tests/test_admin_config.py` etc.), does not drive the ASGI
`lifespan` protocol -- httpx's transport only forwards `http` scope requests --
so a mismatch there would go untested even though every endpoint test passes.
`lifespan` is exercised directly here instead.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import settings
from app.exceptions import EmbeddingConfigError
from app.main import lifespan


def make_session(rows: list[tuple[str, str]]) -> Any:
    """A fake `AsyncSessionLocal` factory yielding one config snapshot."""
    result = MagicMock()
    result.all.return_value = rows
    db = AsyncMock()
    db.execute.return_value = result

    @asynccontextmanager
    async def session_factory() -> AsyncIterator[AsyncMock]:
        yield db

    return session_factory


async def test_lifespan_starts_on_a_matching_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embed_model", "text-embedding-3-small")
    monkeypatch.setattr(settings, "embed_dimensions", 1536)
    monkeypatch.setattr(
        "app.main.AsyncSessionLocal",
        make_session([("embed_model", "text-embedding-3-small"), ("embed_dimensions", "1536")]),
    )

    async with lifespan(None):  # type: ignore[arg-type]
        pass  # must not raise


async def test_lifespan_aborts_on_a_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embed_model", "bge-m3")
    monkeypatch.setattr(settings, "embed_dimensions", 1536)
    monkeypatch.setattr(
        "app.main.AsyncSessionLocal",
        make_session([("embed_model", "text-embedding-3-small"), ("embed_dimensions", "1536")]),
    )

    with pytest.raises(EmbeddingConfigError):
        async with lifespan(None):  # type: ignore[arg-type]
            pass
