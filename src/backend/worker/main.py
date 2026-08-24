"""Background Worker — pgqueuer LISTEN/NOTIFY consumer."""

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime

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
    """Raised when the document was replaced while this job was indexing it.

    Not a failure: the upload that replaced it (T-15) enqueued a job of its own,
    and that job is the one whose result belongs in the index.
    """


async def process_document(conn: asyncpg.Connection, job: Job) -> None:
    payload = json.loads(job.payload or b"{}")
    document_id = payload.get("document_id")
    log.info("Processing document job_id=%s document_id=%s", job.id, document_id)

    # The version this run is about. None until the row is read — and only the
    # read itself can fail before that.
    version: datetime | None = None
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
        version = row["updated_at"]
        # row["updated_at"] rather than `version` for the same reason as below:
        # the write is about the version this run read, and `version` is the
        # variable the error path shares.
        if not await mark_processing(conn, document_id, row["updated_at"]):
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
            # row["updated_at"], not `version`: the publish is about the version
            # this run read, and taking it straight from the row says so without
            # relying on a variable the error path shares.
            if not await mark_available(conn, document_id, row["updated_at"], len(chunks)):
                # Inside the transaction on purpose: unwinding it discards the
                # chunks written a line earlier, which are the old version's.
                raise Superseded
        log.info("Indexed document_id=%s chunks=%s", document_id, len(chunks))
    except Superseded:
        log.info(
            "Discarded document_id=%s: replaced while this job was indexing it, "
            "the replacement's own job owns the index now",
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
            # document that is not there, and `updated_at = NULL` matches no row
            # — which is what should happen when there is no row to mark.
            "UPDATE documents SET status = $4, error_message = $2 "
            "WHERE id = $1 AND updated_at = $3",
            document_id,
            message,
            version,
            DocumentStatus.failed,
        )
        raise


async def mark_processing(
    conn: asyncpg.Connection, document_id: str, version: datetime
) -> bool:
    """Announce the run to the reader of GET /documents, under the same version
    condition as every other status this worker writes.

    False means an upload replaced the document between the read a moment ago
    and this write — its own job will do the indexing, and this one stops here.
    """
    claimed = await conn.fetchval(
        "UPDATE documents SET status = $2 WHERE id = $1 AND updated_at = $3 RETURNING id",
        document_id,
        DocumentStatus.processing,
        version,
    )
    return claimed is not None


async def mark_available(
    conn: asyncpg.Connection, document_id: str, version: datetime, chunk_count: int
) -> bool:
    """Publish this run's chunks, unless the document has been replaced since.

    `updated_at` is the version token: the API sets it on every upload and every
    replacement (`app/routers/documents.py`), and nothing else writes it — the
    worker's own updates deliberately leave it alone. So a row whose updated_at
    still matches the one read with the content is the version this job indexed.

    Returns False when the row no longer matches, i.e. an upload replaced the
    document while this job was embedding. Without the condition that run would
    publish the superseded version's chunks over the new one's, and there is no
    error anywhere to notice it by.
    """
    published = await conn.fetchval(
        "UPDATE documents SET status = $4, chunk_count = $2, "
        "error_message = NULL WHERE id = $1 AND updated_at = $3 RETURNING id",
        document_id,
        chunk_count,
        version,
        DocumentStatus.available,
    )
    return published is not None


async def fetch_document(conn: asyncpg.Connection, document_id: str) -> asyncpg.Record:
    """The row this run works on: content, its type, and the version token.

    One statement, so `updated_at` describes the very bytes that come with it —
    see `mark_available`, which refuses to publish under any other version. Kept
    apart from the chunking below so the caller holds the version before the
    first step that can fail with the row already read.
    """
    row = await conn.fetchrow(
        "SELECT content, content_type, updated_at FROM documents WHERE id = $1", document_id
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
    await qm.run()


if __name__ == "__main__":
    asyncio.run(main())
