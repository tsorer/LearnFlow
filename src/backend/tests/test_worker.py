import inspect
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pgqueuer.models import Job

from app.services.parsing import MARKDOWN_CONTENT_TYPE
from worker.main import make_job_handler, process_document, read_chunk_config

MARKDOWN = b"# Titel\n\nErster Absatz.\n\nZweiter Absatz."


@pytest.fixture(autouse=True)
def fake_tokenizer(monkeypatch: pytest.MonkeyPatch) -> None:
    """One word = one token — keeps the suite independent of tiktoken's BPE download."""
    monkeypatch.setattr("worker.main.count_tokens", lambda text: len(text.split()))


def make_job(document_id: str) -> Job:
    now = datetime.now(UTC)
    return Job(
        id=1,
        priority=0,
        created=now,
        updated=now,
        heartbeat=now,
        execute_after=now,
        status="picked",
        entrypoint="process_document",
        payload=json.dumps({"document_id": document_id}).encode(),
        queue_manager_id=None,
        headers=None,
    )


def make_conn(
    content: bytes = MARKDOWN,
    content_type: str = MARKDOWN_CONTENT_TYPE,
    config: Sequence[tuple[str, str]] = (("chunk_size", "512"), ("chunk_overlap", "64")),
) -> AsyncMock:
    conn = AsyncMock()
    # transaction() is a sync call returning an async context manager.
    conn.transaction = MagicMock(return_value=AsyncMock())
    conn.fetchrow.return_value = {"content": content, "content_type": content_type}
    conn.fetch.return_value = [{"key": key, "value": value} for key, value in config]
    return conn


def executed(conn: AsyncMock) -> list[tuple[Any, ...]]:
    return [call.args for call in conn.execute.await_args_list]


async def test_process_document_writes_chunks_and_marks_available() -> None:
    document_id = str(uuid.uuid4())
    conn = make_conn()

    await process_document(conn, make_job(document_id))

    assert executed(conn)[0] == (
        "UPDATE documents SET status = 'processing' WHERE id = $1",
        document_id,
    )

    sql, rows = conn.executemany.await_args.args
    assert "INSERT INTO chunks" in sql
    # Heading and content share the index; coalesce keeps PDF chunks (heading
    # NULL) from producing a NULL tsv.
    assert "to_tsvector('german', coalesce($6, '') || ' ' || $3)" in sql
    assert len(rows) == 1
    chunk_id, doc_id, text, index, page, heading = rows[0]
    # chunks.id has no server default — the worker supplies it.
    assert uuid.UUID(chunk_id)
    assert (doc_id, text, index, page, heading) == (
        document_id,
        "Erster Absatz.\n\nZweiter Absatz.",
        0,
        None,
        "Titel",
    )

    assert executed(conn)[-1] == (
        "UPDATE documents SET status = 'available', chunk_count = $2, "
        "error_message = NULL WHERE id = $1",
        document_id,
        1,
    )


async def test_process_document_replaces_previous_chunks() -> None:
    document_id = str(uuid.uuid4())
    conn = make_conn()

    await process_document(conn, make_job(document_id))

    assert ("DELETE FROM chunks WHERE document_id = $1", document_id) in executed(conn)


async def test_chunk_parameters_come_from_config() -> None:
    document_id = str(uuid.uuid4())
    body = " ".join(f"Satz nummer {i} mit sechs Wörtern." for i in range(1, 6))
    conn = make_conn(
        content=f"# Titel\n\n{body}".encode(),
        config=(("chunk_size", "8"), ("chunk_overlap", "0")),
    )

    await process_document(conn, make_job(document_id))

    _, rows = conn.executemany.await_args.args
    assert len(rows) > 1
    assert [row[3] for row in rows] == list(range(len(rows)))


async def test_process_document_without_extractable_text_fails() -> None:
    document_id = str(uuid.uuid4())
    conn = make_conn(content=b"   \n\n  ")

    with pytest.raises(ValueError):
        await process_document(conn, make_job(document_id))

    conn.executemany.assert_not_awaited()
    assert executed(conn)[-1] == (
        "UPDATE documents SET status = 'failed', error_message = $2 WHERE id = $1",
        document_id,
        "Kein extrahierbarer Text gefunden",
    )


def test_job_handler_is_a_coroutine_function() -> None:
    """pgqueuer decides via iscoroutinefunction() whether to await the
    entrypoint. Registering a lambda made every job report success without ever
    running — this guards the shape of the handler, not just its body.
    """
    assert inspect.iscoroutinefunction(make_job_handler(AsyncMock()))


async def test_job_handler_uses_a_pooled_connection() -> None:
    """Jobs must not share the QueueManager's connection — asyncpg forbids
    concurrent operations on one connection (two parallel uploads).
    """
    job_conn = make_conn()
    # acquire() is a sync call returning an async context manager.
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=job_conn)))

    await make_job_handler(pool)(make_job(str(uuid.uuid4())))

    pool.acquire.assert_called_once()
    job_conn.executemany.assert_awaited_once()


async def test_process_document_sets_failed_for_missing_document() -> None:
    document_id = str(uuid.uuid4())
    conn = make_conn()
    conn.fetchrow.return_value = None

    with pytest.raises(ValueError):
        await process_document(conn, make_job(document_id))

    assert executed(conn)[-1] == (
        "UPDATE documents SET status = 'failed', error_message = $2 WHERE id = $1",
        document_id,
        f"Dokument {document_id} nicht gefunden",
    )


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ((("chunk_size", "256"), ("chunk_overlap", "32")), (256, 32)),
        ((), (512, 64)),  # ADR-007 defaults when the config rows are missing
    ],
)
async def test_read_chunk_config(
    config: Sequence[tuple[str, str]], expected: tuple[int, int]
) -> None:
    conn = make_conn(config=config)

    assert await read_chunk_config(conn) == expected
