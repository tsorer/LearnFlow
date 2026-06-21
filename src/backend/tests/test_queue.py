"""Unit tests for the enqueue_document helper."""

import json
from unittest.mock import AsyncMock

from app.queue import enqueue_document


async def test_enqueue_document_executes_insert_and_notify() -> None:
    db = AsyncMock()

    await enqueue_document(db, "doc-123")

    assert db.execute.call_count == 2

    # First call: INSERT into pgqueuer
    first_call_kwargs = db.execute.call_args_list[0]
    payload_arg = first_call_kwargs[0][1]["payload"]
    assert json.loads(payload_arg) == {"document_id": "doc-123"}

    # Second call: pg_notify
    second_call_sql = str(db.execute.call_args_list[1][0][0])
    assert "pg_notify" in second_call_sql
