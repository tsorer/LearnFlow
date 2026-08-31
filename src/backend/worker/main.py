"""Background Worker — pgqueuer LISTEN/NOTIFY consumer."""

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable

import asyncpg
from pgqueuer import QueueManager
from pgqueuer.db import AsyncpgDriver
from pgqueuer.models import Job

from app.config import settings
from app.exceptions import UserFacingError
from app.models.tables import DocumentStatus
from app.services.chunking import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    Chunk,
    chunk_blocks,
    count_tokens,
)
from app.services.embedding import embed_texts
from app.services.parsing import parse_document

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# The heading is indexed alongside the content: DOCX and Markdown headings are
# not part of the chunk text (parsing strips them into their own field), and in
# our corpus the section titles carry the search-relevant terms. coalesce is not
# optional — `NULL || ' ' || text` is NULL in Postgres, and PDF chunks always
# have heading = NULL, so without it no PDF chunk would be indexed at all.
#
# The embedding is bound as text and cast in Postgres ($7::text::vector, ADR-005):
# a bare $7::vector would make Postgres infer the parameter type as `vector`,
# which asyncpg cannot encode without registering the extension codec on every
# pooled connection. pgvector's input format is a JSON float array, so
# json.dumps produces exactly the literal it expects.
INSERT_CHUNK = (
    "INSERT INTO chunks (id, document_id, content, chunk_index, page, heading, tsv, embedding) "
    "VALUES ($1, $2, $3, $4, $5, $6, "
    "to_tsvector('german', coalesce($6, '') || ' ' || $3), $7::text::vector)"
)


class Superseded(Exception):
    """Raised when this run no longer owns the document's index.

    Not a failure, and there are two ways to get here. An upload replaced the
    document while the job was indexing it (T-15) — its own job carries the
    result that belongs in the index. Or the reaper declared this run abandoned
    and handed the document to a fresh attempt (T-43). Both say the same thing
    by incrementing `index_version`: whatever this run computed is about a
    version nobody is waiting for any more.
    """


async def process_document(conn: asyncpg.Connection, job: Job) -> None:
    payload = json.loads(job.payload or b"{}")
    document_id = payload.get("document_id")
    log.info("Processing document job_id=%s document_id=%s", job.id, document_id)

    # The version this run is about. None until the row is read — and only the
    # read itself can fail before that.
    version: int | None = None
    try:
        # Reading before the first write, so every status this function sets
        # carries the version condition. The other order left 'processing' as
        # the one unguarded write in the file: a stale job — redelivered after a
        # worker crash — would pull a document that is 'available' back into
        # 'processing' and out of retrieval for the length of its run.
        row = await fetch_document(conn, document_id)
        # Captured here, not after the chunking: parsing and the chunk config
        # can both still throw, and a failure at that point belongs to this
        # version just as much as a failed embedding does. Taking the version
        # from the return value of the chunking left it None for exactly those
        # failures, which let them through the guard below (review on #87).
        version = row["index_version"]
        # row["index_version"] rather than `version` for the same reason as
        # below: the write is about the version this run read, and `version` is
        # the variable the error path shares.
        if not await mark_processing(conn, document_id, row["index_version"]):
            # Before the embedding, not after: a run that is already superseded
            # here has nothing to contribute and no reason to spend a provider
            # call finding that out.
            raise Superseded
        chunks = await prepare_chunks(conn, row)
        # Embedding runs before the transaction opens, not inside it: it is
        # tens of seconds of HTTP, and an open transaction across that span
        # would sit idle-in-transaction and hold back VACUUM on chunks.
        # All chunks are embedded before anything is written — a partially
        # embedded document would stay findable through the tsv index while
        # being invisible to the dense half of the hybrid search (ADR-007),
        # which is silently degraded recall instead of a failed job.
        embeddings = await embed_texts([chunk.content for chunk in chunks])
        async with conn.transaction():
            await store_chunks(conn, document_id, chunks, embeddings)
            # row["index_version"], not `version`: the publish is about the
            # version this run read, and taking it straight from the row says so
            # without relying on a variable the error path shares.
            if not await mark_available(conn, document_id, row["index_version"], len(chunks)):
                # Inside the transaction on purpose: unwinding it discards the
                # chunks written a line earlier, which are the old version's.
                raise Superseded
        log.info("Indexed document_id=%s chunks=%s", document_id, len(chunks))
    except Superseded:
        log.info(
            "Discarded document_id=%s: replaced or reaped while this job was "
            "indexing it, a newer attempt owns the index now",
            document_id,
        )
    except Exception as exc:
        log.exception("Failed to process document_id=%s", document_id)
        # error_message is handed to every knowledge_owner and admin by GET
        # /documents, not only to the uploader. Only a UserFacingError carries a
        # message written for that audience; everything else stays in the log
        # above — provider errors carry api_base, deployment names and, on an
        # auth failure, a fragment of the API key.
        message = str(exc) if isinstance(exc, UserFacingError) else "Verarbeitung fehlgeschlagen"
        await conn.execute(
            # Same version condition as the success path: a run that fails after
            # the document was replaced must not report its own failure on the
            # new version, which is still waiting for its own job. Without the
            # condition it would mark a document 'failed' that another run has
            # meanwhile indexed successfully — and fail-closed retrieval
            # (ADR-008) would drop it from every answer with nothing to see.
            #
            # No escape for version IS NULL: the only failure that early is a
            # document that is not there, and `index_version = NULL` matches no
            # row — which is what should happen when there is no row to mark.
            "UPDATE documents SET status = $4, error_message = $2 "
            "WHERE id = $1 AND index_version = $3",
            document_id,
            message,
            version,
            DocumentStatus.failed,
        )
        raise


