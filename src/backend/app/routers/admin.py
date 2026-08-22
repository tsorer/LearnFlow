import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db
from app.models.tables import Config, User
from app.services.config import CONFIDENCE_THRESHOLD_KEYS, PIPELINE_KEYS

router = APIRouter(prefix="/admin", tags=["admin"])

# The writable whitelist is exactly the keys migration 0012's CHECK constraint
# validates — CONFIDENCE_THRESHOLD_KEYS and PIPELINE_KEYS are the same tuples
# app/services/config.py reads back, so a key added there gets a reader and a
# write path together. `chunk_size`/`chunk_overlap` are seeded (0007) but stay
# read-only here: a change only takes effect after a full re-indexing of the
# corpus (ADR-007), which contradicts this endpoint's "wirkt sofort ohne
# Neustart" contract (US-11). `stale_days` (0004, US-06) is likewise left out:
# it has neither a reader nor a DB-level value constraint yet, so there is
# nothing here to validate it against.
COUNT_KEYS = frozenset({"retrieval_top_k", "context_top_n", "rrf_k"})
WRITABLE_KEYS = frozenset(CONFIDENCE_THRESHOLD_KEYS) | frozenset(PIPELINE_KEYS)

# Mirrors migration 0012's regexes exactly (same trade-off as that migration's
# own comment: repeated rather than imported, so this file keeps describing
# the values it accepts even if the migration is squashed away later). This is
# a fast-fail for a friendly 422; the CHECK constraint and the deferred
# band-order trigger stay the actual authority underneath both write paths
# (ADR-008, Nachtrag 2026-08-16).
NUMERIC_UNIT_INTERVAL = re.compile(r"^(0(\.[0-9]+)?|1(\.0+)?)$")
POSITIVE_INTEGER = re.compile(r"^[1-9][0-9]*$")


class ConfigResponse(BaseModel):
    config: dict[str, str]


class ConfigUpdateRequest(BaseModel):
    config: dict[str, str]


async def _read_all(db: AsyncSession) -> ConfigResponse:
    result = await db.execute(select(Config.key, Config.value))
    return ConfigResponse(config={key: value for key, value in result.all()})


def _validate(key: str, value: str) -> str | None:
    """Returns a German, human-readable problem description, or None if valid."""
    if key not in WRITABLE_KEYS:
        return f"Unbekannter oder nicht schreibbarer Schlüssel: {key}"
    if key in COUNT_KEYS:
        if not POSITIVE_INTEGER.match(value):
            return f"{key} muss eine positive ganze Zahl sein ({value!r})"
    elif not NUMERIC_UNIT_INTERVAL.match(value):
        return f"{key} muss eine Zahl zwischen 0 und 1 sein ({value!r})"
    return None


@router.get("/config", dependencies=[Depends(require_admin)])
async def read_config(db: AsyncSession = Depends(get_db)) -> ConfigResponse:
    """Every row, not just the writable ones — an operator calibrating the
    pipeline needs to see `chunk_size`/`chunk_overlap`/`stale_days` too, even
    though PUT below won't accept changes to them.
    """
    return await _read_all(db)


@router.put("/config")
async def update_config(
    body: ConfigUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ConfigResponse:
    """Replaces the given keys; keys not mentioned are left untouched.

    Validated against the whitelist and its per-key value shape before any
    write, so a bad key in a multi-key request aborts the whole request
    instead of applying the good keys and rejecting only the bad one.
    """
    problems = [msg for key, value in body.config.items() if (msg := _validate(key, value))]
    if problems:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="; ".join(problems)
        )

    now = datetime.now(UTC)
    for key, value in body.config.items():
        # Every writable key is seeded by 0004/0007/0008, so this row always
        # exists; mutating the attached ORM object is enough to flush an
        # UPDATE on commit below. The None branch is unreachable in practice
        # and exists to satisfy strict typing on db.get's Optional return.
        row = await db.get(Config, key)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"config-Zeile fehlt für bekannten Schlüssel: {key}",
            )
        row.value = value
        row.changed_by = user.id
        row.changed_at = now

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        # The confidence band order (medium <= high) spans two rows and is
        # only enforced at commit by the deferred trigger (migration 0009) --
        # a request that changes just one of the two can still violate it.
        message = getattr(exc.orig, "message", None) or str(exc.orig)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message
        ) from exc

    return await _read_all(db)
