import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.dml import Update as UpdateStatement
from sqlalchemy.sql.selectable import Select as SelectStatement

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import User

ADMIN_ID = uuid.uuid4()

TABLE = {
    "chunk_size": "512",
    "chunk_overlap": "64",
    "similarity_threshold": "0.35",
    "min_retrieval_confidence": "0.40",
    "min_citation_coverage": "0.50",
    "confidence_threshold_high": "0.75",
    "confidence_threshold_medium": "0.45",
    "stale_days": "90",
    "rrf_k": "60",
    "retrieval_top_k": "20",
    "context_top_n": "5",
    "processing_timeout_seconds": "900",
    "processing_max_attempts": "3",
}


def make_user(role: str) -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


class FakeCheckViolation(Exception):
    """Shaped like the asyncpg error migrations 0009/0012 raise: a `sqlstate`
    and a `message` attribute, both of which the router reads via getattr."""

    def __init__(self, message: str, sqlstate: str = "23514"):
        super().__init__(message)
        self.message = message
        self.sqlstate = sqlstate


def _integrity_error(orig: Exception) -> IntegrityError:
    return IntegrityError("UPDATE config ...", {}, orig)


def make_db(
    *, table: dict[str, str] | None = None, commit_error: Exception | None = None
) -> AsyncMock:
    """A session backed by an in-memory copy of the config table.

    SELECTs answer from it (unfiltered -- the router only ever looks up keys
    it asked for, so returning everything is equivalent and much simpler than
    reimplementing `.where(...in_(...))`). UPDATEs are applied to it via the
    statement's own bound params, so a GET-after-PUT within one test sees the
    write -- and so a test can assert exactly what was bound, the same way
    `tests/test_feedback_endpoint.py`'s `bound_params` does.
    """
    state = dict(table if table is not None else TABLE)
    updates: list[dict[str, object]] = []

    async def _execute(stmt: object) -> MagicMock:
        if isinstance(stmt, UpdateStatement):
            params = stmt.compile().params
            updates.append(params)
            key = params.get("key_1")
            if key is not None:
                state[str(key)] = str(params["value"])
            return MagicMock()
        assert isinstance(stmt, SelectStatement)
        result = MagicMock()
        result.all.return_value = list(state.items())
        return result

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=_execute)
    db.updates = updates  # type: ignore[attr-defined]
    if commit_error is not None:
        db.commit = AsyncMock(side_effect=commit_error)
    return db


async def _request(method: str, db: AsyncMock, role: str | None, **kwargs: object) -> object:
    if role is not None:
        app.dependency_overrides[get_current_user] = lambda: make_user(role)
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, "/admin/config", **kwargs)


async def _get_config(db: AsyncMock, role: str | None = "admin") -> object:
    return await _request("GET", db, role)


async def _put_config(body: dict, db: AsyncMock, role: str | None = "admin") -> object:
    return await _request("PUT", db, role, json=body)


# ---- GET -----------------------------------------------------------------


async def test_get_returns_every_row_including_non_writable_ones() -> None:
    db = make_db()

    r = await _get_config(db)

    assert r.status_code == 200
    body = r.json()
    assert body["config"]["chunk_size"] == "512"  # not writable, still readable
    assert body["config"]["stale_days"] == "90"  # no reader yet, still readable
    assert body["config"]["confidence_threshold_high"] == "0.75"


async def test_get_without_auth_returns_401() -> None:
    r = await _get_config(make_db(), role=None)
    assert r.status_code == 401


async def test_get_with_learner_role_returns_403() -> None:
    r = await _get_config(make_db(), role="learner")
    assert r.status_code == 403


# ---- PUT: success ----------------------------------------------------------


async def test_put_updates_value_and_fills_audit_fields() -> None:
    db = make_db()

    r = await _put_config({"config": {"confidence_threshold_high": "0.80"}}, db)

    assert r.status_code == 200
    db.commit.assert_awaited_once()
    assert len(db.updates) == 1
    params = db.updates[0]
    assert params["key_1"] == "confidence_threshold_high"
    assert params["value"] == "0.80"
    assert params["changed_by"] == ADMIN_ID
    assert params["changed_at"] is not None


async def test_put_returns_the_full_config_after_the_change() -> None:
    db = make_db()

    r = await _put_config({"config": {"rrf_k": "80"}}, db)

    assert r.json()["config"]["rrf_k"] == "80"
    assert r.json()["config"]["chunk_size"] == "512"  # untouched keys still reported


async def test_put_accepts_a_positive_integer_count_key() -> None:
    db = make_db()

    r = await _put_config({"config": {"retrieval_top_k": "30"}}, db)

    assert r.status_code == 200
    assert db.updates[0]["value"] == "30"


async def test_put_accepts_the_reaper_keys() -> None:
    """0017 put both reaper keys under the same CHECK, and the whitelist here is
    meant to be exactly that set (T-43). They are counts, not thresholds — a
    timeout of 900 would fail the unit-interval shape every non-count key gets.
    """
    db = make_db()

    r = await _put_config(
        {"config": {"processing_timeout_seconds": "900", "processing_max_attempts": "5"}}, db
    )

    assert r.status_code == 200
    assert [update["value"] for update in db.updates] == ["900", "5"]


async def test_put_rejects_a_reaper_key_that_is_not_a_positive_integer() -> None:
    db = make_db()

    r = await _put_config({"config": {"processing_max_attempts": "0"}}, db)

    assert r.status_code == 422


