"""Runtime thresholds read from the `config` table (ADR-008, T-24).

The confidence band limits must be recalibratable without a deployment and
without a service restart (US-02, US-11), so they are read from the database
per request instead of being cached at startup — the same trade-off the worker
already makes for the chunking parameters. One extra round-trip on a two-row
lookup is irrelevant next to the LLM call it guards.

Every value keeps a module-level default: a missing or unreadable row must
never drop the pipeline to an unguarded threshold, so the code falls back to
the seeded start values (fail-closed, ADR-008).
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
    """
    result = await db.execute(
        select(Config.key, Config.value).where(Config.key.in_(CONFIDENCE_THRESHOLD_KEYS))
    )
    values: dict[str, str] = {key: value for key, value in result.all()}

    high = _as_float(values, "confidence_threshold_high", DEFAULT_CONFIDENCE_THRESHOLD_HIGH)
    medium = _as_float(values, "confidence_threshold_medium", DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM)

    # A typo that puts medium above high would silently invert the bands and
    # let low-confidence answers through — fall back to the known-good pair.
    if medium > high:
        logger.warning(
            "config: confidence_threshold_medium (%s) liegt über confidence_threshold_high (%s) "
            "— beide Defaults werden verwendet",
            medium,
            high,
        )
        return ConfidenceThresholds(
            high=DEFAULT_CONFIDENCE_THRESHOLD_HIGH,
            medium=DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM,
        )

    return ConfidenceThresholds(high=high, medium=medium)


def _as_float(values: dict[str, str], key: str, default: float) -> float:
    raw = values.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "config: %s hat keinen numerischen Wert (%r) — Default %s", key, raw, default
        )
        return default
