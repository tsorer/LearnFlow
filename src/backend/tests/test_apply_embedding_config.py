"""_reconcile() -- the reindex-triggering half of T-42 (ADR-005).

Exercised against a mocked AsyncSession rather than a real database: the
function's whole point is to run exactly once, by hand, against a real
corpus (see `apply_embedding_config.py`'s module docstring) -- a live test
would delete real chunks and queue real embedding jobs. What is worth
verifying without that is the branching (no-op vs. model-only vs. dimension
change), the statements it issues and the *values* they carry, in the order
the docstring promises.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

import apply_embedding_config
from app.config import settings
from app.exceptions import EmbeddingConfigError
from app.services.embedding_config import EmbeddingConfig
from apply_embedding_config import _reconcile


def sql(call: Any) -> str:
    """The rendered SQL text of one db.execute(...) call."""
    return str(call.args[0])


def bound(call: Any) -> dict[str, Any]:
    """The parameters bound to one db.execute(...) call, if any.

    Checking the SQL text alone only proves a statement of the right *shape*
    ran -- it still contains the literal `:value` placeholder even if the
    wrong Python value got bound to it. A swapped `persisted`/`configured`
    argument would pass every text-only assertion and still write the old
    value back.
    """
    return call.args[1] if len(call.args) > 1 else {}


def make_db(
    config_rows: list[tuple[str, str]], document_ids: list[str] = []  # noqa: B006
) -> AsyncMock:
    """A session whose execute() answers the SELECT and the requeue RETURNING
    in order; every other call (UPDATE/DELETE/INSERT/DDL) gets a bare mock."""
    config_result = MagicMock()
    config_result.all.return_value = config_rows

    documents_result = MagicMock()
    documents_result.scalars.return_value.all.return_value = document_ids

    db = AsyncMock()

    def execute(clause: Any, params: Any = None) -> Any:
        text = str(clause)
        if "SELECT key, value FROM config" in text:
            return config_result
        if "UPDATE documents" in text:
            return documents_result
        return MagicMock()

    db.execute.side_effect = execute
    return db


MATCHING_ROWS = [("embed_model", "text-embedding-3-small"), ("embed_dimensions", "1536")]
MATCHING_CONFIG = EmbeddingConfig(model="text-embedding-3-small", dimensions=1536)


async def test_matching_configuration_is_a_no_op() -> None:
    db = make_db(MATCHING_ROWS)

    await _reconcile(db, MATCHING_CONFIG)

    # Only the initial read -- no UPDATE, DELETE, INSERT or DDL statement.
    assert db.execute.await_count == 1


async def test_model_change_with_same_dimension_skips_the_schema_change() -> None:
    """The bug Issue #68 describes: two models sharing a dimension. No DDL is
    needed, only the config rows and the requeue."""
    db = make_db(MATCHING_ROWS, document_ids=["11111111-1111-1111-1111-111111111111"])
    configured = EmbeddingConfig(model="text-embedding-3-large", dimensions=1536)

    await _reconcile(db, configured)

    calls = db.execute.await_args_list
    statements = [sql(call) for call in calls]
    assert not any("ALTER TABLE chunks" in s or "DROP INDEX" in s for s in statements)

    model_update = next(c for c in calls if "key = 'embed_model'" in sql(c))
    assert bound(model_update)["value"] == "text-embedding-3-large"
    dimensions_update = next(c for c in calls if "key = 'embed_dimensions'" in sql(c))
    assert bound(dimensions_update)["value"] == "1536"

    assert any("UPDATE documents SET status = 'pending'" in s for s in statements)
    assert any("DELETE FROM chunks" in s for s in statements)
    assert any(
        "DELETE FROM pgqueuer WHERE entrypoint = 'process_document' AND status = 'queued'" in s
        for s in statements
    )
    insert_jobs = [c for c in calls if "INSERT INTO pgqueuer" in sql(c)]
    assert len(insert_jobs) == 1
    expected_payload = b'{"document_id": "11111111-1111-1111-1111-111111111111"}'
    assert bound(insert_jobs[0])["payload"] == expected_payload


async def test_pending_job_dedupe_delete_runs_before_the_new_jobs_are_queued() -> None:
    """A document already `pending` with an unconsumed `queued` job keeps that
    job across the UPDATE above -- `documents.status` and `pgqueuer` have no
    FK between them. Without this delete, such a document is embedded twice."""
    db = make_db(MATCHING_ROWS, document_ids=["11111111-1111-1111-1111-111111111111"])
    configured = EmbeddingConfig(model="text-embedding-3-large", dimensions=1536)

    await _reconcile(db, configured)

    statements = [sql(call) for call in db.execute.await_args_list]
    dedupe_index = next(
        i
        for i, s in enumerate(statements)
        if "DELETE FROM pgqueuer" in s and "status = 'queued'" in s
    )
    insert_index = next(i for i, s in enumerate(statements) if "INSERT INTO pgqueuer" in s)
    assert dedupe_index < insert_index


async def test_dimension_change_rebuilds_the_embedding_column_before_the_requeue() -> None:
    db = make_db(MATCHING_ROWS, document_ids=[])
    configured = EmbeddingConfig(model="bge-m3", dimensions=1024)

    await _reconcile(db, configured)

    statements = [sql(call) for call in db.execute.await_args_list]
    ddl_order = [
        i
        for i, s in enumerate(statements)
        if "DROP INDEX" in s or "DROP COLUMN" in s or "ADD COLUMN embedding vector(1024)" in s
    ]
    config_update_index = next(
        i for i, s in enumerate(statements) if "UPDATE config SET value" in s
    )
    assert len(ddl_order) == 3
    # Schema change happens before the config row is updated to the new
    # value -- a crash between the two must not leave `config` claiming a
    # dimension the column doesn't have yet.
    assert max(ddl_order) < config_update_index


async def test_multiple_documents_each_get_their_own_job() -> None:
    ids = [f"{n:08d}-0000-0000-0000-000000000000" for n in range(3)]
    db = make_db(MATCHING_ROWS, document_ids=ids)
    configured = EmbeddingConfig(model="text-embedding-3-large", dimensions=1536)

    await _reconcile(db, configured)

    statements = [sql(call) for call in db.execute.await_args_list]
    assert sum("INSERT INTO pgqueuer" in s for s in statements) == len(ids)


async def test_no_documents_means_no_jobs() -> None:
    db = make_db(MATCHING_ROWS, document_ids=[])
    configured = EmbeddingConfig(model="text-embedding-3-large", dimensions=1536)

    await _reconcile(db, configured)

    statements = [sql(call) for call in db.execute.await_args_list]
    assert sum("INSERT INTO pgqueuer" in s for s in statements) == 0


async def test_main_rejects_an_invalid_configured_dimension_before_touching_the_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A typo'd EMBED_DIMENSIONS must fail cleanly through the same parser
    `persisted` gets, not crash mid-ALTER on a raw Postgres error once
    _reconcile discovers it while building the HNSW index."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setattr(settings, "embed_dimensions", 99999)

    with pytest.raises(EmbeddingConfigError):
        await apply_embedding_config.main()
