import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pgqueuer.models import Job

from worker.main import process_document


def make_job(document_id: str) -> Job:
    now = datetime.now(UTC)
    return Job(
        id=1,
        priority=0,
        created=now,
        updated=now,
        heartbeat=now,
        execute_after=now,
        status="picked",
        entrypoint="process_document",
        payload=json.dumps({"document_id": document_id}).encode(),
        queue_manager_id=None,
        headers=None,
    )


async def test_process_document_sets_processing_then_available() -> None:
    document_id = str(uuid.uuid4())
    conn = AsyncMock()

    await process_document(conn, make_job(document_id))

    calls = [c.args for c in conn.execute.await_args_list]
    assert calls[0] == ("UPDATE documents SET status = 'processing' WHERE id = $1", document_id)
    assert calls[1] == ("UPDATE documents SET status = 'available' WHERE id = $1", document_id)


async def test_process_document_sets_failed_on_error() -> None:
    document_id = str(uuid.uuid4())
    conn = AsyncMock()
    conn.execute.side_effect = [None, RuntimeError("boom"), None]

    with pytest.raises(RuntimeError):
        await process_document(conn, make_job(document_id))

    calls = [c.args for c in conn.execute.await_args_list]
    assert calls[0] == ("UPDATE documents SET status = 'processing' WHERE id = $1", document_id)
    assert calls[2] == (
        "UPDATE documents SET status = 'failed', error_message = $2 WHERE id = $1",
        document_id,
        "boom",
    )
