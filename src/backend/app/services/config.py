"""Runtime thresholds read from the `config` table (ADR-008, T-24).

The confidence band limits must be recalibratable without a deployment and
without a service restart (US-02, US-11), so they are read from the database
per request instead of being cached at startup — the same trade-off the worker
already makes for the chunking parameters. One extra round-trip on a two-row
lookup is irrelevant next to the LLM call it guards.

A *missing* row falls back to the module-level default: nobody asked for
anything else, and that is what the default is for. A row that is present but
unreadable is the opposite case — somebody wanted something and it went wrong —
and must not be answered with a different, looser value (ADR-008, Nachtrag
2026-08-16). Migration 0009 rejects such a value on the way in, on both write
paths; this reader raises if one ever gets past it.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Config

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE_THRESHOLD_HIGH = 0.75
DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM = 0.45

CONFIDENCE_THRESHOLD_KEYS = ("confidence_threshold_high", "confidence_threshold_medium")


class ConfigurationError(Exception):
    """A `config` row exists but cannot be used as the threshold it names.

    Not a runtime state to recover from but an operator error that the database
    constraints (migration 0009) should have caught at write time. The caller
    translates it into a suppressed answer ("Weiss ich nicht", T-26), never into
    a value — fail-closed means no answer, not a looser threshold.
    """


@dataclass(frozen=True)
class ConfidenceThresholds:
    """Band limits for the displayed composite confidence (ADR-008).

    Read as: score >= high -> 'Hoch', score >= medium -> 'Mittel',
    below medium -> suppressed.
    """

    high: float
    medium: float


async def read_confidence_thresholds(db: AsyncSession) -> ConfidenceThresholds:
    """Load the confidence band limits from `config`.

    Deliberately uncached: a threshold changed via SQL (or later via the admin
    endpoint, T-37) takes effect on the very next call, no restart required.

    Raises:
        ConfigurationError: a row is present but not a usable threshold.
    """
    result = await db.execute(
        select(Config.key, Config.value).where(Config.key.in_(CONFIDENCE_THRESHOLD_KEYS))
    )
    values: dict[str, str] = {key: value for key, value in result.all()}

    high = _as_threshold(values, "confidence_threshold_high", DEFAULT_CONFIDENCE_THRESHOLD_HIGH)
    medium = _as_threshold(
        values, "confidence_threshold_medium", DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM
    )

    # Inverted bands would let everything through as 'Hoch'. Guarded by
    # trg_config_confidence_band_order at write time; reaching this means the
    # rows were written past the database.
    if medium > high:
        raise ConfigurationError(
            f"config: confidence_threshold_medium ({medium}) liegt über "
            f"confidence_threshold_high ({high})"
        )

    return ConfidenceThresholds(high=high, medium=medium)


def _as_threshold(values: dict[str, str], key: str, default: float) -> float:
    raw = values.get(key)
    if raw is None:
        logger.debug("config: %s nicht gesetzt — Default %s", key, default)
        return default

    try:
        value = float(raw)
    except ValueError as exc:
        # '0,90' is the realistic case, not 'hoch': the docs are German and the
        # pilot checklist prescribes writing these values by hand in psql.
        raise ConfigurationError(f"config: {key} ist keine Zahl ({raw!r})") from exc

    if not 0.0 <= value <= 1.0:
        raise ConfigurationError(f"config: {key} liegt ausserhalb von [0, 1] ({raw!r})")

    return value
