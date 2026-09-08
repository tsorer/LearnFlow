r"""Persist the active embedding model and dimension in `config` (ADR-005, T-42)

Until now `EMBED_MODEL`/`EMBED_DIMENSIONS` (`app/config.py`) were process
settings only, read fresh by the worker on every embedding call
(`app/services/embedding.py`) with nothing recorded anywhere else. Changing
`EMBED_MODEL` to a different model of the *same* dimension is invisible to
Postgres -- pgvector only rejects a vector of the wrong length, and two
models sharing a dimension produce vectors that are individually valid and
mutually meaningless in the same HNSW index. That is the silent failure
ADR-008 exists to rule out, just one step upstream of the pipeline it
otherwise covers.

These two rows are the baseline a startup check (worker and API, added
alongside this migration) compares the running `Settings` against -- a
mismatch aborts the process rather than embedding new documents against an
index built for a different model. Seeded from `settings.embed_model`/
`embed_dimensions` at the moment this migration runs, not from a hardcoded
MVP literal: an installation already configured for a different provider on
its very first boot (Azure OpenAI EU, Ollama) gets a seed that already
matches, so the startup check passes the first time uvicorn starts. A
hardcoded MVP default here would instead crash-loop that installation on
`alembic upgrade head`'s own doing -- self-inflicted, since `api`'s command is
`alembic upgrade head && uvicorn ...` in the same container, and
`apply_embedding_config.py` would be the only documented way out despite
`docker-compose.yml` now gating the worker behind `api: service_healthy`,
which the crash-loop itself prevents. Reading `alembic/env.py` already
imports `app.config.settings` to build the migration engine's own connection,
so this adds no new coupling category, only a second read of the same
already-loaded object. `apply_embedding_config.py` remains the path for a
*later*, deliberate model change on an already-running installation -- it is
no longer needed just to match what `.env` already said on day one.

The CHECK constraint gets two more branches, same drop-and-recreate dance as
0009/0012/0014/0017:

* `embed_dimensions` joins the count keys but cannot reuse `POSITIVE_INTEGER`
  as-is -- ADR-005/ADR-003 cap it at 2000, the pgvector HNSW limit (AC4). A
  `value::int <= 2000` alongside the regex would risk the same evaluation-
  order trap the confidence thresholds avoid by staying regex-only (ADR-008,
  Nachtrag 2026-08-16): Postgres does not guarantee a `CASE`/`AND` evaluates
  left-to-right, so a non-numeric value could hit the cast before the regex
  short-circuits it, turning a constraint violation into a cast error.
  `^([1-9][0-9]{0,2}|1[0-9]{3}|2000)$` covers 1-999, 1000-1999 and exactly
  2000 without ever casting.
* `embed_model` gets its own branch (`\S`, non-empty) rather than falling
  into `ELSE true` -- unlike a threshold or a count, a model name has no
  numeric shape to check, but an empty string is not a model either, and the
  admin API (T-37 pattern) has no reader of its own to catch it first.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-05
"""

import sqlalchemy as sa

from alembic import op
from app.config import settings

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

CHECK_NAME = "ck_config_confidence_threshold_value"

# Unchanged from 0017 -- repeated rather than imported so this migration keeps
# describing the state it creates.
NUMERIC_UNIT_INTERVAL = r"^(0(\.[0-9]+)?|1(\.0+)?)$"
POSITIVE_INTEGER = r"^[1-9][0-9]*$"
UNIT_INTERVAL_KEYS = (
    "confidence_threshold_high",
    "confidence_threshold_medium",
    "similarity_threshold",
    "min_retrieval_confidence",
    "min_citation_coverage",
    "self_check_band_low",
    "self_check_band_high",
)
COUNT_KEYS = ("retrieval_top_k", "context_top_n", "rrf_k", "processing_timeout_seconds",
              "processing_max_attempts")

# 1-999, 1000-1999, 2000 -- see module docstring for why this stays a regex
# instead of a cast-and-compare.
EMBED_DIMENSIONS_RANGE = r"^([1-9][0-9]{0,2}|1[0-9]{3}|2000)$"
NON_EMPTY = r"\S"

def _rows() -> list[tuple[str, str, str]]:
    """Read at upgrade time, not module-import time, even though `settings` is
    already resolved by then (`alembic/env.py` imports it before any revision
    loads) -- keeps the side effect visibly inside the function that has one."""
    return [
        (
            "embed_model",
            settings.embed_model,
            "Active embedding model; a mismatch against Settings aborts startup (ADR-005, T-42)",
        ),
        (
            "embed_dimensions",
            str(settings.embed_dimensions),
            "Active embedding dimension, <= 2000 (pgvector HNSW limit, ADR-003/ADR-005, T-42)",
        ),
    ]


def _quoted(keys: tuple[str, ...]) -> str:
    return ", ".join(f"'{key}'" for key in keys)


def _check() -> str:
    return (
        f"ALTER TABLE config ADD CONSTRAINT {CHECK_NAME} CHECK ("
        "  CASE"
        f"    WHEN key IN ({_quoted(UNIT_INTERVAL_KEYS)})"
        f"    THEN value ~ '{NUMERIC_UNIT_INTERVAL}'"
        f"    WHEN key IN ({_quoted(COUNT_KEYS)})"
        f"    THEN value ~ '{POSITIVE_INTEGER}'"
        "    WHEN key = 'embed_dimensions'"
        f"    THEN value ~ '{EMBED_DIMENSIONS_RANGE}'"
        "    WHEN key = 'embed_model'"
        f"    THEN value ~ '{NON_EMPTY}'"
        "    ELSE true"
        "  END"
        ")"
    )


def _check_without_embedding_keys() -> str:
    """The 0017 constraint, for downgrade -- repeated rather than imported for
    the same reason 0017 repeated 0012's list instead of importing it."""
    return (
        f"ALTER TABLE config ADD CONSTRAINT {CHECK_NAME} CHECK ("
        "  CASE"
        f"    WHEN key IN ({_quoted(UNIT_INTERVAL_KEYS)})"
        f"    THEN value ~ '{NUMERIC_UNIT_INTERVAL}'"
        f"    WHEN key IN ({_quoted(COUNT_KEYS)})"
        f"    THEN value ~ '{POSITIVE_INTEGER}'"
        "    ELSE true"
        "  END"
        ")"
    )


def upgrade() -> None:
    # Same reason as 0017: Alembic runs the upgrade in one transaction, and a
    # fresh database still has the 0014 band-order trigger's events pending
    # when this revision starts -- Postgres refuses to ALTER a table with
    # pending trigger events.
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))

    # Constraint first, rows second -- same ordering as 0017 and for the same
    # reason: `config` has a foreign key to `users`, so inserting first would
    # leave pending trigger events behind and Postgres would refuse the ALTER.
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(_check()))

    bind = op.get_bind()
    for key, value, description in _rows():
        bind.execute(
            sa.text(
                "INSERT INTO config (key, value, description) VALUES (:key, :value, :description)"
            ),
            {"key": key, "value": value, "description": description},
        )


def downgrade() -> None:
    op.execute(sa.text(f"ALTER TABLE config DROP CONSTRAINT IF EXISTS {CHECK_NAME}"))
    op.execute(sa.text(_check_without_embedding_keys()))
    op.execute(sa.text("DELETE FROM config WHERE key IN ('embed_model', 'embed_dimensions')"))
    op.execute(sa.text("SET CONSTRAINTS ALL IMMEDIATE"))
