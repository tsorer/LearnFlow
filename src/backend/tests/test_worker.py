import inspect
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pgqueuer.models import Job

from app.exceptions import UserFacingError
from app.models.tables import DocumentStatus
from app.services.parsing import MARKDOWN_CONTENT_TYPE
from worker.main import Superseded, make_job_handler, process_document, read_chunk_config

MARKDOWN = b"# Titel\n\nErster Absatz.\n\nZweiter Absatz."


# The document's updated_at, which a run carries as its version token: read
# together with the content, it has to match again before anything is published
# (T-15 — an upload replacing the document in between moves it).
VERSION = datetime(2026, 8, 19, 8, 0, tzinfo=UTC)

# The failed-update carries the same token, so a run that fails after a
# replacement cannot report its failure on the new version.
FAILED_UPDATE = (
    "UPDATE documents SET status = $4, error_message = $2 "
    "WHERE id = $1 AND updated_at = $3"
)


@pytest.fixture(autouse=True)
def fake_tokenizer(monkeypatch: pytest.MonkeyPatch) -> None:
    """One word = one token — keeps the suite independent of tiktoken's BPE download."""
    monkeypatch.setattr("worker.main.count_tokens", lambda text: len(text.split()))


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may reach the embedding provider — CI runs with a dummy API key.
    The n-th chunk gets the vector [n, 0.5], so tests can assert which vector
    ended up on which chunk, not merely that one is present.
    """

    async def embed(texts: list[str]) -> list[list[float]]:
        return [[float(i), 0.5] for i in range(len(texts))]

    monkeypatch.setattr("worker.main.embed_texts", embed)


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
    version: datetime = VERSION,
) -> AsyncMock:
    conn = AsyncMock()
    # transaction() is a sync call returning an async context manager.
    conn.transaction = MagicMock(return_value=AsyncMock())
    conn.fetchrow.return_value = {
        "content": content,
        "content_type": content_type,
        "updated_at": version,
    }
    conn.fetch.return_value = [{"key": key, "value": value} for key, value in config]
    return conn


def executed(conn: AsyncMock) -> list[tuple[Any, ...]]:
    return [call.args for call in conn.execute.await_args_list]


async def test_process_document_writes_chunks_and_marks_available() -> None:
    document_id = str(uuid.uuid4())
    conn = make_conn()

    await process_document(conn, make_job(document_id))

    assert executed(conn)[0] == (
        "UPDATE documents SET status = $2 WHERE id = $1",
        document_id,
        DocumentStatus.processing,
    )

    sql, rows = conn.executemany.await_args.args
    assert "INSERT INTO chunks" in sql
    # Heading and content share the index; coalesce keeps PDF chunks (heading
    # NULL) from producing a NULL tsv.
    assert "to_tsvector('german', coalesce($6, '') || ' ' || $3)" in sql
    assert len(rows) == 1
    chunk_id, doc_id, text, index, page, heading, _embedding = rows[0]
    # chunks.id has no server default — the worker supplies it.
    assert uuid.UUID(chunk_id)
    assert (doc_id, text, index, page, heading) == (
        document_id,
        "Erster Absatz.\n\nZweiter Absatz.",
        0,
        None,
        "Titel",
    )

    assert conn.fetchval.await_args.args == (
        "UPDATE documents SET status = $4, chunk_count = $2, "
        "error_message = NULL WHERE id = $1 AND updated_at = $3 RETURNING id",
        document_id,
        1,
        VERSION,
        DocumentStatus.available,
    )


async def test_a_document_replaced_while_indexing_is_not_published() -> None:
    """T-15's race: an upload replaces the document while this job is embedding.

    The chunks this run wrote belong to the version the upload just discarded,
    and the replacement enqueued a job of its own. Publishing here would put the
    superseded content back into the index under a document the owner has
    already replaced — with nothing anywhere to notice it by. The guarded UPDATE
    matches no row, and unwinding the transaction takes the chunks with it.
    """
    document_id = str(uuid.uuid4())
    conn = make_conn()
    # No row left carrying the updated_at this run read.
    conn.fetchval.return_value = None

    await process_document(conn, make_job(document_id))

    # The guarded publish ran and matched nothing, and the transaction was left
    # through the exception — which is what discards the chunks written in it.
    # Asserting on the exit rather than on "no chunks written": the writes
    # happen, the rollback is what takes them back.
    assert conn.fetchval.await_count == 1
    assert conn.transaction.return_value.__aexit__.await_args.args[0] is Superseded
    # And it is not an error: the replacement's job owns the index now, so
    # nothing marks this document failed.
    assert DocumentStatus.failed not in [arg for call in executed(conn) for arg in call]


async def test_the_version_read_with_the_content_is_the_one_published() -> None:
    """The token has to come from the same read as the content. Taken from a
    second query, an upload landing between the two would leave the run indexing
    the old bytes under the new version's token — and publishing them."""
    document_id = str(uuid.uuid4())
    conn = make_conn(version=datetime(2026, 8, 19, 9, 30, tzinfo=UTC))

    await process_document(conn, make_job(document_id))

    assert "updated_at" in conn.fetchrow.await_args.args[0]
    assert conn.fetchval.await_args.args[3] == datetime(2026, 8, 19, 9, 30, tzinfo=UTC)


