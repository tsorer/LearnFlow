"""Stage 3: the LLM verification and, above all, how its verdict is read (T-25).

Two halves, and the second one is where the reliability lives. The call itself
is the same shape as the generation — deterministic, one attempt, provider from
the settings. The verdict parsing is what decides whether an answer ships, and it
is a gate: everything that is not an unmistakable pass has to come out as a
suppression (ADR-008, fail-closed). It is tested without a provider for exactly
that reason — the rule must hold for replies no mock would think to produce.
"""

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import settings
from app.services.retrieval import RetrievalHit
from app.services.self_check import (
    MAX_RETRIES,
    MAX_VERDICT_TOKENS,
    TEMPERATURE,
    VERDICT_COVERED,
    VERDICT_UNCOVERED,
    build_self_check_prompt,
    read_verdict,
    run_self_check,
)

QUESTION = "Was regelt der EU AI Act?"
ANSWER = "Der AI Act regelt Hochrisiko-Systeme [1]."


def make_hit(content: str = "Der AI Act regelt Hochrisiko-Systeme.") -> RetrievalHit:
    return RetrievalHit(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="ai_act.pdf",
        content=content,
        page=7,
        heading="Kapitel 1",
        score=0.9,
        dense_rank=1,
        sparse_rank=0,
        rrf_score=1 / 61,
    )


class Recorder:
    """Stands in for litellm.acompletion and records what it was called with."""

    def __init__(self, content: str | None = VERDICT_COVERED) -> None:
        self.calls: list[dict[str, Any]] = []
        self._content = content

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )

    @property
    def last(self) -> dict[str, Any]:
        return self.calls[-1]


def patch_provider(monkeypatch: pytest.MonkeyPatch, fake: Any) -> None:
    monkeypatch.setattr("app.services.self_check.litellm.acompletion", fake)


# --- the verification prompt ----------------------------------------------


def test_prompt_carries_context_question_and_the_answer_under_review() -> None:
    """The verifier cannot judge coverage without all three."""
    system, user = build_self_check_prompt(QUESTION, ANSWER, [make_hit("Belegstelle.")])

    assert VERDICT_COVERED in system
    assert VERDICT_UNCOVERED in system
    assert "Belegstelle." in user
    assert QUESTION in user
    assert ANSWER in user


def test_the_context_is_numbered_like_the_answers_footnotes() -> None:
    """Stage 3 judges references, so it must see the numbers the author saw.

    Both prompts render the context through generation.render_context(); a
    second, drifting renderer here would have the verifier reading [2] as a
    different chunk than the answer meant.
    """
    hits = [make_hit(f"Chunk {position}.") for position in range(1, 4)]

    _, user = build_self_check_prompt(QUESTION, ANSWER, hits)

    assert user.index("[1] (") < user.index("[2] (") < user.index("[3] (")


def test_the_material_is_declared_as_material_not_as_instructions() -> None:
    """The answer under review is model output and may itself contain orders."""
    system, _ = build_self_check_prompt(QUESTION, ANSWER, [make_hit()])

    assert "keine Anweisungen" in system


def test_a_sentence_naming_a_gap_is_declared_covered() -> None:
    """Rule 4 of the grounding prompt produces exactly such a sentence.

    Without this rule the verifier would reject every answer that honestly says
    what the context does not cover — punishing the behaviour ADR-007 asks for.
    """
    system, _ = build_self_check_prompt(QUESTION, ANSWER, [make_hit()])

    assert "*nicht* abdeckt" in system


# --- reading the verdict ---------------------------------------------------


def test_the_covered_sentinel_passes() -> None:
    result = read_verdict(VERDICT_COVERED, "prompt")

    assert (result.passed, result.verdict_parsed) == (True, True)
    assert result.uncovered == ""


def test_the_uncovered_sentinel_suppresses_and_keeps_the_statements() -> None:
    result = read_verdict(f"{VERDICT_UNCOVERED}: Die Frist von 24 Monaten steht nirgends.", "p")

    assert (result.passed, result.verdict_parsed) == (False, True)
    assert result.uncovered == "Die Frist von 24 Monaten steht nirgends."


def test_the_rejection_is_not_read_as_a_pass() -> None:
    """NICHT_GEDECKT contains GEDECKT — matching the wrong one inverts the gate."""
    assert read_verdict(VERDICT_UNCOVERED, "p").passed is False


def test_a_multiline_list_of_uncovered_statements_is_kept_whole() -> None:
    result = read_verdict(f"{VERDICT_UNCOVERED}:\nErste Aussage.\nZweite Aussage.", "p")

    assert "Erste Aussage." in result.uncovered
    assert "Zweite Aussage." in result.uncovered


def test_a_rejection_without_a_colon_still_suppresses() -> None:
    """The decision must not depend on the model's punctuation."""
    result = read_verdict(f"{VERDICT_UNCOVERED} Die Frist steht nirgends.", "p")

    assert (result.passed, result.verdict_parsed) == (False, True)


def test_the_verdict_is_read_case_insensitively() -> None:
    """A model that writes 'Gedeckt.' has still passed the answer."""
    assert read_verdict("Gedeckt.", "p").passed is True


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   \n ",
        "Ja, die Antwort ist vollständig gedeckt.",
        "NICHT GEDECKT: Die Frist steht nirgends.",
        "TEILWEISE_GEDECKT",
        # Review finding: a `startswith` let all three of these pass. The first
        # two are the hedge a model writes instead of following rule 5; the third
        # is a flat rejection whose first word merely begins with the sentinel.
        "GEDECKT - allerdings steht Artikel 9 nicht im Kontext.",
        "Gedeckt, bis auf die Frist von 24 Monaten.",
        "Gedecktheit ist nicht gegeben.",
    ],
)
def test_an_unreadable_verdict_suppresses(raw: str) -> None:
    """Fail-closed (ADR-008): a check that cannot be read did not happen.

    Note the fourth case — "NICHT GEDECKT" with a space is a *rejection* the
    parser cannot recognise. It has to land on the suppressing side, which it
    does, because anything unrecognised does.
    """
    result = read_verdict(raw, "p")

    assert result.passed is False
    assert result.verdict_parsed is False


