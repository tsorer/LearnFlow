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


async def main() -> None:
    log.info("Worker starting — connecting to database")
    conn = await asyncpg.connect(settings.asyncpg_dsn)
    driver = AsyncpgDriver(conn)
    qm = QueueManager(driver)

    @qm.entrypoint("process_document")
    async def process_document(job: Job) -> None:
        payload = json.loads(job.payload or b"{}")
        document_id = payload.get("document_id")
        log.info("Processing document job_id=%s document_id=%s", job.id, document_id)
        # TODO (T-12): parsing + chunking
        # TODO (T-13): embedding + pgvector indexing

    log.info("Worker ready — listening for jobs")
    await qm.run()


if __name__ == "__main__":
    asyncio.run(main())