@pytest.mark.parametrize("failing_step", ["embedding", "chunk config", "chunking"])
async def test_every_failure_after_the_read_reports_on_the_version_it_read(
    failing_step: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Counterpart on the error path: the failure belongs to the version this
    run read, whatever it was that failed.

    Reported without the version condition, a run that fails after the document
    was replaced flips a row to 'failed' that the replacement's job has by then
    indexed successfully — and fail-closed retrieval (ADR-008) drops it from
    every answer, with no error anywhere to notice it by.

    Parametrised over where it goes wrong, because that is what the review on
    #87 caught: the version used to come out of the chunking, so only failures
    *after* it — the embedding — were covered, while the two inside it silently
    fell back to matching the row by id alone.
    """
    document_id = str(uuid.uuid4())
    conn = make_conn()

    if failing_step == "embedding":

        async def fail(texts: list[str]) -> list[list[float]]:
            raise UserFacingError("Embedding hat 3 statt 1536 Dimensionen")

        monkeypatch.setattr("worker.main.embed_texts", fail)
    elif failing_step == "chunk config":
        conn = make_conn(config=(("chunk_size", "fünfhundert"), ("chunk_overlap", "64")))
    else:
        conn = make_conn(content=b"   \n\n  ")

    with pytest.raises(UserFacingError):
        await process_document(conn, make_job(document_id))

    sql, _, _, version, _ = executed(conn)[-1]
    assert sql == FAILED_UPDATE
    assert version == VERSION


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


async def test_stores_one_embedding_per_chunk() -> None:
    document_id = str(uuid.uuid4())
    body = " ".join(f"Satz nummer {i} mit sechs Wörtern." for i in range(1, 6))
    conn = make_conn(
        content=f"# Titel\n\n{body}".encode(),
        config=(("chunk_size", "8"), ("chunk_overlap", "0")),
    )

    await process_document(conn, make_job(document_id))

    sql, rows = conn.executemany.await_args.args
    # Bound as text and cast in Postgres — asyncpg has no codec for `vector`.
    assert "embedding" in sql
    assert "$7::text::vector" in sql
    # Vectors keep their chunk's position; a mix-up here would show up as wrong
    # citations at query time, not as an error.
    assert [json.loads(row[6]) for row in rows] == [[float(i), 0.5] for i in range(len(rows))]


async def test_embedding_runs_before_the_transaction_opens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole point of the split: seconds of HTTP must not happen inside an
    open transaction, where they would block VACUUM on chunks.
    """
    conn = make_conn()
    open_transactions: list[int] = []

    async def embed(texts: list[str]) -> list[list[float]]:
        open_transactions.append(conn.transaction.call_count)
        return [[0.0, 0.5] for _ in texts]

    monkeypatch.setattr("worker.main.embed_texts", embed)

    await process_document(conn, make_job(str(uuid.uuid4())))

    assert open_transactions == [0]


async def test_embedding_failure_marks_the_document_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = str(uuid.uuid4())
    conn = make_conn()

    # Shaped like a real provider error: an auth failure echoes a fragment of
    # the key, and the whole string would otherwise reach the API client.
    secret = "AuthenticationError: Incorrect API key provided: sk-proj-abc***XYZ (api_base: ...)"

    async def fail(texts: list[str]) -> list[list[float]]:
        raise RuntimeError(secret)

    monkeypatch.setattr("worker.main.embed_texts", fail)

    with pytest.raises(RuntimeError):
        await process_document(conn, make_job(document_id))

    # Nothing was written, so the previous index of this document survives.
    conn.executemany.assert_not_awaited()
    assert ("DELETE FROM chunks WHERE document_id = $1", document_id) not in executed(conn)
    assert executed(conn)[-1] == (
        FAILED_UPDATE,
        document_id,
        "Verarbeitung fehlgeschlagen",
        VERSION,
        DocumentStatus.failed,
    )
    # documents.error_message is served to every knowledge_owner and admin by
    # GET /documents — nothing from the provider may end up in it.
    assert not any(secret in str(call) for call in executed(conn))


async def test_foreign_error_deriving_from_valueerror_stays_out_of_error_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gap T-44 closes: until now the worker decided by isinstance(exc,
    ValueError), so a dependency whose error type happens to derive from
    ValueError would have had its message served to every knowledge_owner.
    Nothing enforced that assumption across dependency upgrades — only the
    exception type we raise ourselves may reach error_message.
    """
    document_id = str(uuid.uuid4())
    conn = make_conn()

    class ProviderError(ValueError):
        """Shaped like a third-party error that inherits from ValueError."""

    secret = "Incorrect API key provided: sk-proj-abc***XYZ (api_base: https://eu.example)"

    async def fail(texts: list[str]) -> list[list[float]]:
        raise ProviderError(secret)

    monkeypatch.setattr("worker.main.embed_texts", fail)

    with pytest.raises(ProviderError):
        await process_document(conn, make_job(document_id))

    assert executed(conn)[-1] == (
        FAILED_UPDATE,
        document_id,
        "Verarbeitung fehlgeschlagen",
        VERSION,
        DocumentStatus.failed,
    )
    assert not any(secret in str(call) for call in executed(conn))


async def test_user_facing_error_reaches_error_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Counterpart to the test above: the allowed path still carries its text."""
    document_id = str(uuid.uuid4())
    conn = make_conn()

    async def fail(texts: list[str]) -> list[list[float]]:
        raise UserFacingError("Embedding hat 3 statt 1536 Dimensionen")

    monkeypatch.setattr("worker.main.embed_texts", fail)

    with pytest.raises(UserFacingError):
        await process_document(conn, make_job(document_id))

    assert executed(conn)[-1] == (
        FAILED_UPDATE,
        document_id,
        "Embedding hat 3 statt 1536 Dimensionen",
        VERSION,
        DocumentStatus.failed,
    )


async def test_process_document_without_extractable_text_fails() -> None:
    document_id = str(uuid.uuid4())
    conn = make_conn(content=b"   \n\n  ")

    with pytest.raises(UserFacingError):
        await process_document(conn, make_job(document_id))

    conn.executemany.assert_not_awaited()
    assert executed(conn)[-1] == (
        FAILED_UPDATE,
        document_id,
        "Kein extrahierbarer Text gefunden",
        VERSION,
        DocumentStatus.failed,
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

    with pytest.raises(UserFacingError):
        await process_document(conn, make_job(document_id))

    assert executed(conn)[-1] == (
        FAILED_UPDATE,
        document_id,
        f"Dokument {document_id} nicht gefunden",
        None,
        DocumentStatus.failed,
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


async def test_non_numeric_chunk_config_fails_with_a_configuration_message() -> None:
    """config.value is a plain Text column and nothing validates it on write
    (PUT /admin/config is a T-37 placeholder), so a non-numeric value is
    reachable. It must read like the range checks in chunk_blocks rather than
    like Python's int() — and not fall back to the default, which would index
    the corpus with parameters nobody configured."""
    document_id = str(uuid.uuid4())
    conn = make_conn(config=(("chunk_size", "fünfhundert"), ("chunk_overlap", "64")))

    with pytest.raises(UserFacingError):
        await process_document(conn, make_job(document_id))

    assert executed(conn)[-1] == (
        FAILED_UPDATE,
        document_id,
        "Chunk-Konfiguration ungültig: chunk_size ist keine ganze Zahl ('fünfhundert')",
        VERSION,
        DocumentStatus.failed,
    )
