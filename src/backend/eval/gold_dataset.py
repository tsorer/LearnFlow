"""T-28/T-22/T-56: loads questions and the corpus list from the consolidated
gold-eval dataset (T-47/T-48, #101) at LearningCorpus/gold-eval-dataset.yaml,
plus the corpus-indexed precondition shared by every gate built on it (the
out-of-corpus refusal-rate gate, the in-corpus latency measurement, and the
in-corpus quality gates).

Loadability, unique ids, and the declared field set are already guaranteed by
`tests/test_gold_eval_dataset.py` (same directory depth as this file, so the
same walk-up logic applies) — this loader does not re-check those, only
projects the dataset to what each ticket's gate needs.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    import httpx

DATASET_NAME = "gold-eval-dataset.yaml"


def _corpus_dir() -> pathlib.Path:
    """Walk up until LearningCorpus/ turns up.

    Mirrors tests/test_gold_eval_dataset.py::_corpus_dir(): src/backend/eval/
    and src/backend/tests/ sit at the same depth, so the same walk finds the
    repo-root LearningCorpus/ locally and the /LearningCorpus mount
    (docker-compose.yml) inside the api container.
    """
    here = pathlib.Path(__file__).resolve()
    for base in (here, *here.parents):
        candidate = base / "LearningCorpus"
        if (candidate / DATASET_NAME).is_file():
            return candidate
    raise AssertionError(
        f"{DATASET_NAME} not found. Outside CI the api container needs the "
        "LearningCorpus mount from docker-compose.yml."
    )


def _load() -> dict[str, Any]:
    path = _corpus_dir() / DATASET_NAME
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


@dataclass(frozen=True)
class OutOfCorpusQuestion:
    id: str
    question: str
    expected_refusal: bool


def load_out_of_corpus_questions() -> list[OutOfCorpusQuestion]:
    """All `category: out_of_corpus` entries from the consolidated dataset.

    No dedup check needed here (unlike the three-file version this replaced):
    id uniqueness across the whole file is already a CI-enforced invariant,
    test_gold_eval_dataset.py::test_question_ids_are_unique.
    """
    return [
        OutOfCorpusQuestion(
            id=q["id"],
            question=q["question"],
            expected_refusal=bool(q["expected_refusal"]),
        )
        for q in _load()["questions"]
        if q["category"] == "out_of_corpus"
    ]


@dataclass(frozen=True)
class ExpectedSource:
    """The Quellreferenz-Schema from the dataset header, projected to what
    the eval joins on: pages, not the prose `locator` (T-56 does not evaluate
    it, same as tests/test_gold_eval_dataset.py). All three corpora anchor on
    `pages` today (`anchor: pages` for every entry in `corpora`); a `.docx` or
    `.md` corpus using `headings` instead is not something this loader or
    eval/metrics.py handles yet -- out of scope until a corpus like that
    exists (see the dataset header's `anchor` note).
    """

    pages: tuple[int, ...]


def _expected_source(raw: dict[str, Any] | None) -> ExpectedSource | None:
    if raw is None:
        return None
    return ExpectedSource(pages=tuple(raw["pages"]))


@dataclass(frozen=True)
class InCorpusQuestion:
    id: str
    question: str
    corpus: str
    expected_source: ExpectedSource


def load_in_corpus_questions() -> list[InCorpusQuestion]:
    """All `category: in_corpus` entries from the consolidated dataset.

    Unlike out_of_corpus questions, these produce real answers rather than
    refusals -- they reach retrieval and generation (and, in the self-check
    boundary band, stage 3's second provider call), which makes them the
    right question pool for a latency measurement (T-22, #29) and, since
    T-56, for hallucination/false-suppression/context-recall.

    `corpus` and `expected_source` are additive since T-56: perf/ only reads
    `id`/`question`, and tests/test_gold_eval_dataset.py already guarantees
    every in_corpus entry carries a non-null `expected_source` with `pages`
    (never `headings`, matching `anchor: pages` for all three corpora today).
    """
    return [
        InCorpusQuestion(
            id=q["id"],
            question=q["question"],
            corpus=q["corpus"],
            # Never None for in_corpus -- enforced by
            # test_in_corpus_questions_name_a_source.
            expected_source=_expected_source(q["expected_source"]),  # type: ignore[arg-type]
        )
        for q in _load()["questions"]
        if q["category"] == "in_corpus"
    ]


@dataclass(frozen=True)
class AdversarialQuestion:
    id: str
    question: str
    corpus: str
    expected_refusal: bool
    #: None for the two entries that expect a refusal (SKOS-ADV-02,
    #: SKOS-IPV-02) -- a refusal has no source to score recall against,
    #: same as an out_of_corpus question (test_refusals_carry_no_answer_and_no_source).
    expected_source: ExpectedSource | None


def load_adversarial_questions() -> list[AdversarialQuestion]:
    """All `category: adversarial` entries (T-56): suggestive or ambiguous
    questions, mostly expecting a nuanced answer (`expected_refusal: false`,
    11 of 13) rather than the flat refusal out_of_corpus questions expect.
    Two entries (`expected_refusal: true`) test that a suggested wrong number
    or an out-of-scope detail gets refused rather than confirmed or invented.
    """
    return [
        AdversarialQuestion(
            id=q["id"],
            question=q["question"],
            corpus=q["corpus"],
            expected_refusal=bool(q["expected_refusal"]),
            expected_source=_expected_source(q["expected_source"]),
        )
        for q in _load()["questions"]
        if q["category"] == "adversarial"
    ]


@dataclass(frozen=True)
class Corpus:
    key: str
    path: str
    filename: str


def load_corpora() -> list[Corpus]:
    """The corpus PDFs the dataset's questions are written against.

    `path` (a file under LearningCorpus/) and `filename` (the upload identity
    in `documents`, T-15) are the same string today, but the schema keeps them
    apart on purpose (ADR-009, Quellreferenz-Schema) -- callers that upload or
    verify a corpus document should go through this rather than re-deriving
    the list from whatever happens to be in the directory.
    """
    return [
        Corpus(key=key, path=c["path"], filename=c["filename"])
        for key, c in _load()["corpora"].items()
    ]


def load_corpus_filenames() -> dict[str, str]:
    """`questions[].corpus` -> the upload filename, for joining a `Citation`
    or a `ChunkDebugInfo` entry back to the question that asked about it
    (T-56). A dict, not a re-filter of `load_corpora()` per call, because the
    in-corpus eval does this lookup once per question, ~58 times a run.
    """
    return {corpus.key: corpus.filename for corpus in load_corpora()}


def assert_documents_cover_the_corpus(documents: list[dict[str, Any]]) -> None:
    """The check itself, over an already-fetched `GET /api/documents` body.

    Split out from the two wrappers below so the rule lives once (T-55): the
    latency measurement still drives a synchronous client, while the refusal
    gate now runs in-process against the ASGI app and therefore awaits. Only
    the fetching differs; what counts as "indexed" must not.
    """
    by_filename = {d["filename"]: d for d in documents}

    missing = []
    for corpus in load_corpora():
        doc = by_filename.get(corpus.filename)
        if doc is None:
            missing.append(f"{corpus.filename}: not uploaded")
        elif doc["status"] != "available":
            missing.append(f"{corpus.filename}: status={doc['status']}")
    if missing:
        pytest.fail(
            "Corpus not fully indexed: " + "; ".join(missing) + ". Run `make seed-corpus` "
            "against the running stack first."
        )


def assert_corpus_is_indexed(client: httpx.Client, headers: dict[str, str]) -> None:
    """A measurement against the corpus is only meaningful if it was indexed.

    Without this, a dead worker or a `seed-corpus` that silently uploaded
    nothing looks identical to a working stack: every question would hit the
    retrieval gate instead of exercising retrieval/generation (review on
    #100, originally guarding the refusal-rate gate; T-22 reuses it because an
    unindexed corpus would make a latency measurement equally meaningless --
    every request would return in milliseconds via the gate, not seconds).
    """
    r = client.get("/api/documents", headers=headers)
    assert r.status_code == 200, r.text
    assert_documents_cover_the_corpus(r.json())


async def assert_corpus_is_indexed_async(
    client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    """Same precondition for the in-process eval client (T-55)."""
    r = await client.get("/api/documents", headers=headers)
    assert r.status_code == 200, r.text
    assert_documents_cover_the_corpus(r.json())
