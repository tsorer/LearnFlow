"""Fail-closed startup guard: configured `Settings` vs. persisted `config` (ADR-005, T-42).

`EMBED_MODEL`/`EMBED_DIMENSIONS` (`app/config.py`) decide which vectors the
next document or query gets embedded with; migration 0018 persists the value
a prior startup accepted. The two are read independently and compared here
rather than trusted to stay in sync, because pgvector cannot catch the
dangerous case itself: it rejects a vector of the wrong *dimension*, but two
different models sharing a dimension (e.g. two 1536-dim OpenAI models)
produce vectors that are each individually valid and mutually meaningless in
the same HNSW index — the exact silent failure described in Issue #68 and
ruled out on principle by ADR-008.

Both the API and the worker call `verify_embedding_config` once at startup
(`app/main.py`, `worker/main.py`) and let a mismatch abort the process,
mirroring `Settings.validate_secrets()`'s fail-closed crash on a weak JWT
secret. There is no automatic recovery: accepting a changed value is a
deliberate operator action (`apply_embedding_config.py`), because it also
means re-indexing every document — not something either process should ever
do on its own during startup.

Known limitation: this only compares two *claims* about the dimension — what
`Settings` says and what `config` says — never the real width of
`chunks.embedding` itself (that column is pgvector-typed, fixed at creation,
and changed only by `apply_embedding_config.py`'s raw DDL, never through this
module). An `alembic downgrade` below migration 0018 followed by an
`alembic upgrade head` reseeds `config` with the MVP defaults while leaving
the column at whatever a prior reconciliation left it — the two `config` rows
and the physical column can drift apart with this check reporting no problem
at all, because both sides it *does* look at agree. Migrating below 0018 on a
database that has been through a real reconciliation should be followed by
re-running `apply_embedding_config.py` before trusting this check again.
"""

from dataclasses import dataclass

from app.exceptions import EmbeddingConfigError

EMBEDDING_CONFIG_KEYS = ("embed_model", "embed_dimensions")

# pgvector's HNSW index tops out at 2000 dimensions (ADR-003/ADR-005);
# migration 0018's CHECK constraint enforces the same bound on write.
MAX_EMBED_DIMENSIONS = 2000


@dataclass(frozen=True)
class EmbeddingConfig:
    """One side of the comparison this module exists for: either what
    `Settings` is configured to use right now, or what the `config` table
    says was last accepted (migration 0018 seeds it; `apply_embedding_config.py`
    updates it when an operator intentionally changes the model)."""

    model: str
    dimensions: int


def embedding_config_from(values: dict[str, str]) -> EmbeddingConfig:
    """Parse the two `config` rows already fetched by the caller.

    Unlike the confidence thresholds (`app/services/config.py`), a *missing*
    row is not answered with a default here: migration 0018 seeds both keys
    unconditionally, so any database that has run its migrations has them.
    A missing row means the migration has not run — not a case with a
    sensible default, so it fails closed the same way an unparsable value
    does.

    Raises:
        EmbeddingConfigError: a row is missing, or present but not a usable
            value. Migration 0018's CHECK constraint should keep the second
            case from ever reaching here — same defense-in-depth `_as_count`
            applies in `app/services/config.py` (ADR-008, Nachtrag 2026-08-16).
    """
    model = values.get("embed_model")
    if not model or not model.strip():
        raise EmbeddingConfigError("config: embed_model fehlt oder ist leer")
    # Stripped, not just validated as non-empty after stripping: comparing an
    # unstripped value against Settings' (already-clean) one in
    # verify_embedding_config would report a mismatch on whitespace alone —
    # a false-positive startup abort, not the drift T-42 exists to catch.
    model = model.strip()

    raw_dimensions = values.get("embed_dimensions")
    if raw_dimensions is None:
        raise EmbeddingConfigError("config: embed_dimensions fehlt")
    try:
        dimensions = int(raw_dimensions)
    except ValueError as exc:
        raise EmbeddingConfigError(
            f"config: embed_dimensions ist keine ganze Zahl ({raw_dimensions!r})"
        ) from exc
    if not 1 <= dimensions <= MAX_EMBED_DIMENSIONS:
        raise EmbeddingConfigError(
            f"config: embed_dimensions ausserhalb von [1, {MAX_EMBED_DIMENSIONS}] "
            f"({raw_dimensions!r})"
        )

    return EmbeddingConfig(model=model, dimensions=dimensions)


def verify_embedding_config(persisted: EmbeddingConfig, configured: EmbeddingConfig) -> None:
    """Abort the caller's startup if `Settings` and `config` disagree.

    Pure on purpose (no DB access, no logging) so the decision itself is
    testable without a database — the two callers (`app/main.py`'s lifespan,
    `worker/main.py`'s `main()`) own fetching the rows and logging the
    failure.

    Raises:
        EmbeddingConfigError: `persisted != configured`. The message names
            both sides and the two ways to resolve it, since whoever reads
            this from a container log has no other context: run
            `apply_embedding_config.py` to accept the new value (and
            re-index every document under it), or revert
            `EMBED_MODEL`/`EMBED_DIMENSIONS` to match what's persisted.
    """
    if persisted != configured:
        raise EmbeddingConfigError(
            "Embedding-Konfiguration weicht ab: config-Tabelle sagt "
            f"{persisted.model} / {persisted.dimensions} Dimensionen, Settings verlangt "
            f"{configured.model} / {configured.dimensions} Dimensionen. Absichtlich "
            "geändert? apply_embedding_config.py ausführen — das übernimmt den neuen "
            "Wert und stösst die Re-Indexierung aller Dokumente an. Nicht beabsichtigt? "
            "EMBED_MODEL/EMBED_DIMENSIONS auf den persistierten Wert zurücksetzen."
        )