async def mark_processing(
    conn: asyncpg.Connection, document_id: str, version: int
) -> bool:
    """Announce the run to the reader of GET /documents, under the same version
    condition as every other status this worker writes.

    False means the document was replaced or reaped between the read a moment
    ago and this write — a newer attempt will do the indexing, and this one
    stops here.
    """
    claimed = await conn.fetchval(
        "UPDATE documents SET status = $2 WHERE id = $1 AND index_version = $3 RETURNING id",
        document_id,
        DocumentStatus.processing,
        version,
    )
    return claimed is not None


async def mark_available(
    conn: asyncpg.Connection, document_id: str, version: int, chunk_count: int
) -> bool:
    """Publish this run's chunks, unless the document has been replaced since.

    `index_version` is the version token. Two writers increment it: the API on
    every upload and replacement (`app/routers/documents.py`), and the reaper
    when it gives an abandoned run away (`reap_stuck_documents`). A processing
    run never writes it — so a row whose index_version still matches the one
    read with the content is the version this job indexed.

    Returns False when the row no longer matches. Without the condition a run
    would publish a superseded version's chunks over the current one's, and
    there is no error anywhere to notice it by.
    """
    # `index_attempts = 0` because the budget is meant to bound one incident, not
    # the version: a document reaped twice and then indexed successfully would
    # otherwise carry the two attempts for the rest of its life, and a crash
    # weeks later would get a single retry instead of the configured three.
    published = await conn.fetchval(
        "UPDATE documents SET status = $4, chunk_count = $2, "
        "error_message = NULL, index_attempts = 0 "
        "WHERE id = $1 AND index_version = $3 RETURNING id",
        document_id,
        chunk_count,
        version,
        DocumentStatus.available,
    )
    return published is not None


async def fetch_document(conn: asyncpg.Connection, document_id: str) -> asyncpg.Record:
    """The row this run works on: content, its type, and the version token.

    One statement, so `index_version` describes the very bytes that come with it —
    see `mark_available`, which refuses to publish under any other version. Kept
    apart from the chunking below so the caller holds the version before the
    first step that can fail with the row already read.
    """
    row = await conn.fetchrow(
        "SELECT content, content_type, index_version FROM documents WHERE id = $1", document_id
    )
    if row is None:
        raise UserFacingError(f"Dokument {document_id} nicht gefunden")
    return row


async def prepare_chunks(conn: asyncpg.Connection, row: asyncpg.Record) -> list[Chunk]:
    """Parse and chunk a document's content. Reads config only — writes nothing."""
    chunk_size, chunk_overlap = await read_chunk_config(conn)
    blocks = parse_document(bytes(row["content"]), row["content_type"])
    # Tokenizer passed explicitly: the worker owns the choice of encoding, the
    # chunker stays free of it (and tests can substitute a trivial counter).
    chunks = chunk_blocks(
        blocks, chunk_size=chunk_size, chunk_overlap=chunk_overlap, count=count_tokens
    )
    if not chunks:
        raise UserFacingError("Kein extrahierbarer Text gefunden")
    return chunks


