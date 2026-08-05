"""Background Worker — pgqueuer LISTEN/NOTIFY consumer."""

import asyncio
import json
import logging

import asyncpg
from pgqueuer import QueueManager
from pgqueuer.db import AsyncpgDriver
from pgqueuer.models import Job

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def process_document(conn: asyncpg.Connection, job: Job) -> None:
    payload = json.loads(job.payload or b"{}")
    document_id = payload.get("document_id")
    log.info("Processing document job_id=%s document_id=%s", job.id, document_id)

    await conn.execute("UPDATE documents SET status = 'processing' WHERE id = $1", document_id)
    try:
        # TODO (T-12): parsing + chunking
        # TODO (T-13): embedding + pgvector indexing
        await conn.execute("UPDATE documents SET status = 'available' WHERE id = $1", document_id)
    except Exception as exc:
        log.exception("Failed to process document_id=%s", document_id)
        await conn.execute(
            "UPDATE documents SET status = 'failed', error_message = $2 WHERE id = $1",
            document_id,
            str(exc),
        )
        raise


async def main() -> None:
    log.info("Worker starting — connecting to database")
    conn = await asyncpg.connect(settings.asyncpg_dsn)
    driver = AsyncpgDriver(conn)
    qm = QueueManager(driver)

    qm.entrypoint("process_document")(lambda job: process_document(conn, job))

    log.info("Worker ready — listening for jobs")
    await qm.run()


if __name__ == "__main__":
    asyncio.run(main())
