"""pgqueuer integration — enqueue helper for the API Server."""

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def enqueue_document(db: AsyncSession, document_id: str) -> None:
    payload = json.dumps({"document_id": document_id}).encode()
    # A replacing upload (T-15) leaves the job of the version it replaced in the
    # queue. That job would re-read the document and index the new content a
    # second time — the same result at the price of a second embedding run over
    # the whole document. Only jobs no worker has taken yet can be dropped;
    # 'picked' means the run is already under way.
    await db.execute(
        text("""
            DELETE FROM pgqueuer
             WHERE entrypoint = 'process_document'
               AND status = 'queued'
               AND payload = :payload
        """),
        {"payload": payload},
    )
    await db.execute(
        text("""
            INSERT INTO pgqueuer (priority, created, updated, heartbeat, execute_after,
                                  status, entrypoint, payload)
            VALUES (0, now(), now(), now(), now(), 'queued', 'process_document', :payload)
        """),
        {"payload": payload},
    )
    # No pg_notify here: the tg_pgqueuer_changed trigger from migration 0001
    # already emits the table_changed_event JSON that pgqueuer's listener
    # expects. Sending the bare entrypoint name in addition made every upload
    # log a CRITICAL parse error in the worker.
