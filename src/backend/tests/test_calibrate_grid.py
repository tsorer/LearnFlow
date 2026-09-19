"""T-57: Schicht A1/A2 (`eval/calibrate_grid.py`) — reine Funktionen, kleine handgebaute
Snapshot-Fixtures, kein Stack, wie `tests/test_eval_metrics.py` für `eval/metrics.py`.
"""

from __future__ import annotations

import uuid

from eval.calibrate_grid import (
    A1Candidate,
    A1Ranked,
    A2Candidate,
    CombinedCandidate,
    context_for,
    kfold_splits,
    pre_generation_outcome,
    rank_combined_candidates,
    select_candidates_for_schicht_b,
)
from eval.calibrate_snapshot import QuestionSnapshot, SnapshotRow


def make_row(score: float, *, page: int = 1, filename: str = "doc.pdf") -> SnapshotRow:
    return SnapshotRow(
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        filename=filename,
        page=page,
        heading=None,
        score=score,
    )


def make_question(
    qid: str,
    *,
    category: str = "in_corpus",
    corpus: str | None = "eu-ai-act",
    dense: list[SnapshotRow] | None = None,
    sparse: list[SnapshotRow] | None = None,
) -> QuestionSnapshot:
    return QuestionSnapshot(
        id=qid,
        category=category,
        corpus=corpus,
        question=f"Frage {qid}",
        dense=dense or [],
        sparse=sparse or [],
    )


# --- kfold_splits ------------------------------------------------------------


def test_kfold_splits_partition_every_id_exactly_once_per_fold() -> None:
    ids = [f"q{i}" for i in range(12)]
    corpus_of = {qid: "a" if i % 2 == 0 else "b" for i, qid in enumerate(ids)}

    splits = kfold_splits(ids, corpus_of, k=4, seed=1)

    assert len(splits) == 4
    validation_union: set[str] = set()
    for train, validation in splits:
        assert not set(train) & set(validation)
        assert set(train) | set(validation) == set(ids)
        validation_union.update(validation)
    assert validation_union == set(ids)


def test_kfold_splits_are_deterministic_for_a_fixed_seed() -> None:
    ids = [f"q{i}" for i in range(9)]
    corpus_of = dict.fromkeys(ids, "a")

    a = kfold_splits(ids, corpus_of, k=3, seed=57)
    b = kfold_splits(ids, corpus_of, k=3, seed=57)

    assert a == b


def test_kfold_splits_stratify_across_folds() -> None:
    """Jeder Korpus landet über die Folds verteilt, nicht komplett in einem."""
    ids = [f"a{i}" for i in range(6)] + [f"b{i}" for i in range(6)]
    corpus_of = {qid: qid[0] for qid in ids}

    splits = kfold_splits(ids, corpus_of, k=3, seed=1)

    for _train, validation in splits:
        corpora_in_fold = {corpus_of[qid] for qid in validation}
        assert corpora_in_fold == {"a", "b"}


# --- context_for -------------------------------------------------------------


def test_context_for_truncates_to_retrieval_top_k_then_context_top_n() -> None:
    dense = [make_row(0.9), make_row(0.8), make_row(0.7)]
    question = make_question("Q1", dense=dense, sparse=[])
    a1 = A1Candidate(retrieval_top_k=2, rrf_k=60, context_top_n=1)

    context = context_for(question, a1)

    # Nur die ersten zwei dense-Zeilen (top_k=2) sind im Kandidatenpool, davon die
    # beste eine im Kontext (context_top_n=1) -- die dritte Zeile (0.7) darf nicht
    # auftauchen, obwohl sie im Snapshot steht.
    assert len(context) == 1
    assert context[0].score == 0.9


# --- pre_generation_outcome ---------------------------------------------------


def test_pre_generation_outcome_passes_when_gate_and_confidence_clear() -> None:
    question = make_question("Q1", dense=[make_row(0.9), make_row(0.85)])
    a1 = A1Candidate(retrieval_top_k=10, rrf_k=60, context_top_n=2)
    a2 = A2Candidate(similarity_threshold=0.35, min_retrieval_confidence=0.10)

    outcome = pre_generation_outcome(question, a1, a2)

    assert outcome.passed is True
    assert len(outcome.context_chunk_ids) == 2


