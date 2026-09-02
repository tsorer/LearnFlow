"""T-28: loads the `out_of_corpus` questions from the consolidated gold-eval
dataset (T-47/T-48, #101) at LearningCorpus/gold-eval-dataset.yaml.

Loadability, unique ids, and the declared field set are already guaranteed by
`tests/test_gold_eval_dataset.py` (same directory depth as this file, so the
same walk-up logic applies) — this loader does not re-check those, only
filters to the category this ticket's gate measures.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

import yaml

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
    path = _corpus_dir() / DATASET_NAME
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return [
        OutOfCorpusQuestion(
            id=q["id"],
            question=q["question"],
            expected_refusal=bool(q["expected_refusal"]),
        )
        for q in data["questions"]
        if q["category"] == "out_of_corpus"
    ]
