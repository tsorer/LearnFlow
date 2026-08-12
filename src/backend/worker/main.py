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


async def process_document(conn: asyncpg.Connection, job: Job) -> None:
    payload = json.loads(job.payload or b"{}")
    document_id = payload.get("document_id")
    log.info("Processing document job_id=%s document_id=%s", job.id, document_id)

    await conn.execute("UPDATE documents SET status = 'processing' WHERE id = $1", document_id)
    try:
        chunks = await prepare_chunks(conn, document_id)
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
            await conn.execute(
                "UPDATE documents SET status = 'available', chunk_count = $2, "
                "error_message = NULL WHERE id = $1",
                document_id,
                len(chunks),
            )
        log.info("Indexed document_id=%s chunks=%s", document_id, len(chunks))
    except Exception as exc:
        log.exception("Failed to process document_id=%s", document_id)
        # error_message is handed to every knowledge_owner and admin by GET
        # /documents, not only to the uploader. Only a UserFacingError carries a
        # message written for that audience; everything else stays in the log
        # above — provider errors carry api_base, deployment names and, on an
        # auth failure, a fragment of the API key.
        message = str(exc) if isinstance(exc, UserFacingError) else "Verarbeitung fehlgeschlagen"
        await conn.execute(
            "UPDATE documents SET status = 'failed', error_message = $2 WHERE id = $1",
            document_id,
            message,
        )
        raise


async def prepare_chunks(conn: asyncpg.Connection, document_id: str) -> list[Chunk]:
    """Read, parse and chunk a document. Reads only — writes nothing."""
    row = await conn.fetchrow(
        "SELECT content, content_type FROM documents WHERE id = $1", document_id
    )
    if row is None:
        raise UserFacingError(f"Dokument {document_id} nicht gefunden")

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
    values = {row["key"]: row["value"] for row in rows}
    return (
        int(values.get("chunk_size", DEFAULT_CHUNK_SIZE)),
        int(values.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)),
    )


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
