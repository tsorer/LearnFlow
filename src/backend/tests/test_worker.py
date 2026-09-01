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
from app.models.tables import Document, DocumentStatus
from app.services.parsing import MARKDOWN_CONTENT_TYPE
from worker.main import (
    DEFAULT_PROCESSING_MAX_ATTEMPTS,
    DEFAULT_PROCESSING_TIMEOUT_SECONDS,
    MAX_REAPER_INTERVAL_SECONDS,
    Superseded,
    make_job_handler,
    process_document,
    read_chunk_config,
    read_reaper_config,
    reap_stuck_documents,
    reaper_interval,
)

MARKDOWN = b"# Titel\n\nErster Absatz.\n\nZweiter Absatz."


# The document's index_version, which a run carries as its version token: read
# together with the content, it has to match again before anything is published
# (T-15 — an upload replacing the document moves it, T-43 — so does the reaper).
VERSION = 7

# The failed-update carries the same token, so a run that fails after a
# replacement cannot report its failure on the new version.
FAILED_UPDATE = (
    "UPDATE documents SET status = $4, error_message = $2 "
    "WHERE id = $1 AND index_version = $3"
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
    version: int = VERSION,
) -> AsyncMock:
    conn = AsyncMock()
    # transaction() is a sync call returning an async context manager.
    conn.transaction = MagicMock(return_value=AsyncMock())
    conn.fetchrow.return_value = {
        "content": content,
        "content_type": content_type,
        "index_version": version,
    }
    conn.fetch.return_value = [{"key": key, "value": value} for key, value in config]
    return conn


def executed(conn: AsyncMock) -> list[tuple[Any, ...]]:
    return [call.args for call in conn.execute.await_args_list]


