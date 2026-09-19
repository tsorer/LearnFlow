"""T-57: the stratified train/holdout split the calibration sweep measures against.

ADR-009's calibration loop needs a split that survives more than one run: a Zufallssplit
drawn fresh each time would let today's "holdout" leak into tomorrow's training data the
moment someone reruns `make calibrate`, and after the third run there would be no holdout
left at all. So the split is computed once (`_compute_holdout_ids` below, kept for
reproducibility and for the test that guards it) and the resulting question ids are
committed as `HOLDOUT_IDS`, a literal, not a function call.

Stratified by `(category, corpus)`, not by `category` alone: the two constraints the sweep
optimises under live on different question pools (Out-of-Corpus-Refusal on the 22
`out_of_corpus` questions, False-Suppression on the 45 `in_corpus` questions, ADR-009), and
each pool spans three corpora. A split that ignores `corpus` could put five of one corpus's
`in_corpus` questions in the holdout and none of another's, which would make a per-corpus
regression invisible in the reported numbers.

Roughly one third of each stratum goes to the holdout (`round(n / 3)`) — for the 45
`in_corpus` questions that is exactly 15 per corpus in training and 5 in holdout, 30/15
overall, the split size the issue's clarification comment reasons about explicitly. The
other two categories round the same way; see `test_calibrate_dataset.py` for the exact
counts per stratum.
"""

from __future__ import annotations

import random
from typing import TypeVar

from eval.gold_dataset import (
    AdversarialQuestion,
    InCorpusQuestion,
    OutOfCorpusQuestion,
    _load,
    load_adversarial_questions,
    load_in_corpus_questions,
    load_out_of_corpus_questions,
)

#: Fixed at generation time (see `_compute_holdout_ids`, seed `SEED` below) — not
#: recomputed on import. A question id that disappears from the dataset would silently drop
#: out of the intersection with "the current dataset" anywhere this is used; a question id
#: that the dataset later adds is not automatically in the holdout, which is the point (a
#: dataset change should not reshuffle who is being held out). `test_calibrate_dataset.py`
#: is the guard against drift between this literal and the live dataset.
HOLDOUT_IDS: frozenset[str] = frozenset(
    {
        "AIA-ADV-03",
        "AIA-ADV-04",
        "AIA-ANFORDERUNGEN-02",
        "AIA-DOKUMENT-01",
        "AIA-KMU-01",
        "AIA-OOC-03",
        "AIA-OOC-05",
        "AIA-PROTOKOLL-01",
        "AIA-RUECKRUF-01",
        "SAMW-ADV-03",
        "SAMW-BELMONT-01",
        "SAMW-BV118B-01",
        "SAMW-JUGENDLICHE-01",
        "SAMW-OOC-01",
        "SAMW-OOC-03",
        "SAMW-RISIKOKAT-01",
        "SAMW-SAETTIGUNG-01",
        "SKOS-ALI-01",
        "SKOS-EL-OOC-01",
        "SKOS-GBL-02",
        "SKOS-IPV-02",
        "SKOS-KV-01",
        "SKOS-KV-02",
        "SKOS-OOC-02",
        "SKOS-PRINZ-01",
        "SKOS-PRINZ-03",
    }
)

#: Named so `_compute_holdout_ids` is reproducible by inspection rather than by re-running
#: it against a snapshot of the dataset that may have moved on.
SEED = 57


def _compute_holdout_ids() -> frozenset[str]:
    """Recompute the stratified holdout from the *current* dataset.

    Not called anywhere in the sweep — `HOLDOUT_IDS` above is what the sweep actually
    uses. This function is the definition of how that literal was produced, and exists so
    the derivation is auditable code rather than a comment describing a one-off script.
    `test_calibrate_dataset.py::test_holdout_ids_match_a_fresh_stratified_split` calls it
    and asserts it reproduces `HOLDOUT_IDS` exactly, as long as the dataset itself has not
    changed shape.
    """
    ids_by_stratum: dict[tuple[str, str], list[str]] = {}
    for category, corpus, qid in _all_ids():
        ids_by_stratum.setdefault((category, corpus), []).append(qid)

    holdout: set[str] = set()
    for (category, corpus), ids in ids_by_stratum.items():
        pool = sorted(ids)
        n_holdout = round(len(pool) / 3)
        rng = random.Random(f"{SEED}:{category}:{corpus}")
        holdout.update(rng.sample(pool, n_holdout))
    return frozenset(holdout)


def _all_ids() -> list[tuple[str, str, str]]:
    """`(category, corpus, id)` for every question, straight from the raw dataset.

    Not via `load_out_of_corpus_questions()`: `OutOfCorpusQuestion` deliberately drops the
    dataset's `corpus` field (T-56's loader has no use for it, an out_of_corpus question
    answers no corpus), but the raw entries do carry one — every out_of_corpus question is
    still written *against* one of the three corpora, and stratifying on it keeps that pool
    balanced across corpora the same way `in_corpus`/`adversarial` are.
    """
    return [(q["category"], q["corpus"], q["id"]) for q in _load()["questions"]]


_Q = TypeVar("_Q", InCorpusQuestion, AdversarialQuestion, OutOfCorpusQuestion)


def split_in_corpus() -> tuple[list[InCorpusQuestion], list[InCorpusQuestion]]:
    """`(train, holdout)` for the 45 `in_corpus` questions."""
    return _split(load_in_corpus_questions())


def split_adversarial() -> tuple[list[AdversarialQuestion], list[AdversarialQuestion]]:
    """`(train, holdout)` for the 13 `adversarial` questions."""
    return _split(load_adversarial_questions())


def split_out_of_corpus() -> tuple[list[OutOfCorpusQuestion], list[OutOfCorpusQuestion]]:
    """`(train, holdout)` for the 22 `out_of_corpus` questions."""
    return _split(load_out_of_corpus_questions())


def _split(questions: list[_Q]) -> tuple[list[_Q], list[_Q]]:
    train = [q for q in questions if q.id not in HOLDOUT_IDS]
    holdout = [q for q in questions if q.id in HOLDOUT_IDS]
    return train, holdout
