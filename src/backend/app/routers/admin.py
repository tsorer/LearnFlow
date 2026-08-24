import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
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
# nothing here to validate it against. Recorded in ADR-008's 2026-08-22
# Nachtrag, since issue #44 left this open for T-37 to decide.
COUNT_KEYS = frozenset({"retrieval_top_k", "context_top_n", "rrf_k"})
WRITABLE_KEYS = frozenset(CONFIDENCE_THRESHOLD_KEYS) | frozenset(PIPELINE_KEYS)

# Mirrors migration 0012's regexes exactly (same trade-off as that migration's
# own comment: repeated rather than imported, so this file keeps describing
# the values it accepts even if the migration is squashed away later). This is
# a fast-fail for a friendly 422; the CHECK constraint and the deferred
# band-order trigger stay the actual authority underneath both write paths
# (ADR-008, Nachtrag 2026-08-16). `fullmatch`, not `match`+`$`: Python's `$`
# also matches just before a trailing newline, Postgres' `~` does not — with
# `match` a value like "0.35\n" would pass here and then fail the CHECK with a
# raw DB error instead of this endpoint's friendly one.
NUMERIC_UNIT_INTERVAL = re.compile(r"^(0(\.[0-9]+)?|1(\.0+)?)$")
POSITIVE_INTEGER = re.compile(r"^[1-9][0-9]*$")

# check_violation — what both the per-row CHECK (0009/0012) and the deferred
# band-order trigger (0009) raise. Any other IntegrityError out of commit()
# (e.g. a FK violation on changed_by) is not this endpoint's to relabel as a
# client error; it propagates and becomes a 500.
CHECK_VIOLATION_SQLSTATE = "23514"


class ConfigResponse(BaseModel):
    config: dict[str, str]


class ConfigUpdateRequest(BaseModel):
    config: dict[str, str]


async def _read_all(db: AsyncSession) -> ConfigResponse:
    result = await db.execute(select(Config.key, Config.value))
    return ConfigResponse(config={key: value for key, value in result.all()})


def _validate_shape(key: str, value: str) -> str | None:
    """Value-shape check for a key already known to be writable."""
    if key in COUNT_KEYS:
        if not POSITIVE_INTEGER.fullmatch(value):
            return f"{key} muss eine positive ganze Zahl sein ({value!r})"
    elif not NUMERIC_UNIT_INTERVAL.fullmatch(value):
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

    The admin UI round-trips GET's whole response back through PUT
    (`ChatView.tsx`, `saveParams`), so every save carries the non-writable
    keys too, unchanged, even when the admin only meant to touch one
    threshold. Rejecting a non-writable key outright would 422 every single
    save. A non-writable key is therefore only an error if its value actually
    *differs* from what's currently stored — an unchanged pass-through is not
    a write and is silently accepted. A key absent from `config` entirely is
    always unknown and always 422s, whether or not it's on the whitelist.
    """
    result = await db.execute(
        select(Config.key, Config.value).where(Config.key.in_(body.config.keys()))
    )
    current = {key: value for key, value in result.all()}

    problems: list[str] = []
    to_write: dict[str, str] = {}
    for key, value in body.config.items():
        if key not in current:
            problems.append(f"Unbekannter Schlüssel: {key}")
        elif key in WRITABLE_KEYS:
            message = _validate_shape(key, value)
            if message:
                problems.append(message)
            else:
                to_write[key] = value
        elif value != current[key]:
            problems.append(f"Nicht schreibbarer Schlüssel: {key}")

    if problems:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="; ".join(problems)
        )

    now = datetime.now(UTC)
    for key, value in to_write.items():
        await db.execute(
            update(Config)
            .where(Config.key == key)
            .values(value=value, changed_by=user.id, changed_at=now)
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if getattr(exc.orig, "sqlstate", None) != CHECK_VIOLATION_SQLSTATE:
            raise
        # The confidence band order (medium <= high) spans two rows and is
        # only enforced at commit by the deferred trigger (migration 0009) --
        # a request that changes just one of the two can still violate it.
        message = getattr(exc.orig, "message", None) or str(exc.orig)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message
        ) from exc

    return await _read_all(db)
