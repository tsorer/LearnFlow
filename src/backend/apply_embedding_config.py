#!/usr/bin/env python
"""Reconcile script: docker compose run --rm api python apply_embedding_config.py

Accepts a changed `EMBED_MODEL`/`EMBED_DIMENSIONS` (`app/config.py`) as the new
active configuration and re-indexes the whole corpus under it (ADR-005, T-42).

Deliberately `docker compose run`, not `docker exec src-api-1 ...`: the moment
`.env` carries a changed value, the long-running `api`/`worker` containers
crash-loop on the very mismatch this script exists to resolve (their startup
check, `app/services/embedding_config.py`), so `src-api-1` may not be a
running container to exec into. `run` starts a one-off container from the
same image and `.env`, without the `api` service's own
`alembic upgrade head && uvicorn ...` command and therefore without its
startup check — it only needs `db` to already be up. See
`Ops/07_Pilotstart-Checkliste.md` 2.2a for the full sequencing.

This is the deliberate half of T-42's fail-closed pair. The startup check
(`app/services/embedding_config.py`, wired into `app/main.py` and
`worker/main.py`) aborts the API and the worker the moment `Settings` and the
`config` table disagree — on purpose, so that neither process ever embeds a
single chunk under an unreconciled model. Nothing about that abort resolves
itself: an operator who changed `EMBED_MODEL` on purpose runs this script
once to accept the new value, which is also the only moment a full
re-indexing of the corpus is triggered. Running it without having changed
anything is a safe no-op (see `_reconcile` below) — there is no destructive
path that fires on a matching configuration.

Three things happen together, in one transaction, because a script killed
half-way through must not leave the corpus in a state no query or worker
startup can make sense of:

1. If the *dimension* changed, `chunks.embedding` is dropped and recreated at
   the new width, HNSW index included — pgvector's column type is fixed at
   creation (`0003_documents_chunks.py`), so a dimension change is a schema
   change, not just a config change. A model change that keeps the same
   dimension (the case Issue #68 describes — pgvector cannot tell two
   same-width models apart) skips this step entirely; nothing about the
   column needs to move.
2. `config.embed_model`/`embed_dimensions` are updated to what `Settings`
   currently says — the same two rows migration 0018 seeded, now carrying
   the accepted value instead of the MVP default. Passing through the same
   `UPDATE` path the admin API would use keeps this subject to the CHECK
   constraint (0018) like every other write to this table.
3. Every document goes back to `pending` with `index_version` incremented
   (the same token `worker/main.py`'s `Superseded` guard and the T-43 reaper
   already use) and `index_attempts` reset to zero — a fresh incident, not a
   continuation of whatever attempts predate this run. Existing chunks are
   deleted outright rather than left for the worker to replace one document
   at a time: they reference a vector space this script may have just
   dropped, and until the requeue finishes they are stale under a model
   change either way. A running worker or API needs no downtime for this —
   an in-flight indexing run that read its document before this script
   committed loses the version race in `mark_available` and discards its own
   work as superseded, exactly as T-43 already handles a replaced upload.
"""

import asyncio
import json
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.services.embedding_config import (
    EMBEDDING_CONFIG_KEYS,
    EmbeddingConfig,
    embedding_config_from,
)

HNSW_INDEX = "ix_chunks_embedding_hnsw"

INSERT_JOB = """
    INSERT INTO pgqueuer (priority, created, updated, heartbeat, execute_after,
                          status, entrypoint, payload)
    VALUES (0, now(), now(), now(), now(), 'queued', 'process_document', :payload)
"""


