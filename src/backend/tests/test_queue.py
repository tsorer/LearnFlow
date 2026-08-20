"""Unit tests for the enqueue_document helper."""

import json
from unittest.mock import AsyncMock

from app.queue import enqueue_document


def statements(db: AsyncMock) -> list[tuple[str, dict]]:
    return [(str(call[0][0]), call[0][1]) for call in db.execute.call_args_list]


async def test_enqueue_document_inserts_the_job() -> None:
    db = AsyncMock()

    await enqueue_document(db, "doc-123")

    inserts = [(sql, params) for sql, params in statements(db) if "INSERT INTO pgqueuer" in sql]
    assert len(inserts) == 1
    assert json.loads(inserts[0][1]["payload"]) == {"document_id": "doc-123"}


async def test_enqueue_document_drops_a_still_queued_job_for_the_same_document() -> None:
    """T-15: replacing a document that has not been picked up yet would leave
    its predecessor's job in the queue — a second full embedding run over the
    same content. Only 'queued' rows may go; 'picked' means a worker is on it.
    """
    db = AsyncMock()

    await enqueue_document(db, "doc-123")

    deletes = [(sql, params) for sql, params in statements(db) if "DELETE FROM pgqueuer" in sql]
    assert len(deletes) == 1
    sql, params = deletes[0]
    assert "status = 'queued'" in sql
    assert json.loads(params["payload"]) == {"document_id": "doc-123"}
    # The delete has to run before the insert, or it removes the job it just wrote.
    assert [i for i, (s, _) in enumerate(statements(db)) if "DELETE FROM pgqueuer" in s] < [
        i for i, (s, _) in enumerate(statements(db)) if "INSERT INTO pgqueuer" in s
    ]


async def test_enqueue_document_does_not_notify_itself() -> None:
    """Notification is the job of the tg_pgqueuer_changed trigger (migration
    0001). A hand-written pg_notify sends a payload the listener cannot parse."""
    db = AsyncMock()

    await enqueue_document(db, "doc-123")

    assert all("pg_notify" not in str(call[0][0]) for call in db.execute.call_args_list)