async def test_process_document_writes_chunks_and_marks_available() -> None:
    document_id = str(uuid.uuid4())
    conn = make_conn()

    await process_document(conn, make_job(document_id))

    # Read first, then claim: the processing write carries the version like
    # every other status this worker sets.
    assert conn.fetchrow.await_args.args[0].startswith("SELECT content")
    assert conn.fetchval.await_args_list[0].args == (
        "UPDATE documents SET status = $2 WHERE id = $1 AND index_version = $3 RETURNING id",
        document_id,
        DocumentStatus.processing,
        VERSION,
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

    assert conn.fetchval.await_args_list[1].args == (
        "UPDATE documents SET status = $4, chunk_count = $2, "
        "error_message = NULL, index_attempts = 0 "
        "WHERE id = $1 AND index_version = $3 RETURNING id",
        document_id,
        1,
        VERSION,
        DocumentStatus.available,
    )


async def test_a_successful_run_returns_the_attempt_budget() -> None:
    """The budget bounds one incident, not the document: without this a document
    reaped twice and then indexed successfully would carry those two attempts
    for good, and a crash weeks later would get one retry instead of three."""
    conn = make_conn()

    await process_document(conn, make_job(str(uuid.uuid4())))

    publish = conn.fetchval.await_args_list[1].args[0]
    assert "index_attempts = 0" in publish.split(" WHERE ")[0]


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
    # The run claims the document, and by the time it publishes no row carries
    # the index_version it read any more.
    conn.fetchval.side_effect = [document_id, None]

    await process_document(conn, make_job(document_id))

    # The guarded publish ran and matched nothing, and the transaction was left
    # through the exception — which is what discards the chunks written in it.
    # Asserting on the exit rather than on "no chunks written": the writes
    # happen, the rollback is what takes them back.
    assert conn.executemany.await_count == 1
    assert conn.transaction.return_value.__aexit__.await_args.args[0] is Superseded
    # And it is not an error: the replacement's job owns the index now, so
    # nothing marks this document failed.
    assert DocumentStatus.failed not in [arg for call in executed(conn) for arg in call]


async def test_the_version_read_with_the_content_is_the_one_published() -> None:
    """The token has to come from the same read as the content. Taken from a
    second query, an upload landing between the two would leave the run indexing
    the old bytes under the new version's token — and publishing them."""
    document_id = str(uuid.uuid4())
    conn = make_conn(version=42)

    await process_document(conn, make_job(document_id))

    read_version = 42
    assert "index_version" in conn.fetchrow.await_args.args[0]
    # Both guarded writes compare against the version that came with the bytes.
    assert conn.fetchval.await_args_list[0].args[3] == read_version
    assert conn.fetchval.await_args_list[1].args[3] == read_version


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


async def test_a_processing_run_never_writes_its_own_version_token() -> None:
    """`index_version` is the token the guard compares against, and it only means
    anything as long as the run being guarded is not the one moving it.

    A statement in `process_document` that set it would make the guard compare a
    value the run moved itself — every run would look current, and the whole
    construction would be decoration. The reaper in the same module does write
    the column, and must: that is how it invalidates the run it gives away.
    """
    document_id = str(uuid.uuid4())
    conn = make_conn()

    await process_document(conn, make_job(document_id))

    writes = [
        call.args[0]
        for call in [*conn.execute.await_args_list, *conn.fetchval.await_args_list]
        if "UPDATE documents" in call.args[0]
    ]
    assert writes, "no document write happened — the assertion below proves nothing"
    for sql in writes:
        assignments = sql.split(" WHERE ")[0]
        assert "index_version" not in assignments, sql


def test_the_version_token_does_not_move_on_an_unrelated_orm_write() -> None:
    """The other half of the same invariant, and the reason T-43 gave the guard a
    column of its own (#69).

    `updated_at` carries `onupdate=func.now()`: any ORM write to a Document moves
    it, so while it was the token, a route writing the row for an unrelated
    reason — a validation (US-06), an area rename, the reaper itself — silently
    invalidated a run that was indexing the document at that moment. Logged as
    info, reported as nothing, document left without chunks. `index_version` has
    no `onupdate`, which is what makes that impossible rather than merely
    documented.
    """
    assert Document.__table__.c.index_version.onupdate is None
    assert Document.__table__.c.index_attempts.onupdate is None


def make_reaper_conn(rows: Sequence[dict[str, Any]] = ()) -> AsyncMock:
    """A connection whose reaping UPDATE returns `rows` — id plus the attempt
    count the statement has already incremented."""
    conn = AsyncMock()
    conn.transaction = MagicMock(return_value=AsyncMock())
    conn.fetch.return_value = list(rows)
    return conn


async def test_the_reaper_only_looks_at_processing_documents_without_a_live_job() -> None:
    """AK 4 — a document that is being processed right now stays untouched.

    Both halves of that live in the statement: the status filter, and a NOT
    EXISTS over the queue that spares any document whose job was handed out
    within the timeout.
    """
    conn = make_reaper_conn()

    await reap_stuck_documents(conn, timeout_seconds=900, max_attempts=3)

    sql, timeout, max_attempts, pending, failed, message, status = conn.fetch.await_args.args
    assert status == DocumentStatus.processing
    assert "NOT EXISTS" in sql
    assert "q.heartbeat > now() - make_interval(secs => $1)" in sql
    assert "q.status IN ('queued', 'picked')" in sql
    # float, not int: make_interval takes double precision, and asyncpg refuses
    # to encode an int where the query says float8.
    assert timeout == 900.0
    assert isinstance(timeout, float)
    assert (max_attempts, pending, failed) == (3, DocumentStatus.pending, DocumentStatus.failed)
    assert "3 Versuchen" in message


async def test_the_reaper_invalidates_the_run_it_takes_away() -> None:
    """The point of the version token (#69): `index_version` moves in both
    branches, unconditionally, so a job presumed dead that wakes up anyway fails
    every guarded write instead of racing the new attempt for the chunks."""
    conn = make_reaper_conn()

    await reap_stuck_documents(conn, timeout_seconds=900, max_attempts=3)

    sql = conn.fetch.await_args.args[0]
    assert "index_version  = d.index_version + 1" in sql
    # The status is the part that branches, the token is not.
    assert "CASE WHEN" not in sql.split("index_version  = d.index_version + 1")[1].split("\n")[0]


async def test_the_reaper_requeues_a_document_below_the_attempt_budget() -> None:
    document_id = uuid.uuid4()
    conn = make_reaper_conn([{"id": document_id, "index_attempts": 1}])

    reaped = await reap_stuck_documents(conn, timeout_seconds=900, max_attempts=3)

    assert reaped == 1
    sql, rows = conn.executemany.await_args.args
    assert "INSERT INTO pgqueuer" in sql
    # Byte-identical to what app/queue.py enqueues, so its dedupe still
    # recognises the job a later upload replaces.
    assert rows == [(json.dumps({"document_id": str(document_id)}).encode(),)]


async def test_the_reaper_gives_up_at_the_attempt_budget() -> None:
    """The document is marked failed and *not* queued again — otherwise a
    document that reliably kills the worker would be retried forever, taking
    every other document's processing down with it each time."""
    conn = make_reaper_conn([{"id": uuid.uuid4(), "index_attempts": 3}])

    reaped = await reap_stuck_documents(conn, timeout_seconds=900, max_attempts=3)

    assert reaped == 1
    conn.executemany.assert_not_awaited()


async def test_the_reaper_queues_only_the_documents_that_got_another_attempt() -> None:
    kept, given_up = uuid.uuid4(), uuid.uuid4()
    conn = make_reaper_conn(
        [{"id": kept, "index_attempts": 2}, {"id": given_up, "index_attempts": 3}]
    )

    await reap_stuck_documents(conn, timeout_seconds=900, max_attempts=3)

    _, rows = conn.executemany.await_args.args
    assert rows == [(json.dumps({"document_id": str(kept)}).encode(),)]


async def test_reaping_and_requeueing_share_one_transaction() -> None:
    """A document back on 'pending' without a job to pick it up is exactly the
    state this function repairs — it must not be able to create it."""
    conn = make_reaper_conn([{"id": uuid.uuid4(), "index_attempts": 1}])

    await reap_stuck_documents(conn, timeout_seconds=900, max_attempts=3)

    conn.transaction.assert_called_once()
    conn.transaction.return_value.__aexit__.assert_awaited()


async def test_reaper_config_falls_back_when_the_keys_are_missing() -> None:
    conn = AsyncMock()
    conn.fetch.return_value = []

    assert await read_reaper_config(conn) == (
        DEFAULT_PROCESSING_TIMEOUT_SECONDS,
        DEFAULT_PROCESSING_MAX_ATTEMPTS,
    )


@pytest.mark.parametrize("value", ["neunhundert", "0", "-5"])
async def test_reaper_config_falls_back_instead_of_raising_on_a_bad_value(value: str) -> None:
    """Unlike the chunk parameters, a bad value here has no document to be
    reported on, and a reaper that stops on a typo is the very failure this
    ticket repairs. The CHECK of 0017 keeps such values out of the table."""
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"key": "processing_timeout_seconds", "value": value},
        {"key": "processing_max_attempts", "value": "2"},
    ]

    assert await read_reaper_config(conn) == (DEFAULT_PROCESSING_TIMEOUT_SECONDS, 2)