async def _reconcile(db: AsyncSession, configured: EmbeddingConfig) -> None:
    result = await db.execute(
        text("SELECT key, value FROM config WHERE key = ANY(:keys)"),
        {"keys": list(EMBEDDING_CONFIG_KEYS)},
    )
    values: dict[str, str] = {key: value for key, value in result.all()}
    persisted = embedding_config_from(values)

    if persisted == configured:
        print(
            f"Bereits synchron: {configured.model} / {configured.dimensions} Dimensionen. "
            "Nichts zu tun."
        )
        return

    print(
        f"config sagt {persisted.model} / {persisted.dimensions} Dimensionen, "
        f"Settings verlangt {configured.model} / {configured.dimensions} Dimensionen."
    )

    if persisted.dimensions != configured.dimensions:
        print(
            f"Dimension ändert sich {persisted.dimensions} -> {configured.dimensions}: "
            "chunks.embedding wird neu angelegt."
        )
        # DROP COLUMN cascades to the index -- named for symmetry with the
        # CREATE below, not because Postgres needs the DROP INDEX spelled out.
        await db.execute(text(f"DROP INDEX IF EXISTS {HNSW_INDEX}"))
        await db.execute(text("ALTER TABLE chunks DROP COLUMN IF EXISTS embedding"))
        await db.execute(
            text(f"ALTER TABLE chunks ADD COLUMN embedding vector({configured.dimensions})")
        )
        # Same WITH (...) as 0003_documents_chunks.py -- an index rebuilt with
        # different parameters would make retrieval quality depend on which
        # model change happened to trigger the rebuild.
        await db.execute(
            text(
                f"CREATE INDEX {HNSW_INDEX} ON chunks "
                "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
            )
        )

    # changed_by stays NULL rather than carrying whatever admin last touched an
    # unrelated row: this write has no admin session behind it, and leaving
    # the two audit columns untouched would misattribute this change to
    # whoever's id happened to be there before, or leave changed_at silently
    # stuck at migration 0018's insert time forever.
    await db.execute(
        text(
            "UPDATE config SET value = :value, changed_by = NULL, changed_at = now() "
            "WHERE key = 'embed_model'"
        ),
        {"value": configured.model},
    )
    await db.execute(
        text(
            "UPDATE config SET value = :value, changed_by = NULL, changed_at = now() "
            "WHERE key = 'embed_dimensions'"
        ),
        {"value": str(configured.dimensions)},
    )

    document_ids = (
        await db.execute(
            text(
                "UPDATE documents SET status = 'pending', index_version = index_version + 1, "
                "index_attempts = 0, chunk_count = 0, error_message = NULL "
                "RETURNING id"
            )
        )
    ).scalars().all()

    # Stale under the new configuration regardless of whether the dimension
    # moved -- the worker would delete and reinsert per document anyway
    # (`store_chunks`), but leaving them until every requeued job completes
    # would serve a query mixing two models' vectors in one retrieval.
    await db.execute(text("DELETE FROM chunks"))

    # A document already `pending` with a `queued` job the worker hasn't
    # picked up yet keeps that job regardless of the UPDATE above -- marking
    # `documents.status` does nothing to `pgqueuer`, the two tables have no FK
    # between them. Without this, such a document gets a second job alongside
    # the untouched first one and is embedded twice. Same reasoning as
    # `app/queue.py`'s enqueue_document, just for the whole corpus at once
    # instead of one payload.
    await db.execute(
        text(
            "DELETE FROM pgqueuer WHERE entrypoint = 'process_document' AND status = 'queued'"
        )
    )

    for document_id in document_ids:
        payload = json.dumps({"document_id": str(document_id)}).encode()
        await db.execute(text(INSERT_JOB), {"payload": payload})

    print(f"{len(document_ids)} Dokument(e) für Re-Indexierung eingeplant.")


async def main() -> None:
    database_url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Through the same parser `persisted` gets, not built by hand: a bad
    # `.env` value (a typo'd EMBED_DIMENSIONS above 2000, an empty
    # EMBED_MODEL) would otherwise sail past this line and crash mid-DDL on a
    # raw Postgres error once the reconcile below tries to build an HNSW
    # index over it, instead of a clean, actionable rejection right here.
    configured = embedding_config_from(
        {"embed_model": settings.embed_model, "embed_dimensions": str(settings.embed_dimensions)}
    )

    async with session_factory() as db:
        await _reconcile(db, configured)
        await db.commit()

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