def test_pre_generation_outcome_fails_below_similarity_threshold() -> None:
    question = make_question("Q1", dense=[make_row(0.10)])
    a1 = A1Candidate(retrieval_top_k=10, rrf_k=60, context_top_n=1)
    a2 = A2Candidate(similarity_threshold=0.35, min_retrieval_confidence=0.10)

    outcome = pre_generation_outcome(question, a1, a2)

    assert outcome.passed is False
    assert outcome.context_chunk_ids == ()


def test_pre_generation_outcome_fails_below_retrieval_confidence_even_if_gate_passes() -> None:
    """Ein Chunk knapp über der Similarity-Schwelle reicht für Stufe 0, aber `result`
    (Stufe 1) kann trotzdem unter `min_retrieval_confidence` bleiben."""
    question = make_question("Q1", dense=[make_row(0.36)])
    a1 = A1Candidate(retrieval_top_k=10, rrf_k=60, context_top_n=5)
    a2 = A2Candidate(similarity_threshold=0.35, min_retrieval_confidence=0.99)

    outcome = pre_generation_outcome(question, a1, a2)

    assert outcome.passed is False


# --- rank_combined_candidates --------------------------------------------------


def test_rank_combined_candidates_prefers_sets_that_meet_the_refusal_gate() -> None:
    # Zwei out_of_corpus-Fragen: "OOC-WEAK" liegt unter jeder Gitterschwelle
    # (immer unterdrückt), "OOC-STRONG" liegt knapp über dem grössten
    # `similarity_threshold`-Gitterwert (0.40), aber knapp unter dem
    # `min_retrieval_confidence`-Höchstwert (0.60) -- je nach A2-Kombination
    # wird sie also mal am Gate, mal an der Konfidenz, mal gar nicht
    # unterdrückt. Damit unterscheiden sich die A2-Kandidaten in der
    # Refusal-Proxy-Rate zwischen 50 % und 100 %.
    weak_ooc = make_question(
        "OOC-WEAK", category="out_of_corpus", corpus=None, dense=[make_row(0.01)]
    )
    strong_ooc = make_question(
        "OOC-STRONG", category="out_of_corpus", corpus=None, dense=[make_row(0.38)]
    )
    ic = make_question("IC-1", dense=[make_row(0.9)])

    a1 = A1Candidate(retrieval_top_k=10, rrf_k=60, context_top_n=1)
    ranked = rank_combined_candidates(
        [weak_ooc, strong_ooc, ic],
        a1_candidates=[a1],
        out_of_corpus_train_ids=["OOC-WEAK", "OOC-STRONG"],
        in_corpus_train_ids=["IC-1"],
    )

    # Mindestens eine A2-Kombination unterdrückt beide out_of_corpus-Fragen
    # (Refusal-Proxy 100 %) und erfüllt damit das 90-%-Gate; die Top-Kandidaten
    # müssen `meets_refusal_gate=True` tragen und vor jedem Nicht-Erfüller stehen.
    top = ranked[0]
    assert top.meets_refusal_gate is True
    first_failing_index = next(i for i, r in enumerate(ranked) if not r.meets_refusal_gate)
    assert all(r.meets_refusal_gate for r in ranked[:first_failing_index])


# --- select_candidates_for_schicht_b -------------------------------------------


def test_select_candidates_for_schicht_b_returns_at_most_top_n() -> None:
    ic = make_question("IC-1", dense=[make_row(0.9)])
    ooc = make_question("OOC-1", category="out_of_corpus", corpus=None, dense=[make_row(0.05)])
    a1 = A1Candidate(retrieval_top_k=10, rrf_k=60, context_top_n=1)
    a1_ranked = [
        A1Ranked(
            candidate=a1, mean_recall=1.0, mean_precision=1.0, mean_f1=1.0, mean_mrr=1.0, f1_std=0.0
        )
    ]

    selected = select_candidates_for_schicht_b(
        [ic, ooc],
        a1_ranked,
        out_of_corpus_train_ids=["OOC-1"],
        in_corpus_train_ids=["IC-1"],
        top_n=3,
    )

    assert len(selected) <= 3
    assert all(isinstance(c, CombinedCandidate) for c in selected)
