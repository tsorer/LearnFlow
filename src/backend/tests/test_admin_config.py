import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import Config, User

ADMIN_ID = uuid.uuid4()

ROWS_AFTER = (
    ("chunk_size", "512"),
    ("chunk_overlap", "64"),
    ("similarity_threshold", "0.35"),
    ("min_retrieval_confidence", "0.40"),
    ("min_citation_coverage", "0.50"),
    ("confidence_threshold_high", "0.80"),
    ("confidence_threshold_medium", "0.50"),
    ("stale_days", "90"),
    ("rrf_k", "60"),
    ("retrieval_top_k", "20"),
    ("context_top_n", "5"),
)


def make_user(role: str) -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def make_row(key: str, value: str) -> Config:
    return Config(key=key, value=value, description=None, changed_by=None, changed_at=None)


def make_result(rows: tuple) -> MagicMock:
    result = MagicMock()
    result.all.return_value = list(rows)
    return result


def make_db(
    *,
    rows: tuple = ROWS_AFTER,
    get_rows: dict[str, Config] | None = None,
    commit_error: Exception | None = None,
) -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=make_result(rows))

    async def _get(model: type, key: str) -> Config | None:
        assert model is Config
        return (get_rows or {}).get(key)

    db.get = AsyncMock(side_effect=_get)
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
    assert body["config"]["confidence_threshold_high"] == "0.80"


async def test_get_without_auth_returns_401() -> None:
    r = await _get_config(make_db(), role=None)
    assert r.status_code == 401


async def test_get_with_learner_role_returns_403() -> None:
    r = await _get_config(make_db(), role="learner")
    assert r.status_code == 403


# ---- PUT: success ----------------------------------------------------------


async def test_put_updates_value_and_fills_audit_fields() -> None:
    row = make_row("confidence_threshold_high", "0.75")
    db = make_db(get_rows={"confidence_threshold_high": row})

    r = await _put_config({"config": {"confidence_threshold_high": "0.80"}}, db)

    assert r.status_code == 200
    db.commit.assert_awaited_once()
    assert row.value == "0.80"
    assert row.changed_by == ADMIN_ID
    assert row.changed_at is not None


async def test_put_only_touches_the_keys_in_the_request() -> None:
    high = make_row("confidence_threshold_high", "0.75")
    db = make_db(get_rows={"confidence_threshold_high": high})

    await _put_config({"config": {"confidence_threshold_high": "0.80"}}, db)

    db.get.assert_awaited_once_with(Config, "confidence_threshold_high")


async def test_put_returns_the_full_config_after_the_change() -> None:
    row = make_row("rrf_k", "60")
    db = make_db(get_rows={"rrf_k": row}, rows=ROWS_AFTER)

    r = await _put_config({"config": {"rrf_k": "80"}}, db)

    assert r.json()["config"] == dict(ROWS_AFTER)


async def test_put_accepts_a_positive_integer_count_key() -> None:
    row = make_row("retrieval_top_k", "20")
    db = make_db(get_rows={"retrieval_top_k": row})

    r = await _put_config({"config": {"retrieval_top_k": "30"}}, db)

    assert r.status_code == 200
    assert row.value == "30"


# ---- PUT: rejected keys / values --------------------------------------------


async def test_put_unknown_key_returns_422_and_writes_nothing() -> None:
    db = make_db()

    r = await _put_config({"config": {"does_not_exist": "1"}}, db)

    assert r.status_code == 422
    db.get.assert_not_called()
    db.commit.assert_not_called()


async def test_put_chunk_size_is_rejected_despite_existing_in_the_table() -> None:
    """chunk_size only takes effect after a full re-index (ADR-007) -- it
    fails the "wirkt sofort ohne Neustart" contract, so it stays read-only."""
    db = make_db()

    r = await _put_config({"config": {"chunk_size": "1024"}}, db)

    assert r.status_code == 422
    db.get.assert_not_called()


async def test_put_stale_days_is_rejected() -> None:
    """No reader and no DB-level value constraint exist for it yet (US-06 is
    unbuilt) -- nothing to validate a write against."""
    db = make_db()

    r = await _put_config({"config": {"stale_days": "30"}}, db)

    assert r.status_code == 422


async def test_put_threshold_value_outside_unit_interval_returns_422() -> None:
    db = make_db()

    r = await _put_config({"config": {"confidence_threshold_high": "1.5"}}, db)

    assert r.status_code == 422
    db.get.assert_not_called()


async def test_put_threshold_value_with_german_decimal_comma_returns_422() -> None:
    db = make_db()

    r = await _put_config({"config": {"similarity_threshold": "0,80"}}, db)

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
    high = make_row("confidence_threshold_high", "0.75")
    db = make_db(get_rows={"confidence_threshold_high": high})

    r = await _put_config(
        {"config": {"confidence_threshold_high": "0.80", "chunk_size": "1024"}}, db
    )

    assert r.status_code == 422
    db.get.assert_not_called()
    assert high.value == "0.75"  # nothing applied


# ---- PUT: the band-order invariant (issue #73, migration 0009) -------------


async def test_put_band_order_violation_from_the_db_trigger_returns_422() -> None:
    """Changing only `high` below the current `medium` is valid per this
    endpoint's own per-key checks -- only the deferred cross-row trigger in
    the database catches it, at commit."""
    row = make_row("confidence_threshold_high", "0.75")
    orig = Exception(
        "confidence_threshold_medium (0.45) darf nicht über "
        "confidence_threshold_high (0.30) liegen"
    )
    db = make_db(
        get_rows={"confidence_threshold_high": row},
        commit_error=IntegrityError("UPDATE config ...", {}, orig),
    )

    r = await _put_config({"config": {"confidence_threshold_high": "0.30"}}, db)

    assert r.status_code == 422
    assert "darf nicht über" in r.json()["detail"]
    db.rollback.assert_awaited_once()


# ---- PUT: auth ---------------------------------------------------------


async def test_put_without_auth_returns_401() -> None:
    r = await _put_config({"config": {"rrf_k": "70"}}, make_db(), role=None)
    assert r.status_code == 401


async def test_put_with_learner_role_returns_403() -> None:
    r = await _put_config({"config": {"rrf_k": "70"}}, make_db(), role="learner")
    assert r.status_code == 403
