"""Embedding generation via LiteLLM (ADR-005, T-13).

Provider, model and dimension are configuration, not code: switching from
OpenAI Direct to Azure OpenAI EU (ADR-004) must not touch this module. Settings
are read per call so a changed model takes effect on the next job.

Batch size, timeout and retry count are operational constants and stay here
rather than in the config table: unlike chunk_size/chunk_overlap they do not
change retrieval quality, which is the criterion for that table (ADR-007).
"""

from typing import Any

import litellm

from app.config import settings
from app.exceptions import UserFacingError

# OpenAI caps one embeddings request at 300k tokens. At the ADR-007 chunk size
# of 512 tokens, 64 inputs are ~33k — enough headroom that raising chunk_size
# to 1024 in the calibration spike cannot invalidate the batch.
BATCH_SIZE = 64

# LiteLLM defaults to 600s. A hung connection would hold the pgqueuer job and
# its pooled database connection for ten minutes and leave the document stuck
# in 'processing'; a full batch normally returns in about a second.
TIMEOUT_SECONDS = 30.0

# Applies to retryable failures only (429, 5xx, timeouts) with backoff. An
# invalid key or an oversized input fails immediately, which is what T-13
# requires: the job must fail loudly instead of retrying its way into silence.
MAX_RETRIES = 2


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts in input order. Raises on any provider or response error."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        response = await litellm.aembedding(
            model=settings.embed_model,
            input=batch,
            dimensions=settings.embed_dimensions,
            # Per request, never as the global litellm.drop_params: that would
            # also silence unsupported parameters on the completion calls.
            # Dropping is safe here because _vectors_from rejects a vector of
            # unexpected length anyway.
            drop_params=True,
            # The defaults are "", and an empty string is not None to LiteLLM —
            # it would be used as the api_base and break the OpenAI Direct path.
            api_base=settings.litellm_base_url or None,
            api_version=settings.litellm_api_version or None,
            # Passed explicitly instead of relying on LiteLLM reading
            # OPENAI_API_KEY from the environment: pydantic-settings loads .env
            # into Settings without exporting to os.environ, so a worker started
            # outside docker compose (which does export it via env_file) would
            # fail to authenticate although the key sits in .env.
            api_key=settings.litellm_api_key or settings.openai_api_key,
            timeout=TIMEOUT_SECONDS,
            num_retries=MAX_RETRIES,
        )
        vectors.extend(_vectors_from(response, expected=len(batch)))
    return vectors


def _vectors_from(response: Any, expected: int) -> list[list[float]]:
    """Extract vectors from an embeddings response, ordered like the input."""
    # The response carries an `index` per item precisely because its order is
    # not guaranteed. Sorting is what keeps chunk N's vector on chunk N — a
    # mix-up would not raise, it would produce wrong citations at query time.
    items = sorted(response.data, key=lambda item: int(item["index"]))
    if len(items) != expected:
        raise UserFacingError(f"Embedding-Antwort enthält {len(items)} statt {expected} Vektoren")

    vectors = [[float(value) for value in item["embedding"]] for item in items]
    for vector in vectors:
        if len(vector) != settings.embed_dimensions:
            raise UserFacingError(
                f"Embedding hat {len(vector)} statt {settings.embed_dimensions} Dimensionen"
            )
    return vectors
