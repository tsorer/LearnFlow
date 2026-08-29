"""T-28: loads the `out_of_corpus` questions from the three Gold-Eval-Dataset
seed files in LearningCorpus/.

There is no single consolidated dataset yet — T-47 (#95) tracks merging the three
files and, more importantly, deciding a source-reference schema that survives
re-indexing. That problem does not touch this loader: out-of-corpus entries carry
no `expected_source_id` (there is no source to reference), so reading all three
files directly here means T-28 does not wait on T-47. Once the consolidated file
exists, only `_SOURCE_FILES` needs to change.

Fachlich noch nicht abgenommen (T-48, #96) — the refusal expectation itself is
trivial ("this is not in any of the three corpora"), so that review matters far
less here than for `in_corpus` reference answers.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CORPUS_DIR = Path(os.environ.get("LEARNING_CORPUS_DIR", "/learning-corpus"))

# One Markdown file per author with an embedded ```yaml fence; Christoph's set is
# also checked in as a plain YAML file, which is simpler to parse directly.
_SOURCE_FILES = [
    CORPUS_DIR / "Eval-Gold-Dataset-Frank.md",
    CORPUS_DIR / "Eval-Gold-Dataset-Reto.md",
    CORPUS_DIR / "Eval_Gold-Dataset-Christoph.yaml",
]

_YAML_FENCE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)


@dataclass(frozen=True)
class OutOfCorpusQuestion:
    id: str
    question: str
    expected_refusal: bool
    source_file: str


def _entries(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".yaml":
        raw = text
    else:
        match = _YAML_FENCE.search(text)
        if match is None:
            raise ValueError(f"No ```yaml fence found in {path}")
        raw = match.group(1)
    entries = yaml.safe_load(raw)
    if not isinstance(entries, list):
        raise ValueError(f"{path} did not parse to a list of entries")
    return entries  # type: ignore[no-any-return]


def load_out_of_corpus_questions() -> list[OutOfCorpusQuestion]:
    """All `category: out_of_corpus` entries across the three seed files.

    Raises on a duplicate `id` across files — the three sets were written
    independently and are not guaranteed to have disjoint id spaces (T-47's
    problem in miniature), so a silent collision would drop a question.
    """
    questions: list[OutOfCorpusQuestion] = []
    seen_ids: dict[str, str] = {}
    for path in _SOURCE_FILES:
        for entry in _entries(path):
            if entry.get("category") != "out_of_corpus":
                continue
            entry_id = str(entry["id"])
            if entry_id in seen_ids:
                raise ValueError(
                    f"Duplicate question id {entry_id!r} in {path.name} "
                    f"(already seen in {seen_ids[entry_id]})"
                )
            seen_ids[entry_id] = path.name
            questions.append(
                OutOfCorpusQuestion(
                    id=entry_id,
                    question=str(entry["question"]),
                    expected_refusal=bool(entry["expected_refusal"]),
                    source_file=path.name,
                )
            )
    return questions