async def store_chunks(
    conn: asyncpg.Connection,
    document_id: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    """Write a document's chunks with their vectors. The caller owns the
    transaction, so a failure leaves the previous index untouched."""
    # Replace instead of append so re-processing a document stays idempotent.
    await conn.execute("DELETE FROM chunks WHERE document_id = $1", document_id)
    await conn.executemany(
        INSERT_CHUNK,
        [
            (
                str(uuid.uuid4()),
                document_id,
                c.content,
                c.chunk_index,
                c.page,
                c.heading,
                json.dumps(embedding),
            )
            # strict= turns a chunk/vector count mismatch into an error instead
            # of silently dropping the tail.
            for c, embedding in zip(chunks, embeddings, strict=True)
        ],
    )


async def read_chunk_config(conn: asyncpg.Connection) -> tuple[int, int]:
    """Chunk parameters live in the config table so they can be calibrated
    without a deployment (ADR-007). Read per job, not cached at startup."""
    rows = await conn.fetch(
        "SELECT key, value FROM config WHERE key IN ('chunk_size', 'chunk_overlap')"
    )
    values: dict[str, str] = {row["key"]: row["value"] for row in rows}
    return (
        _as_int(values, "chunk_size", DEFAULT_CHUNK_SIZE),
        _as_int(values, "chunk_overlap", DEFAULT_CHUNK_OVERLAP),
    )


def _as_int(values: dict[str, str], key: str, default: int) -> int:
    """Read one chunk parameter from the config rows.

    `config.value` is one Text column shared by floats, ints and everything
    else, and nothing validates it on write yet — PUT /admin/config is still a
    placeholder (T-37). A bare int() would fail with Python's own wording
    ("invalid literal for int() ..."), which is exactly the kind of text this
    ticket keeps out of error_message, while the range checks one call later in
    chunk_blocks already phrase the same class of mistake as a configuration
    error. The value comes from an operator, not from a provider, so it can be
    named.
    """
    raw = values.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise UserFacingError(
            f"Chunk-Konfiguration ungültig: {key} ist keine ganze Zahl ({raw!r})"
        ) from exc


# Fallbacks for the two reaper settings, used when `config` has no row for
# them — the same "read per pass, fall back on absence" contract the chunk
# parameters follow. Values match the seed of migration 0017.
#
# 2700 s is derived, not picked (ADR-006, Nachtrag): a 10 MB upload at the
# density of the densest corpus document runs to ~29 embedding batches, the
# batches are sequential, and each one may take TIMEOUT_SECONDS *per attempt*
# with MAX_RETRIES on top (`app/services/embedding.py`). A run in which every
# batch times out once and succeeds on retry is slow but valid, and reaping it
# would end in a `failed` that no re-upload can fix.
DEFAULT_PROCESSING_TIMEOUT_SECONDS = 2700
DEFAULT_PROCESSING_MAX_ATTEMPTS = 3

# How often the reaper looks within one timeout, and the ceiling on the pause
# between two passes. The quarter keeps short timeouts responsive; the cap keeps
# a long one from also making the *detection* slow, which is a separate thing:
# the pass is one indexed query, and nothing is gained by waiting 11 minutes
# between two of them just because the deadline being enforced is 45.
REAPER_PASSES_PER_TIMEOUT = 4
MAX_REAPER_INTERVAL_SECONDS = 300

# A document is abandoned when nothing in the queue is working on it any more.
#
# `heartbeat` is the timestamp pgqueuer writes when it hands the job out
# (`SET status = 'picked', updated = NOW(), heartbeat = NOW()`), so with our
# registration it reads as "claimed this long ago": the periodic heartbeat
# pgqueuer can send is driven by `retry_timer`, and ours is the default zero,
# which leaves that sender switched off. The timeout therefore has to exceed the
# longest legitimate run, embedding included — that is what the 900 s default is
# for. Should `retry_timer` ever be set, live jobs start refreshing the column
# and this same condition tightens by itself into "still alive".
#
# The payload is matched through `->>` rather than by byte equality, unlike the
# dedupe in `app/queue.py`: there both sides come from json.dumps, here one side
# would be JSON rendered by Postgres, which spaces its colons differently.
#
# The cast sits inside a CASE, and that is not decoration: Postgres does not
# promise to evaluate the entrypoint filter first, so a second entrypoint with a
# non-JSON payload would let the cast see bytes it cannot parse and throw. The
# loop below catches that, logs it, and sleeps — leaving the reaper silently
# switched off while the worker otherwise looks healthy, which is the very class
# of failure this ticket exists to remove. CASE is what Postgres documents for
# forcing the order, so the guard cannot be optimised away (review on #104).
STUCK_DOCUMENTS = """
    UPDATE documents d
       SET index_version  = d.index_version + 1,
           index_attempts = d.index_attempts + 1,
           status = CASE WHEN d.index_attempts + 1 < $2 THEN $3 ELSE $4 END,
           error_message = CASE WHEN d.index_attempts + 1 < $2 THEN NULL ELSE $5 END
     WHERE d.status = $6
       AND NOT EXISTS (
             SELECT 1
               FROM pgqueuer q
              WHERE q.status IN ('queued', 'picked')
                AND q.heartbeat > now() - make_interval(secs => $1)
                AND CASE WHEN q.entrypoint = 'process_document'
                         THEN convert_from(q.payload, 'UTF8')::json ->> 'document_id'
                              = d.id::text
                         ELSE false
                    END
           )
 RETURNING d.id, d.index_attempts
"""

REQUEUE_DOCUMENT = """
    INSERT INTO pgqueuer (priority, created, updated, heartbeat,
                          execute_after, status, entrypoint, payload)
    VALUES (0, now(), now(), now(), now(), 'queued', 'process_document', $1)
"""


async def reap_stuck_documents(
    conn: asyncpg.Connection, timeout_seconds: int, max_attempts: int
) -> int:
    """Free documents whose indexing run died with the worker that claimed it.

    `process_document` sets 'processing' before it starts, so a container that
    dies in between — crash, restart, deployment, OOM — leaves the row there for
    good: invisible to retrieval, not marked failed, and to the user a document
    that loads forever (T-43).

    The run is not merely re-queued, it is invalidated: `index_version` moves in
    both branches. A job presumed dead that wakes up anyway then fails
    `mark_processing`, `mark_available` *and* its own failure write, logs that it
    was superseded and touches nothing — deterministic, where re-queueing alone
    would leave two live runs racing over one document's chunks.

    Below the attempt budget the document goes back to 'pending' and is queued
    again; at the budget it is marked failed with a message its owner can act on.
    Returns how many rows were touched, for the caller's log.
    """
    # The message names no cause on purpose. The condition below is "claimed
    # longer ago than the timeout", which a worker that died satisfies — and so
    # does a run that is simply slower than the timeout allows. Naming the
    # restart would diagnose the second case wrongly, and its usual advice, to
    # upload the document again, would send the owner into the same timeout.
    exhausted = (
        f"Verarbeitung wurde nach {max_attempts} Versuchen aufgegeben — sie wurde jeweils "
        "abgebrochen oder hat das Zeitlimit überschritten."
    )
    # One transaction, so no document ends up back on 'pending' without a job to
    # pick it up: that state looks exactly like the one being repaired here.
    async with conn.transaction():
        rows = await conn.fetch(
            STUCK_DOCUMENTS,
            float(timeout_seconds),
            max_attempts,
            DocumentStatus.pending,
            DocumentStatus.failed,
            exhausted,
            DocumentStatus.processing,
        )
        requeued = [row for row in rows if row["index_attempts"] < max_attempts]
        if requeued:
            # Same insert as `app/queue.py`, in raw SQL because the worker has no
            # SQLAlchemy session, and with a json.dumps payload for the same
            # reason: the dedupe over there matches payload bytes, and would stop
            # recognising these jobs if Postgres rendered the JSON instead.
            await conn.executemany(
                REQUEUE_DOCUMENT,
                [(json.dumps({"document_id": str(row["id"])}).encode(),) for row in requeued],
            )
    for row in rows:
        log.warning(
            "Reaped document_id=%s: indexing run abandoned, attempt %s of %s — %s",
            row["id"],
            row["index_attempts"],
            max_attempts,
            "re-queued" if row["index_attempts"] < max_attempts else "giving up",
        )
    return len(rows)


async def read_reaper_config(conn: asyncpg.Connection) -> tuple[int, int]:
    """The reaper's timeout and attempt budget — read per pass, so both can be
    calibrated without a deployment (same reason as the chunk parameters).

    Falls back to the defaults instead of raising, unlike `_as_int`: a bad value
    arrives here without a document to report it on, and a reaper that stops on a
    typo is the very failure this ticket exists to repair. The CHECK constraint
    of migration 0017 keeps such a value out of the table in the first place, so
    the warning below should stay theoretical.
    """
    rows = await conn.fetch(
        "SELECT key, value FROM config "
        "WHERE key IN ('processing_timeout_seconds', 'processing_max_attempts')"
    )
    values: dict[str, str] = {row["key"]: row["value"] for row in rows}
    parsed: list[int] = []
    for key, default in (
        ("processing_timeout_seconds", DEFAULT_PROCESSING_TIMEOUT_SECONDS),
        ("processing_max_attempts", DEFAULT_PROCESSING_MAX_ATTEMPTS),
    ):
        raw = values.get(key)
        if raw is None:
            parsed.append(default)
            continue
        try:
            value = int(raw)
        except ValueError:
            value = 0
        if value < 1:
            log.warning("config %s=%r is not a positive integer — using %s", key, raw, default)
            value = default
        parsed.append(value)
    return parsed[0], parsed[1]


def reaper_interval(timeout_seconds: float) -> float:
    """How long to wait between two passes for a given timeout."""
    return min(timeout_seconds / REAPER_PASSES_PER_TIMEOUT, MAX_REAPER_INTERVAL_SECONDS)


async def reaper_loop(pool: asyncpg.Pool) -> None:
    """Run the reaper for as long as the worker lives.

    Sleeps first: at startup the jobs of a worker that just died are the ones
    this exists for, and they are not stale yet — and the API may still be
    running the migrations of the same deployment.

    Every failure is logged and swallowed. The reaper is a repair mechanism, and
    a broken one must not take the job consumer down with it.
    """
    interval = reaper_interval(DEFAULT_PROCESSING_TIMEOUT_SECONDS)
    while True:
        await asyncio.sleep(interval)
        try:
            async with pool.acquire() as conn:
                timeout_seconds, max_attempts = await read_reaper_config(conn)
                interval = reaper_interval(timeout_seconds)
                await reap_stuck_documents(conn, timeout_seconds, max_attempts)
        except Exception:
            log.exception("Reaper pass failed — next attempt in %s s", interval)


def make_job_handler(pool: asyncpg.Pool) -> Callable[[Job], Awaitable[None]]:
    """Build the pgqueuer entrypoint. Lives outside main() so a test can assert
    the one property that silently broke T-11: it must be a coroutine function.
    """

    # Must be an async def, not a lambda: pgqueuer decides via
    # iscoroutinefunction() whether to await the entrypoint. A lambda returning
    # a coroutine is treated as synchronous, so the coroutine is dropped and the
    # job is logged as successful without ever running.
    async def handle_document_job(job: Job) -> None:
        # Own connection per job — the QueueManager's connection is busy with
        # LISTEN/dequeue and asyncpg forbids concurrent operations on one
        # connection, which two parallel uploads would trigger immediately.
        async with pool.acquire() as job_conn:
            await process_document(job_conn, job)

    return handle_document_job


async def main() -> None:
    log.info("Worker starting — connecting to database")
    conn = await asyncpg.connect(settings.asyncpg_dsn)
    pool = await asyncpg.create_pool(settings.asyncpg_dsn, min_size=1, max_size=5)
    driver = AsyncpgDriver(conn)
    qm = QueueManager(driver)

    qm.entrypoint("process_document")(make_job_handler(pool))

    log.info("Worker ready — listening for jobs")
    # The reaper is a side task, not a second consumer: it is cancelled when the
    # queue manager returns, so a SIGTERM shuts the container down instead of
    # leaving an endless loop behind for the runtime to kill.
    reaper = asyncio.create_task(reaper_loop(pool))
    try:
        await qm.run()
    finally:
        reaper.cancel()


if __name__ == "__main__":
    asyncio.run(main())
