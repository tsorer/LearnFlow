"""Document processing task — Parsing → Chunking → Embedding → pgvector indexing."""

import logging
import uuid

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.tables import Chunk, Document, DocumentStatus
from app.services import embedding as emb_service
from app.services.chunking import (
    extract_docx_chunks,
    extract_md_chunks,
    extract_pdf_chunks,
)

log = logging.getLogger(__name__)

BATCH_SIZE = 32  # chunks per embedding API call


async def process_document(document_id: str) -> None:
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, document_id)
        if not doc:
            log.error("Document %s not found", document_id)
            return

        log.info("Processing document %s (%s)", doc.filename, doc.id)

        await db.execute(
            update(Document)
            .where(Document.id == doc.id)
            .values(status=DocumentStatus.processing)
        )
        await db.commit()

        try:
            await _process(db, doc)
        except Exception as exc:
            log.exception("Failed to process document %s: %s", document_id, exc)
            await db.execute(
                update(Document)
                .where(Document.id == doc.id)
                .values(status=DocumentStatus.failed)
            )
            await db.commit()


async def _process(db: AsyncSession, doc: Document) -> None:
    cfg = await _load_config(db)
    chunk_size = int(cfg.get("chunk_size", settings.chunk_size))
    overlap = int(cfg.get("chunk_overlap", settings.chunk_overlap))

    # Parse and chunk
    ct = doc.content_type
    if "pdf" in ct:
        chunks = extract_pdf_chunks(doc.content, chunk_size, overlap)
    elif "wordprocessingml" in ct or "docx" in ct:
        chunks = extract_docx_chunks(doc.content, chunk_size, overlap)
    else:
        chunks = extract_md_chunks(doc.content, chunk_size, overlap)

    if not chunks:
        log.warning("No chunks extracted from %s", doc.filename)
        await db.execute(
            update(Document)
            .where(Document.id == doc.id)
            .values(status=DocumentStatus.available, chunk_count=0)
        )
        await db.commit()
        return

    # Delete existing chunks (re-upload replaces)
    await db.execute(
        text("DELETE FROM chunks WHERE document_id = :doc_id"),
        {"doc_id": doc.id},
    )

    # Embed in batches
    texts = [c.content for c in chunks]
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_emb = await emb_service.embed(batch)
        embeddings.extend(batch_emb)
        log.info("Embedded %d/%d chunks for %s", min(i + BATCH_SIZE, len(texts)), len(texts), doc.filename)

    # Insert chunks with embeddings + tsvector
    for chunk, embedding in zip(chunks, embeddings):
        emb_str = "[" + ",".join(str(v) for v in embedding) + "]"
        await db.execute(
            text("""
                INSERT INTO chunks (id, document_id, content, embedding, tsv, chunk_index, page, heading)
                VALUES (
                    :id, :doc_id, :content,
                    CAST(:embedding AS vector),
                    to_tsvector('german', :content),
                    :chunk_index, :page, :heading
                )
            """),
            {
                "id": str(uuid.uuid4()),
                "doc_id": str(doc.id),
                "content": chunk.content,
                "embedding": emb_str,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page,
                "heading": chunk.heading,
            },
        )

    await db.execute(
        update(Document)
        .where(Document.id == doc.id)
        .values(status=DocumentStatus.available, chunk_count=len(chunks))
    )
    await db.commit()
    log.info("Document %s: %d chunks indexed", doc.filename, len(chunks))


async def _load_config(db: AsyncSession) -> dict:
    rows = await db.execute(text("SELECT key, value FROM config"))
    return {r.key: r.value for r in rows}
