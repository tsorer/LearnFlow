"""pgqueuer integration — enqueue helper for the API Server."""

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def enqueue_document(db: AsyncSession, document_id: str) -> None:
    payload = json.dumps({"document_id": document_id}).encode()
    await db.execute(
        text("""
            INSERT INTO pgqueuer (priority, created, updated, heartbeat, execute_after,
                                  status, entrypoint, payload)
            VALUES (0, now(), now(), now(), now(), 'queued', 'process_document', :payload)
        """),
        {"payload": payload},
    )
    await db.execute(text("SELECT pg_notify('ch_pgqueuer', 'process_document')"))
