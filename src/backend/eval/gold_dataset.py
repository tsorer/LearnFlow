"""T-28/T-22: loads questions and the corpus list from the consolidated
gold-eval dataset (T-47/T-48, #101) at LearningCorpus/gold-eval-dataset.yaml,
plus the corpus-indexed precondition shared by both gates built on it (the
out-of-corpus refusal-rate gate and the in-corpus latency measurement).

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
class InCorpusQuestion:
    id: str
    question: str


def load_in_corpus_questions() -> list[InCorpusQuestion]:
    """All `category: in_corpus` entries from the consolidated dataset.

    Unlike out_of_corpus questions, these produce real answers rather than
    refusals -- they reach retrieval and generation (and, in the self-check
    boundary band, stage 3's second provider call), which makes them the
    right question pool for a latency measurement (T-22, #29).
    """
    return [
        InCorpusQuestion(id=q["id"], question=q["question"])
        for q in _load()["questions"]
        if q["category"] == "in_corpus"
    ]


@dataclass(frozen=True)
class Corpus:
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
    return [Corpus(path=c["path"], filename=c["filename"]) for c in _load()["corpora"].values()]


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
    by_filename = {d["filename"]: d for d in r.json()}

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
