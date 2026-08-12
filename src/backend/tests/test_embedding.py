from types import SimpleNamespace
from typing import Any

import pytest

from app.config import settings
from app.services.embedding import BATCH_SIZE, embed_texts

DIMENSIONS = 3


@pytest.fixture(autouse=True)
def small_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Three dimensions instead of 1536 — keeps the fixtures readable."""
    monkeypatch.setattr(settings, "embed_dimensions", DIMENSIONS)


def vector(seed: float, size: int = DIMENSIONS) -> list[float]:
    return [seed + offset for offset in range(size)]


def response(vectors: list[list[float]], indexes: list[int] | None = None) -> SimpleNamespace:
    positions = indexes if indexes is not None else list(range(len(vectors)))
    return SimpleNamespace(
        data=[
            {"index": position, "embedding": embedding}
            for position, embedding in zip(positions, vectors, strict=True)
        ]
    )


class Recorder:
    """Stands in for litellm.aembedding and records what it was called with."""

    def __init__(self, reply: Any = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._reply = reply

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._reply is not None:
            return self._reply
        return response([vector(float(i)) for i in range(len(kwargs["input"]))])

    @property
    def inputs(self) -> list[list[str]]:
        return [call["input"] for call in self.calls]


def patch_provider(monkeypatch: pytest.MonkeyPatch, fake: Any) -> None:
    monkeypatch.setattr("app.services.embedding.litellm.aembedding", fake)


async def test_returns_one_vector_per_text_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_provider(monkeypatch, Recorder(response([vector(10.0), vector(20.0)])))

    assert await embed_texts(["erster", "zweiter"]) == [vector(10.0), vector(20.0)]


async def test_splits_into_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)
    texts = [f"text {i}" for i in range(BATCH_SIZE * 2 + 2)]

    vectors = await embed_texts(texts)

    assert [len(batch) for batch in recorder.inputs] == [BATCH_SIZE, BATCH_SIZE, 2]
    # Every text is embedded exactly once and keeps its position across batches.
    assert [text for batch in recorder.inputs for text in batch] == texts
    assert len(vectors) == len(texts)


async def test_sorts_response_by_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """A provider may answer out of order — that must not shuffle the vectors,
    because the mix-up would surface as wrong citations, not as an error."""
    patch_provider(
        monkeypatch,
        Recorder(response([vector(20.0), vector(10.0)], indexes=[1, 0])),
    )

    assert await embed_texts(["erster", "zweiter"]) == [vector(10.0), vector(20.0)]


async def test_rejects_wrong_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_provider(monkeypatch, Recorder(response([vector(1.0, size=DIMENSIONS - 1)])))

    with pytest.raises(ValueError, match="Dimensionen"):
        await embed_texts(["erster"])


async def test_rejects_incomplete_response(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_provider(monkeypatch, Recorder(response([vector(1.0)])))

    with pytest.raises(ValueError, match="Vektoren"):
        await embed_texts(["erster", "zweiter"])


async def test_propagates_provider_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """No fallback, no empty vector: the job must fail so the document ends up
    in status 'failed' rather than silently unsearchable."""

    async def fail(**kwargs: Any) -> Any:
        raise RuntimeError("rate limit exceeded")

    patch_provider(monkeypatch, fail)

    with pytest.raises(RuntimeError, match="rate limit"):
        await embed_texts(["erster"])


async def test_passes_model_and_dimensions_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-005: model and dimension are configuration, not code."""
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)
    monkeypatch.setattr(settings, "embed_model", "text-embedding-3-large")

    await embed_texts(["erster"])

    call = recorder.calls[0]
    assert call["model"] == "text-embedding-3-large"
    assert call["dimensions"] == DIMENSIONS
    assert call["timeout"] > 0
    assert call["num_retries"] > 0
    # Empty settings must not be forwarded as an empty api_base.
    assert call["api_base"] is None


async def test_falls_back_to_the_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Passed explicitly, not left to LiteLLM's environment lookup: outside
    docker compose nothing exports OPENAI_API_KEY into os.environ.
    """
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)
    monkeypatch.setattr(settings, "openai_api_key", "sk-openai")
    monkeypatch.setattr(settings, "litellm_api_key", "")

    await embed_texts(["erster"])

    assert recorder.calls[0]["api_key"] == "sk-openai"


async def test_litellm_key_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured gateway/Azure key wins over the OpenAI Direct one (ADR-004)."""
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)
    monkeypatch.setattr(settings, "openai_api_key", "sk-openai")
    monkeypatch.setattr(settings, "litellm_api_key", "sk-gateway")

    await embed_texts(["erster"])

    assert recorder.calls[0]["api_key"] == "sk-gateway"


async def test_without_texts_makes_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty input list is a 400 at the provider — never send it."""
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)

    assert await embed_texts([]) == []
    assert recorder.calls == []
