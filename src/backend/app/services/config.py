"""Runtime thresholds read from the `config` table (ADR-007/ADR-008, T-24).

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

DEFAULT_SIMILARITY_THRESHOLD = 0.35
DEFAULT_MIN_RETRIEVAL_CONFIDENCE = 0.40
DEFAULT_MIN_CITATION_COVERAGE = 0.50
# Deliberately the same start value as DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM: the
# lower edge of the trigger band is the suppression threshold itself, so the
# weakest answers that still ship are the first ones stage 3 sees. A higher
# value would leave a gap in which an answer is delivered *and* skips the check
# — fail-open in exactly the range ADR-008 worries about. The two keys stay
# separate because they are calibrated against different things, but they start
# aligned (ADR-008, Nachtrag 2026-08-22).
DEFAULT_SELF_CHECK_BAND_LOW = 0.45
DEFAULT_SELF_CHECK_BAND_HIGH = 0.75
DEFAULT_RETRIEVAL_TOP_K = 20
DEFAULT_CONTEXT_TOP_N = 5
DEFAULT_RRF_K = 60

PIPELINE_KEYS = (
    "similarity_threshold",
    "min_retrieval_confidence",
    "min_citation_coverage",
    "self_check_band_low",
    "self_check_band_high",
    "retrieval_top_k",
    "context_top_n",
    "rrf_k",
)


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


def _thresholds_from(values: dict[str, str]) -> ConfidenceThresholds:
    """Build the band limits from already-fetched rows.

    Pure, so the rules below are testable without a session and so the fetch
    can be shared with the pipeline parameters (one round-trip, see
    read_query_config).

    Raises:
        ConfigurationError: a row is present but not a usable threshold.
    """
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


@dataclass(frozen=True)
class PipelineConfig:
    """Retrieval parameters (ADR-007) and stage thresholds (ADR-008).

    Retrieval and the gates it feeds are read together because one request
    needs all of them and they are all rows of the same table — splitting them
    into two readers would buy nothing but a second round-trip.
    `min_citation_coverage` is the stage-2 threshold (T-19). Like the others it
    is surfaced in the admin debug view even when its stage did not run — an
    operator calibrating the pipeline needs to see every threshold, not just the
    ones that fired on this request.

    `self_check_band_low` / `_high` bound the range in which stage 3 runs at all
    (T-25): below it the answer is suppressed anyway, above it the footing is
    clear enough that a second LLM call buys nothing.

    All values are hypotheses to be calibrated against the eval dataset
    (ADR-009), which is exactly why they live in `config` and not in Settings.
    """

    similarity_threshold: float
    min_retrieval_confidence: float
    min_citation_coverage: float
    self_check_band_low: float
    self_check_band_high: float
    retrieval_top_k: int
    context_top_n: int
    rrf_k: int


def _pipeline_from(values: dict[str, str]) -> PipelineConfig:
    """Build the retrieval and gate parameters from already-fetched rows.

    Raises:
        ConfigurationError: a row is present but not a usable parameter.
    """
    band_low = _as_threshold(values, "self_check_band_low", DEFAULT_SELF_CHECK_BAND_LOW)
    band_high = _as_threshold(values, "self_check_band_high", DEFAULT_SELF_CHECK_BAND_HIGH)

    # An inverted band is not a milder setting, it is an empty one: no score can
    # be both at or above `high` and below `low`, so stage 3 would never run and
    # nothing would say so. Guarded by trg_config_self_check_band_order at write
    # time; reaching this means the rows were written past the database.
    if band_low > band_high:
        raise ConfigurationError(
            f"config: self_check_band_low ({band_low}) liegt über "
            f"self_check_band_high ({band_high})"
        )

    return PipelineConfig(
        similarity_threshold=_as_threshold(
            values, "similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD
        ),
        min_retrieval_confidence=_as_threshold(
            values, "min_retrieval_confidence", DEFAULT_MIN_RETRIEVAL_CONFIDENCE
        ),
        min_citation_coverage=_as_threshold(
            values, "min_citation_coverage", DEFAULT_MIN_CITATION_COVERAGE
        ),
        self_check_band_low=band_low,
        self_check_band_high=band_high,
        retrieval_top_k=_as_count(values, "retrieval_top_k", DEFAULT_RETRIEVAL_TOP_K),
        context_top_n=_as_count(values, "context_top_n", DEFAULT_CONTEXT_TOP_N),
        rrf_k=_as_count(values, "rrf_k", DEFAULT_RRF_K),
    )


@dataclass(frozen=True)
class QueryConfig:
    """Everything one /query request needs from the `config` table.

    The two halves stay separate types because they answer different questions —
    `pipeline` parametrises the stages, `thresholds` maps the resulting score to
    a band — but they are fetched together. Same table, no ordering dependency
    between them, one request needs both: two round-trips would be two for the
    price of one.
    """

    pipeline: PipelineConfig
    thresholds: ConfidenceThresholds


async def read_query_config(db: AsyncSession) -> QueryConfig:
    """Load the pipeline parameters and the band limits in a single round-trip.

    Deliberately uncached: a value changed via SQL or via the admin endpoint
    (T-37) takes effect on the very next request, no restart required. One
    ten-row lookup is irrelevant next to the embedding call it precedes.

    Raises:
        ConfigurationError: a row is present but not a usable value. Either half
            can raise, and the caller treats both the same way — an unusable
            threshold is answered with "Weiss ich nicht", never with a different
            one (ADR-008, Nachtrag 2026-08-16).
    """
    result = await db.execute(
        select(Config.key, Config.value).where(
            Config.key.in_(CONFIDENCE_THRESHOLD_KEYS + PIPELINE_KEYS)
        )
    )
    values: dict[str, str] = {key: value for key, value in result.all()}

    return QueryConfig(pipeline=_pipeline_from(values), thresholds=_thresholds_from(values))


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


def _as_count(values: dict[str, str], key: str, default: int) -> int:
    """The same contract as `_as_threshold`, for the counts (ADR-008, Nachtrag).

    Separate from the thresholds because the valid range differs — these are
    candidate counts and an RRF constant, not values in [0, 1] — but the
    fail-closed rule is identical: a missing row takes the default, a present
    but unusable one raises rather than silently retrieving with a different
    `top_k` than the operator asked for.
    """
    raw = values.get(key)
    if raw is None:
        logger.debug("config: %s nicht gesetzt — Default %s", key, default)
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"config: {key} ist keine ganze Zahl ({raw!r})") from exc

    if value < 1:
        raise ConfigurationError(f"config: {key} muss positiv sein ({raw!r})")

    return value
