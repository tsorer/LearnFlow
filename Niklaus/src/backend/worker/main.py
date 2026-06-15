"""Background Worker — pgqueuer LISTEN/NOTIFY consumer."""

import asyncio
import logging

import asyncpg
from pgqueuer import QueueManager
from pgqueuer.db import AsyncpgDriver

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main():
    log.info("Worker starting — connecting to database")
    conn = await asyncpg.connect(settings.asyncpg_dsn)
    driver = AsyncpgDriver(conn)
    qm = QueueManager(driver)

    # TODO: register task handlers here
    # @qm.entrypoint("task_name")
    # async def handle_task(context): ...

    log.info("Worker ready — listening for jobs")
    await qm.run()


if __name__ == "__main__":
    asyncio.run(main())
