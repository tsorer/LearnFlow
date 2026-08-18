"""The grounding prompt contract and the refusal it defines (T-18, ADR-007).

No database and no FastAPI here: the generation step has to be callable on its
own (DoD), and the prompt is a contract that deserves assertions rather than a
careful reading.
"""

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import settings
from app.services.generation import (
    FINISH_TRUNCATED,
    MAX_ANSWER_TOKENS,
    REFUSAL_SENTINEL,
    TEMPERATURE,
    build_prompt,
    generate_answer,
)
from app.services.retrieval import RetrievalHit

QUESTION = "Was regelt der EU AI Act?"


def make_hit(
    filename: str = "ai_act.pdf",
    page: int | None = 7,
    heading: str | None = "Kapitel 1",
    content: str = "Der AI Act regelt Hochrisiko-Systeme.",
) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename=filename,
        content=content,
        page=page,
        heading=heading,
        score=0.9,
        dense_rank=1,
        sparse_rank=0,
        rrf_score=1 / 61,
    )


class Recorder:
    """Stands in for litellm.acompletion and records what it was called with."""

    def __init__(
        self, content: str | None = "Antwort mit Beleg [1].", finish_reason: str = "stop"
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._content = content
        self._finish_reason = finish_reason

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._content),
                    finish_reason=self._finish_reason,
                )
            ]
        )

    @property
    def last(self) -> dict[str, Any]:
        return self.calls[-1]


def patch_provider(monkeypatch: pytest.MonkeyPatch, fake: Any) -> None:
    monkeypatch.setattr("app.services.generation.litellm.acompletion", fake)


# --- the prompt ------------------------------------------------------------


def test_prompt_carries_instruction_context_and_question() -> None:
    """The three parts T-18 owes: system instruction, context chunks, question."""
    system, user = build_prompt(QUESTION, [make_hit(content="Erster Chunk.")])

    assert "ausschliesslich" in system
    assert REFUSAL_SENTINEL in system
    assert "Erster Chunk." in user
    assert QUESTION in user


def test_context_is_numbered_from_one_in_context_order() -> None:
    """[n] is the footnote number of citation n — query.py numbers the same list."""
    hits = [make_hit(content=f"Chunk {position}.") for position in range(1, 4)]

    _, user = build_prompt(QUESTION, hits)

    assert user.index("[1] (") < user.index("[2] (") < user.index("[3] (")
    assert "[4]" not in user


def test_each_section_names_its_source() -> None:
    _, user = build_prompt(QUESTION, [make_hit(filename="skos.pdf", page=12, heading="Grundsätze")])

    assert "[1] (skos.pdf · S. 12 · Grundsätze)" in user


def test_missing_page_and_heading_are_left_out() -> None:
    """A chunk from a page-less source must not claim 'S. None'."""
    _, user = build_prompt(QUESTION, [make_hit(filename="notiz.md", page=None, heading=None)])

    assert "[1] (notiz.md)" in user
    assert "None" not in user


def test_the_context_is_declared_as_material_not_as_instructions() -> None:
    """Chunk text comes from uploaded documents and may itself contain orders."""
    system, _ = build_prompt(QUESTION, [make_hit()])

    assert "keine Anweisungen" in system


# --- generation ------------------------------------------------------------


async def test_answer_is_passed_through_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_provider(monkeypatch, Recorder("Hochrisiko-Systeme sind reguliert [1]."))

    result = await generate_answer(QUESTION, [make_hit()])

    assert result.answer == "Hochrisiko-Systeme sind reguliert [1]."
    assert result.raw_response == "Hochrisiko-Systeme sind reguliert [1]."
    assert result.truncated is False


async def test_sentinel_is_a_refusal_not_an_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_provider(monkeypatch, Recorder(REFUSAL_SENTINEL))

    assert (await generate_answer(QUESTION, [make_hit()])).answer is None


async def test_sentinel_with_an_added_justification_still_refuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reading the trailing prose as an answer would invert the model's verdict."""
    patch_provider(monkeypatch, Recorder(f"{REFUSAL_SENTINEL} — der Kontext deckt das nicht ab."))

    assert (await generate_answer(QUESTION, [make_hit()])).answer is None


