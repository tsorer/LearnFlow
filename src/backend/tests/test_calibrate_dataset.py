"""T-57: the committed stratified split (`eval/calibrate_dataset.py`) against the live
gold-eval dataset — guards against the two ways it could go stale: a question id that no
longer exists, and a fresh split (same seed) no longer matching what is committed because
the dataset's shape changed underneath it.
"""

from __future__ import annotations

from eval.calibrate_dataset import (
    HOLDOUT_IDS,
    _compute_holdout_ids,
    split_adversarial,
    split_in_corpus,
    split_out_of_corpus,
)
from eval.gold_dataset import (
    load_adversarial_questions,
    load_in_corpus_questions,
    load_out_of_corpus_questions,
)


def test_holdout_ids_match_a_fresh_stratified_split() -> None:
    """The committed literal is exactly what `_compute_holdout_ids` derives today.

    A drift here means the dataset changed shape (a question added/removed/recategorised)
    without recomputing the split — the fix is to regenerate `HOLDOUT_IDS`, not to relax
    this test.
    """
    assert _compute_holdout_ids() == HOLDOUT_IDS


def test_every_holdout_id_exists_in_the_current_dataset() -> None:
    all_ids = {
        q.id
        for q in (
            *load_in_corpus_questions(),
            *load_adversarial_questions(),
            *load_out_of_corpus_questions(),
        )
    }
    missing = HOLDOUT_IDS - all_ids
    assert not missing, f"Holdout-IDs ohne Entsprechung im Dataset: {sorted(missing)}"


def test_in_corpus_split_is_thirty_train_fifteen_holdout() -> None:
    train, holdout = split_in_corpus()

    assert len(train) == 30
    assert len(holdout) == 15
    assert not set(q.id for q in train) & set(q.id for q in holdout)


def test_in_corpus_holdout_is_five_questions_per_corpus() -> None:
    _, holdout = split_in_corpus()
    by_corpus: dict[str, int] = {}
    for q in holdout:
        by_corpus[q.corpus] = by_corpus.get(q.corpus, 0) + 1

    assert by_corpus == {"eu-ai-act": 5, "samw-leitfaden": 5, "skos-richtlinien": 5}


def test_adversarial_and_out_of_corpus_splits_partition_without_overlap() -> None:
    """Train und Holdout zusammen decken jede Frage der Kategorie genau einmal ab.

    `train_ids | holdout_ids == train_ids.union(holdout_ids)` (die vorherige Fassung dieses
    Tests) ist dieselbe Operation zweimal geschrieben und deshalb immer wahr -- geprüft wurde
    damit nichts. Der Vergleich muss gegen die *unabhängige* Quelle gehen (der volle
    Fragensatz aus dem Dataset), sonst fiele eine Frage, die in keinem der beiden Splits
    landet, nicht auf (Review-Befund).
    """
    for train, holdout, all_questions in (
        (*split_adversarial(), load_adversarial_questions()),
        (*split_out_of_corpus(), load_out_of_corpus_questions()),
    ):
        train_ids = {q.id for q in train}
        holdout_ids = {q.id for q in holdout}
        all_ids = {q.id for q in all_questions}
        assert not train_ids & holdout_ids
        assert train_ids | holdout_ids == all_ids
        assert len(holdout) > 0
        assert len(train) > len(holdout)