async def test_reaper_config_reads_both_keys() -> None:
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"key": "processing_timeout_seconds", "value": "60"},
        {"key": "processing_max_attempts", "value": "1"},
    ]

    assert await read_reaper_config(conn) == (60, 1)


async def test_the_entrypoint_filter_guards_the_json_cast() -> None:
    """Postgres does not promise to evaluate the entrypoint filter before the
    cast. A second entrypoint with a non-JSON payload would make the cast throw,
    `reaper_loop` would swallow it, and the reaper would be off while the worker
    looked healthy — so the guard is a CASE, which Postgres does order (#104).
    """
    conn = make_reaper_conn()

    await reap_stuck_documents(conn, timeout_seconds=900, max_attempts=3)

    sql = conn.fetch.await_args.args[0]
    guard = sql.split("CASE WHEN q.entrypoint = 'process_document'")
    assert len(guard) == 2, "the entrypoint filter no longer guards the cast"
    assert "convert_from" in guard[1].split("END")[0]
    # And nowhere outside it — a bare copy of the condition would reintroduce
    # exactly the unordered evaluation the CASE is there to prevent.
    assert sql.count("convert_from") == 1


def test_the_pass_interval_follows_short_timeouts_and_is_capped_for_long_ones() -> None:
    """The quarter keeps a short timeout responsive; the cap keeps a long one
    from making detection slow as well. A pass is one indexed query — there is
    nothing to save by waiting longer."""
    assert reaper_interval(60) == 15
    assert reaper_interval(DEFAULT_PROCESSING_TIMEOUT_SECONDS) == MAX_REAPER_INTERVAL_SECONDS
    assert reaper_interval(4 * MAX_REAPER_INTERVAL_SECONDS) == MAX_REAPER_INTERVAL_SECONDS