# ---- PUT: the round-trip fix (blocker from review) -------------------------
#
# ChatView.tsx's saveParams loads GET's whole response into form state and
# sends it back unchanged on every save (`api.getConfig` -> `params` ->
# `api.updateConfig(params, ...)`). Rejecting a non-writable key outright,
# regardless of its value, meant every real save 422'd on chunk_size /
# chunk_overlap / stale_days -- the write the admin actually asked for never
# happened. These are the cases that fix covers.


async def test_put_passes_through_an_unchanged_non_writable_key() -> None:
    db = make_db()

    r = await _put_config(
        {"config": {"confidence_threshold_high": "0.80", "chunk_size": "512"}}, db
    )

    assert r.status_code == 200
    # Only the writable key was actually written -- chunk_size was a no-op.
    assert len(db.updates) == 1
    assert db.updates[0]["key_1"] == "confidence_threshold_high"


async def test_put_rejects_a_real_change_to_a_non_writable_key() -> None:
    db = make_db()

    r = await _put_config({"config": {"chunk_size": "1024"}}, db)

    assert r.status_code == 422
    assert db.updates == []
    db.commit.assert_not_called()


async def test_put_rejects_a_real_change_to_stale_days() -> None:
    """No reader and no DB-level value constraint exist for it yet (US-06 is
    unbuilt) -- nothing to validate an actual change against."""
    db = make_db()

    r = await _put_config({"config": {"stale_days": "30"}}, db)

    assert r.status_code == 422
    assert db.updates == []


async def test_put_passes_through_an_unchanged_stale_days() -> None:
    db = make_db()

    r = await _put_config(
        {"config": {"confidence_threshold_high": "0.80", "stale_days": "90"}}, db
    )

    assert r.status_code == 200
    assert len(db.updates) == 1


# ---- PUT: rejected keys / values --------------------------------------------


async def test_put_unknown_key_returns_422_and_writes_nothing() -> None:
    db = make_db()

    r = await _put_config({"config": {"does_not_exist": "1"}}, db)

    assert r.status_code == 422
    assert db.updates == []
    db.commit.assert_not_called()


async def test_put_threshold_value_outside_unit_interval_returns_422() -> None:
    db = make_db()

    r = await _put_config({"config": {"confidence_threshold_high": "1.5"}}, db)

    assert r.status_code == 422
    assert db.updates == []


async def test_put_threshold_value_with_german_decimal_comma_returns_422() -> None:
    db = make_db()

    r = await _put_config({"config": {"similarity_threshold": "0,80"}}, db)

    assert r.status_code == 422


async def test_put_threshold_value_with_trailing_newline_returns_422() -> None:
    """Python's `$` matches just before a trailing newline; Postgres' `~`
    (migration 0012) does not -- `fullmatch` is what keeps this endpoint's
    check as strict as the one underneath it."""
    db = make_db()

    r = await _put_config({"config": {"similarity_threshold": "0.35\n"}}, db)

    assert r.status_code == 422


async def test_put_count_value_zero_returns_422() -> None:
    db = make_db()

    r = await _put_config({"config": {"retrieval_top_k": "0"}}, db)

    assert r.status_code == 422


async def test_put_count_value_non_numeric_returns_422() -> None:
    db = make_db()

    r = await _put_config({"config": {"rrf_k": "hoch"}}, db)

    assert r.status_code == 422


async def test_put_one_bad_key_among_several_rejects_the_whole_request() -> None:
    db = make_db()

    r = await _put_config(
        {"config": {"confidence_threshold_high": "0.80", "chunk_size": "1024"}}, db
    )

    assert r.status_code == 422
    assert db.updates == []  # nothing applied


# ---- PUT: the band-order invariant (issue #73, migration 0009) -------------


async def test_put_band_order_violation_from_the_db_trigger_returns_422() -> None:
    """Changing only `high` below the current `medium` is valid per this
    endpoint's own per-key checks -- only the deferred cross-row trigger in
    the database catches it, at commit."""
    orig = FakeCheckViolation(
        "confidence_threshold_medium (0.45) darf nicht über "
        "confidence_threshold_high (0.30) liegen"
    )
    db = make_db(commit_error=_integrity_error(orig))

    r = await _put_config({"config": {"confidence_threshold_high": "0.30"}}, db)

    assert r.status_code == 422
    assert "darf nicht über" in r.json()["detail"]
    db.rollback.assert_awaited_once()


async def test_put_unrelated_integrity_error_is_not_swallowed_as_422() -> None:
    """A FK violation on changed_by (e.g. the admin user got deleted
    concurrently) is a server-side problem, not a client mistake -- it must
    not be relabelled 422 with raw DB text. It is left to propagate (FastAPI's
    own error-handling middleware turns that into a 500 for a real client;
    here, going through ASGITransport in-process, it surfaces to the caller
    directly rather than as a captured response)."""
    orig = FakeCheckViolation("insert or update on table violates fk", sqlstate="23503")
    db = make_db(commit_error=_integrity_error(orig))

    with pytest.raises(IntegrityError):
        await _put_config({"config": {"confidence_threshold_high": "0.30"}}, db)

    db.rollback.assert_awaited_once()


# ---- PUT: auth ---------------------------------------------------------


async def test_put_without_auth_returns_401() -> None:
    r = await _put_config({"config": {"rrf_k": "70"}}, make_db(), role=None)
    assert r.status_code == 401


async def test_put_with_learner_role_returns_403() -> None:
    r = await _put_config({"config": {"rrf_k": "70"}}, make_db(), role="learner")
    assert r.status_code == 403