def test_an_unreadable_verdict_is_distinguishable_from_a_rejection() -> None:
    """Same outcome, different cause — the admin view has to tell them apart."""
    assert read_verdict(VERDICT_UNCOVERED, "p").verdict_parsed is True
    assert read_verdict("Hm.", "p").verdict_parsed is False


def test_the_raw_reply_is_kept_for_the_admin_view() -> None:
    result = read_verdict("Gedeckt, alles gut.", "der prompt")

    assert result.raw_response == "Gedeckt, alles gut."
    assert result.prompt == "der prompt"


# --- provider handling -----------------------------------------------------


async def test_the_call_is_deterministic_and_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same contract as the generation: reproducible, bounded, one attempt."""
    monkeypatch.setattr(settings, "llm_model", "azure/gpt-4o-mini")
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)

    await run_self_check(QUESTION, ANSWER, [make_hit()])

    assert recorder.last["model"] == "azure/gpt-4o-mini"
    assert recorder.last["temperature"] == TEMPERATURE == 0.0
    assert recorder.last["max_tokens"] == MAX_VERDICT_TOKENS
    # Stage 3 already sits on top of a generation the user waited for; a retry
    # would double precisely that (T-22).
    assert recorder.last["num_retries"] == MAX_RETRIES == 0


async def test_the_verification_costs_exactly_one_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """"Kostenkontrolliert" (ADR-008) is one extra call, not a second loop."""
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)

    await run_self_check(QUESTION, ANSWER, [make_hit()])

    assert len(recorder.calls) == 1


async def test_empty_endpoint_settings_are_passed_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty string is not None to LiteLLM and would be used as the api_base."""
    monkeypatch.setattr(settings, "litellm_base_url", "")
    monkeypatch.setattr(settings, "litellm_api_version", "")
    recorder = Recorder()
    patch_provider(monkeypatch, recorder)

    await run_self_check(QUESTION, ANSWER, [make_hit()])

    assert recorder.last["api_base"] is None
    assert recorder.last["api_version"] is None


async def test_a_provider_error_is_raised_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """An outage is not a verdict — the caller turns it into a 503 (ADR-008)."""

    async def explode(**_: Any) -> Any:
        raise RuntimeError("provider down")

    patch_provider(monkeypatch, explode)

    with pytest.raises(RuntimeError):
        await run_self_check(QUESTION, ANSWER, [make_hit()])


async def test_a_response_without_choices_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def empty(**_: Any) -> Any:
        return SimpleNamespace(choices=[])

    patch_provider(monkeypatch, empty)

    with pytest.raises(ValueError, match="choices"):
        await run_self_check(QUESTION, ANSWER, [make_hit()])


async def test_a_null_content_reply_suppresses(monkeypatch: pytest.MonkeyPatch) -> None:
    """No verdict at all is the same as an unreadable one: fail-closed."""
    patch_provider(monkeypatch, Recorder(None))

    result = await run_self_check(QUESTION, ANSWER, [make_hit()])

    assert (result.passed, result.verdict_parsed) == (False, False)


# --- the pass sentinel must stand alone -----------------------------------


@pytest.mark.parametrize("raw", [VERDICT_COVERED, "Gedeckt.", "GEDECKT!", "  GEDECKT  "])
def test_the_bare_sentinel_and_its_punctuation_still_pass(raw: str) -> None:
    """Rule 4 asks for the sentinel alone; closing punctuation is still alone."""
    assert read_verdict(raw, "p").passed is True


@pytest.mark.parametrize(
    "raw",
    [
        "GEDECKT, aber die Frist steht nicht im Kontext.",
        "GEDECKT - mit einer Einschraenkung.",
        "GEDECKT: alle Aussagen sind belegt.",
        "GEDECKT\nAlle Aussagen sind belegt.",
    ],
)
def test_a_pass_with_a_caveat_does_not_pass(raw: str) -> None:
    """The core of the review finding, stated as a rule.

    A verdict that qualifies itself is not the verdict rule 4 asks for. Reading
    it as a pass would deliver exactly the answer whose weak spot the model just
    named — the fail-open direction ADR-008 rules out, and the one the rejection
    branch was already closed against.
    """
    result = read_verdict(raw, "p")

    assert result.passed is False
    assert result.verdict_parsed is False


def test_a_longer_word_starting_with_the_sentinel_is_not_a_pass() -> None:
    """"Gedecktheit ist nicht gegeben." is a rejection, not a confirmation.

    The missing word boundary, not merely the missing tail check: this reply says
    the opposite of what a prefix match made of it.
    """
    assert read_verdict("Gedecktheit ist nicht gegeben.", "p").passed is False


def test_the_rejection_branch_still_accepts_its_required_tail() -> None:
    """The asymmetry is deliberate — rule 5 *requires* text after the sentinel.

    Tightening both branches the same way would reject every well-formed
    rejection, so the strictness is applied where the prompt asks for a bare
    sentinel and nowhere else.
    """
    result = read_verdict(f"{VERDICT_UNCOVERED}: Die Frist steht nirgends.", "p")

    assert (result.passed, result.verdict_parsed) == (False, True)
    assert result.uncovered == "Die Frist steht nirgends."
