"""Unit tests for the enqueue_document helper."""

import json
from unittest.mock import AsyncMock

from app.queue import enqueue_document


async def test_enqueue_document_inserts_the_job() -> None:
    db = AsyncMock()

    await enqueue_document(db, "doc-123")

    assert db.execute.call_count == 1
    sql, params = db.execute.call_args_list[0][0]
    assert "INSERT INTO pgqueuer" in str(sql)
    assert json.loads(params["payload"]) == {"document_id": "doc-123"}


async def test_enqueue_document_does_not_notify_itself() -> None:
    """Notification is the job of the tg_pgqueuer_changed trigger (migration
    0001). A hand-written pg_notify sends a payload the listener cannot parse."""
    db = AsyncMock()

    await enqueue_document(db, "doc-123")

    assert all("pg_notify" not in str(call[0][0]) for call in db.execute.call_args_list)