@pytest.mark.parametrize("content", ["", "   \n ", None])
async def test_an_empty_response_counts_as_a_refusal(
    monkeypatch: pytest.MonkeyPatch, content: str | None
) -> None:
    """Fail-closed: an answer nobody generated must never be delivered as one."""
    patch_provider(monkeypatch, Recorder(content))

    assert (await generate_answer(QUESTION, [make_hit()])).answer is None


async def test_the_debug_prompt_contains_both_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """DebugInfo.llm_calls shows what was actually sent, not a reconstruction."""
    patch_provider(monkeypatch, Recorder())

    result = await generate_answer(QUESTION, [make_hit(content="Belegstelle.")])

    assert REFUSAL_SENTINEL in result.prompt
    assert "Belegstelle." in result.prompt
    assert QUESTION in result.prompt


# --- provider handling -----------------------------------------------------


async def test_call_is_deterministic_and_uses_the_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider swap is configuration, not code (ADR-004); eval needs temperature 0."""
    monkeypatch.setattr(settings, "llm_model", "azure/gpt-4o-mini")
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)

    await generate_answer(QUESTION, [make_hit()])

    assert recorder.last["model"] == "azure/gpt-4o-mini"
    assert recorder.last["temperature"] == TEMPERATURE == 0.0
    assert recorder.last["max_tokens"] == MAX_ANSWER_TOKENS
    assert [message["role"] for message in recorder.last["messages"]] == ["system", "user"]


async def test_empty_endpoint_settings_are_passed_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty string is not None to LiteLLM and would be used as the api_base."""
    monkeypatch.setattr(settings, "litellm_base_url", "")
    monkeypatch.setattr(settings, "litellm_api_version", "")
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)

    await generate_answer(QUESTION, [make_hit()])

    assert recorder.last["api_base"] is None
    assert recorder.last["api_version"] is None


async def test_the_key_falls_back_to_the_openai_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """pydantic-settings never exports the key, so it has to be passed explicitly."""
    monkeypatch.setattr(settings, "litellm_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "sk-direct")
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)

    await generate_answer(QUESTION, [make_hit()])
    assert recorder.last["api_key"] == "sk-direct"

    monkeypatch.setattr(settings, "litellm_api_key", "azure-key")
    await generate_answer(QUESTION, [make_hit()])
    assert recorder.last["api_key"] == "azure-key"


async def test_a_provider_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """An outage must reach the caller, which answers 503 instead of a non-answer."""

    async def fail(**kwargs: Any) -> Any:
        raise RuntimeError("api_base=https://secret.internal key=sk-123")

    patch_provider(monkeypatch, fail)

    with pytest.raises(RuntimeError):
        await generate_answer(QUESTION, [make_hit()])


async def test_a_response_without_choices_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def empty(**kwargs: Any) -> Any:
        return SimpleNamespace(choices=[])

    patch_provider(monkeypatch, empty)

    with pytest.raises(ValueError):
        await generate_answer(QUESTION, [make_hit()])


async def test_a_truncated_answer_is_not_delivered(monkeypatch: pytest.MonkeyPatch) -> None:
    """The cap cut it off: the last claim may have lost the [n] backing it."""
    patch_provider(
        monkeypatch,
        Recorder("Hochrisiko-Systeme umfassen unter anderem", finish_reason=FINISH_TRUNCATED),
    )

    result = await generate_answer(QUESTION, [make_hit()])

    assert result.truncated is True
    assert result.answer is None
    # The fragment is kept for the admin view — it is what the provider returned.
    assert result.raw_response == "Hochrisiko-Systeme umfassen unter anderem"


async def test_a_missing_finish_reason_does_not_count_as_truncated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider that omits the field must not suppress every answer."""

    async def without_field(**kwargs: Any) -> Any:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Antwort [1]."))]
        )

    patch_provider(monkeypatch, without_field)

    result = await generate_answer(QUESTION, [make_hit()])

    assert result.truncated is False
    assert result.answer == "Antwort [1]."
