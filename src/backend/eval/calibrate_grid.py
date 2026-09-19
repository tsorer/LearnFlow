"""T-57: Schicht A1 (Ranking) und A2 (Vor-Generierungs-Gates) — beide offline, gegen den
Snapshot aus `eval/calibrate_snapshot.py`, ohne LLM-Aufruf und ohne DB-Zugriff.

Schicht A1 sweept `retrieval_top_k`/`rrf_k`/`context_top_n` gegen Context-Recall/Precision/
MRR der 45 `in_corpus`-Fragen (issue: nicht der `adversarial`-Fragen mit Quelle — die
Bewertungsmenge für A1 ist explizit auf `in_corpus` begrenzt). Auswahl über k-fold-CV auf
dem Train-Split, nicht über einen einzelnen Split (`select_a1_candidates`).

Schicht A2 sweept `similarity_threshold`/`min_retrieval_confidence` gegen die
Vor-Generierungs-Suppression über *alle* Kategorien, indem `passes_retrieval_gate()`/
`compute_retrieval_confidence()` (unverändert aus `app/services/confidence.py`) auf dem
Snapshot ausgewertet werden — ohne die Frage tatsächlich zu generieren.

Beide Gitter zusammen liefern die Top-N kombinierten Parametersätze, die
`eval/calibrate_run.py` in echte Läufe (Schicht B) schickt.
"""

from __future__ import annotations

import itertools
import random
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.services.confidence import (
    RetrievalDetail,
    compute_retrieval_confidence,
    passes_retrieval_gate,
)
from app.services.retrieval import RetrievalHit, fuse
from eval.calibrate_snapshot import SNAPSHOT_TOP_K, QuestionSnapshot, snapshot_row_as_hit_dict
from eval.gates import REFUSAL_RATE_GATE
from eval.gold_dataset import load_corpus_filenames, load_in_corpus_questions
from eval.metrics import RetrievalMetrics, retrieval_metrics

# --- Gitterwerte (Vorschlag, im Bericht/PR anpassbar) -----------------------

RETRIEVAL_TOP_K_GRID: tuple[int, ...] = (10, 20, 30, 50, 100)
RRF_K_GRID: tuple[int, ...] = (20, 40, 60, 80, 100)
CONTEXT_TOP_N_GRID: tuple[int, ...] = (3, 5, 7, 10)

# Jeder Kandidat muss innerhalb dessen liegen, was der Snapshot eingefroren hat (AC 1) --
# sonst würde ein grösserer retrieval_top_k-Wert hier still auf zu wenige Zeilen fallen,
# statt laut zu scheitern (Review-Befund: der Docstring in calibrate_snapshot.py versprach
# diesen Assert, ohne ihn zu haben).
assert max(RETRIEVAL_TOP_K_GRID) <= SNAPSHOT_TOP_K, (
    f"RETRIEVAL_TOP_K_GRID enthält einen Wert über SNAPSHOT_TOP_K ({SNAPSHOT_TOP_K}) -- "
    "der Snapshot friert nur so viele Zeilen ein."
)

SIMILARITY_THRESHOLD_GRID: tuple[float, ...] = (0.20, 0.25, 0.30, 0.35, 0.40)
MIN_RETRIEVAL_CONFIDENCE_GRID: tuple[float, ...] = (0.20, 0.30, 0.40, 0.50, 0.60)

#: Wie viele A1-Kandidaten aus der CV in die A2-Kombination gehen.
A1_TOP_N = 5
#: Wie viele kombinierte (A1×A2)-Sets in Schicht B (echte Läufe) gehen.
COMBINED_TOP_N = 8
#: Folds der k-fold-CV auf dem Train-Split der 45 in_corpus-Fragen.
K_FOLDS = 5


@dataclass(frozen=True)
class A1Candidate:
    retrieval_top_k: int
    rrf_k: int
    context_top_n: int


@dataclass(frozen=True)
class A2Candidate:
    similarity_threshold: float
    min_retrieval_confidence: float


@dataclass(frozen=True)
class CombinedCandidate:
    a1: A1Candidate
    a2: A2Candidate


@dataclass(frozen=True)
class PreGenerationOutcome:
    """Ob eine Frage vor der Generierung unterdrückt würde, und mit welchem Kontext."""

    question_id: str
    passed: bool
    #: leer, wenn nicht bestanden (kein Kontext würde generiert)
    context_chunk_ids: tuple[str, ...]
    retrieval_detail: RetrievalDetail
    #: Immer gefüllt (auch wenn `passed` False ist) -- Aufrufer, die den tatsächlichen
    #: Kontext brauchen (Schicht B, Schicht C), sparen sich damit ein zweites
    #: `context_for()` über dieselbe Frage/denselben A1-Kandidaten (Review-Befund).
    context: list[RetrievalHit]


def context_for(
    question: QuestionSnapshot, a1: A1Candidate
) -> list[RetrievalHit]:
    """Repliziert `retrieve()`'s Kontext für `question` unter `a1`, aus dem Snapshot.

    Die Snapshot-Zeilen sind bereits nach Score sortiert (dieselbe `ORDER BY`-Klausel wie
    `DENSE_SQL`/`SPARSE_SQL`) — ein kleineres `retrieval_top_k` ist deshalb einfach ein
    Präfix der `top_k=100`-Zeilen, kein neuer Fetch (ADR-009-Kommentar zum Issue).
    """
    dense = [snapshot_row_as_hit_dict(row) for row in question.dense[: a1.retrieval_top_k]]
    sparse = [snapshot_row_as_hit_dict(row) for row in question.sparse[: a1.retrieval_top_k]]
    candidates = fuse(dense, sparse, a1.rrf_k)
    return candidates[: a1.context_top_n]


# --- Schicht A1: Ranking-Gitter ---------------------------------------------


def a1_grid() -> list[A1Candidate]:
    return [
        A1Candidate(retrieval_top_k=k, rrf_k=r, context_top_n=n)
        for k, r, n in itertools.product(
            RETRIEVAL_TOP_K_GRID, RRF_K_GRID, CONTEXT_TOP_N_GRID
        )
    ]


def _expected_pages_by_id() -> dict[str, tuple[int, ...]]:
    return {q.id: q.expected_source.pages for q in load_in_corpus_questions()}


def _corpus_by_id() -> dict[str, str]:
    return {q.id: q.corpus for q in load_in_corpus_questions()}


def kfold_splits(
    question_ids: Sequence[str], corpus_of: dict[str, str], *, k: int, seed: int
) -> list[tuple[list[str], list[str]]]:
    """`k` stratifizierte (nach `corpus_of`) Folds über `question_ids`.

    Gibt `k` `(train, validation)`-Paare zurück. Stratifiziert, damit ein Fold nicht durch
    Zufall nur Fragen eines Korpus als Validierung bekommt (bei 30 Fragen über drei Korpora,
    10 je Korpus, wäre das bei k=5 sonst leicht möglich).
    """
    by_corpus: dict[str, list[str]] = {}
    for qid in question_ids:
        by_corpus.setdefault(corpus_of[qid], []).append(qid)

    folds: list[list[str]] = [[] for _ in range(k)]
    for corpus, ids in sorted(by_corpus.items()):
        ordered = sorted(ids)
        random.Random(f"kfold:{seed}:{corpus}").shuffle(ordered)
        for i, qid in enumerate(ordered):
            folds[i % k].append(qid)

    splits: list[tuple[list[str], list[str]]] = []
    for i in range(k):
        validation = folds[i]
        train = [qid for j, fold in enumerate(folds) if j != i for qid in fold]
        splits.append((train, validation))
    return splits


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _f1(precision: float, recall: float) -> float:
    """Harmonisches Mittel aus Precision und Recall, 0.0 wenn beide 0 sind.

    Nicht Recall allein: Recall ist in `context_top_n` nicht-fallend (mehr Kontext kann nur
    mehr erwartete Seiten treffen, nie weniger) -- ein reines Recall-Ranking wählt deshalb
    strukturell immer den grössten Gitterwert, unabhängig davon, ob der zusätzliche Kontext
    noch etwas beiträgt (Review-Befund). Precision fällt mit wachsendem `context_top_n`
    typischerweise, F1 balanciert beides.
    """
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


@dataclass(frozen=True)
class _MeanMetrics:
    """Recall/Precision/MRR gemittelt über eine Fragenmenge — nicht `RetrievalMetrics`
    (die beschreibt eine einzelne Frage, mit `hits`/`considered` als Zähler, die für einen
    Mittelwert über mehrere Fragen keinen Sinn ergeben)."""

    recall: float
    precision: float
    mrr: float


def _score_candidate(
    candidate: A1Candidate,
    questions_by_id: dict[str, QuestionSnapshot],
    validation_ids: Iterable[str],
    corpus_filenames: dict[str, str],
    expected_pages: dict[str, tuple[int, ...]],
) -> _MeanMetrics:
    """Recall/Precision/MRR von `candidate` über `validation_ids`, im Kontext-Schnitt."""
    per_question: list[RetrievalMetrics] = []
    for qid in validation_ids:
        question = questions_by_id[qid]
        context = context_for(question, candidate)
        chunks = [{"filename": hit.filename, "page": hit.page} for hit in context]
        per_question.append(
            retrieval_metrics(
                chunks,
                corpus_filename=corpus_filenames[question.corpus] if question.corpus else "",
                expected_pages=expected_pages[qid],
            )
        )
    recall = _mean([m.recall for m in per_question if m.recall is not None])
    precision = _mean([m.precision for m in per_question])
    mrr = _mean([m.mrr for m in per_question])
    return _MeanMetrics(recall=recall, precision=precision, mrr=mrr)


@dataclass(frozen=True)
class A1Ranked:
    candidate: A1Candidate
    #: Mittel über die k Folds (Recall/Precision/F1/MRR im Kontext-Schnitt).
    mean_recall: float
    mean_precision: float
    mean_f1: float
    mean_mrr: float
    #: Streuung von F1 über die k Folds (Populations-Stdev, 0.0 bei k=1). A1 hat keinen
    #: Fit-Schritt -- die Folds "lernen" nichts, ihr Mittelwert über eine vollständige
    #: Partition ist arithmetisch nahezu derselbe wie eine einzelne Auswertung über alle
    #: Trainingsfragen. Was die Folds trotzdem hergeben, ist diese Streuung: wie stabil die
    #: Metrik gegenüber der Wahl der Teilmenge ist. Ohne sie wäre die CV reine Mehrarbeit
    #: ohne zusätzliche Aussage (Review-Befund).
    f1_std: float


def select_a1_candidates(
    snapshot_questions: list[QuestionSnapshot],
    train_ids: Sequence[str],
    *,
    top_n: int = A1_TOP_N,
    k: int = K_FOLDS,
    seed: int = 57,
) -> list[A1Ranked]:
    """Top-N A1-Kandidaten nach k-fold-CV auf `train_ids` (den 30 in_corpus-Trainingsfragen).

    Primärkriterium: mittleres F1 aus Recall und Precision über die Folds (siehe `_f1` --
    Recall allein bevorzugt strukturell den grössten `context_top_n`-Gitterwert). MRR als
    Tie-Breaker.
    """
    questions_by_id = {q.id: q for q in snapshot_questions if q.id in train_ids}
    corpus_filenames = load_corpus_filenames()
    expected_pages = _expected_pages_by_id()
    corpus_of = _corpus_by_id()

    splits = kfold_splits(train_ids, corpus_of, k=k, seed=seed)

    ranked: list[A1Ranked] = []
    for candidate in a1_grid():
        fold_recalls: list[float] = []
        fold_precisions: list[float] = []
        fold_mrrs: list[float] = []
        fold_f1s: list[float] = []
        for _train_fold, validation_fold in splits:
            metrics = _score_candidate(
                candidate, questions_by_id, validation_fold, corpus_filenames, expected_pages
            )
            fold_recalls.append(metrics.recall)
            fold_precisions.append(metrics.precision)
            fold_mrrs.append(metrics.mrr)
            fold_f1s.append(_f1(metrics.precision, metrics.recall))
        ranked.append(
            A1Ranked(
                candidate=candidate,
                mean_recall=_mean(fold_recalls),
                mean_precision=_mean(fold_precisions),
                mean_f1=_mean(fold_f1s),
                mean_mrr=_mean(fold_mrrs),
                f1_std=statistics.pstdev(fold_f1s) if len(fold_f1s) > 1 else 0.0,
            )
        )

    ranked.sort(key=lambda r: (r.mean_f1, r.mean_mrr), reverse=True)
    return ranked[:top_n]


# --- Schicht A2: Vor-Generierungs-Gates -------------------------------------


def a2_grid() -> list[A2Candidate]:
    return [
        A2Candidate(similarity_threshold=s, min_retrieval_confidence=c)
        for s, c in itertools.product(SIMILARITY_THRESHOLD_GRID, MIN_RETRIEVAL_CONFIDENCE_GRID)
    ]


def pre_generation_outcome(
    question: QuestionSnapshot, a1: A1Candidate, a2: A2Candidate
) -> PreGenerationOutcome:
    """Stufe 0 + Stufe 1 (ADR-007/008) rein aus dem Snapshot, ohne Generierung."""
    context = context_for(question, a1)
    scores = [hit.score for hit in context]
    gate_passed = passes_retrieval_gate(scores, a2.similarity_threshold)
    detail = compute_retrieval_confidence(scores, a2.similarity_threshold, a1.context_top_n)
    passed = gate_passed and detail.result >= a2.min_retrieval_confidence
    return PreGenerationOutcome(
        question_id=question.id,
        passed=passed,
        context_chunk_ids=tuple(str(hit.chunk_id) for hit in context) if passed else (),
        retrieval_detail=detail,
        context=context,
    )


@dataclass(frozen=True)
class CombinedRanked:
    combined: CombinedCandidate
    out_of_corpus_refusal_rate: float
    in_corpus_pre_generation_suppression_rate: float
    meets_refusal_gate: bool


def rank_combined_candidates(
    snapshot_questions: list[QuestionSnapshot],
    a1_candidates: Sequence[A1Candidate],
    out_of_corpus_train_ids: Sequence[str],
    in_corpus_train_ids: Sequence[str],
) -> list[CombinedRanked]:
    """Alle A1×A2-Kombinationen über den Train-Split geschätzt und geordnet.

    Reihenfolge: zuerst die Kombinationen, deren Out-of-Corpus-Refusal-Proxy (Anteil der
    `out_of_corpus`-Trainingsfragen, die schon das Retrieval-Gate unterdrückt) das
    90-%-Ziel erreicht — das ist eine untere Schranke auf der echten Refusal-Rate, da
    Stufe 2/3 in Schicht B nur weitere Fragen unterdrücken können, nie weniger. Danach
    niedrigste In-Corpus-Vor-Generierungs-Suppression (dieselbe Logik in die andere
    Richtung: eine untere Schranke auf der echten False-Suppression-Rate).
    """
    by_id = {q.id: q for q in snapshot_questions}

    ranked: list[CombinedRanked] = []
    for a1 in a1_candidates:
        for a2 in a2_grid():
            ooc_outcomes = [
                pre_generation_outcome(by_id[qid], a1, a2) for qid in out_of_corpus_train_ids
            ]
            ic_outcomes = [
                pre_generation_outcome(by_id[qid], a1, a2) for qid in in_corpus_train_ids
            ]
            refusal_rate = _mean([0.0 if o.passed else 1.0 for o in ooc_outcomes])
            suppression_rate = _mean([0.0 if o.passed else 1.0 for o in ic_outcomes])
            ranked.append(
                CombinedRanked(
                    combined=CombinedCandidate(a1=a1, a2=a2),
                    out_of_corpus_refusal_rate=refusal_rate,
                    in_corpus_pre_generation_suppression_rate=suppression_rate,
                    meets_refusal_gate=refusal_rate >= REFUSAL_RATE_GATE,
                )
            )

    ranked.sort(
        key=lambda r: (
            not r.meets_refusal_gate,
            r.in_corpus_pre_generation_suppression_rate,
        )
    )
    return ranked


def select_candidates_for_schicht_b(
    snapshot_questions: list[QuestionSnapshot],
    a1_ranked: Sequence[A1Ranked],
    out_of_corpus_train_ids: Sequence[str],
    in_corpus_train_ids: Sequence[str],
    *,
    top_n: int = COMBINED_TOP_N,
) -> list[CombinedCandidate]:
    """Top-N kombinierte (A1×A2)-Sets, die Schicht B (echte Läufe) auswertet.

    Dünner Wrapper um `rank_combined_candidates()` für den Fall, dass nur die Top-N
    gebraucht werden. `eval/calibrate.py` ruft `rank_combined_candidates()` stattdessen
    direkt auf, weil es aus demselben Ergebnis zusätzlich den entarteten Referenzpunkt
    braucht (`worst_case_candidate()`) -- ein zweiter Aufruf hier würde die ganze
    A1×A2-Auswertung ein zweites Mal rechnen.
    """
    a1_candidates = [r.candidate for r in a1_ranked]
    ranked = rank_combined_candidates(
        snapshot_questions, a1_candidates, out_of_corpus_train_ids, in_corpus_train_ids
    )
    return [r.combined for r in ranked[:top_n]]


def worst_case_candidate(ranked: Sequence[CombinedRanked]) -> CombinedRanked:
    """Der Kandidat mit der höchsten In-Corpus-Vor-Generierungs-Suppression in `ranked` —
    der entartete Punkt "alles unterdrücken" aus AC 7, geschätzt direkt aus Schicht A2
    (offline, ohne echten Lauf: eine fast vollständig unterdrückende Parameterkombination
    generiert ohnehin für fast keine Frage eine Antwort).

    Nur so stark, wie `ranked` es ist: um wirklich "der schlechteste Punkt im ganzen
    A1×A2-Gitter" zu sein, muss der Aufrufer `rank_combined_candidates()` mit `a1_grid()`
    (allen A1-Kandidaten) gefüttert haben, nicht nur den Top-N aus `select_a1_candidates()`
    (Review-Befund: `eval/calibrate.py` rief diese Funktion zuerst mit dem für Schicht B
    bereits auf die Top-5 vorgefilterten Ergebnis auf — der gefundene "entartete" Punkt war
    dadurch nur der schlechteste unter den fünf besten A1-Kandidaten, nicht im ganzen Gitter,
    obwohl der Bericht genau das behauptete).

    `select_candidates_for_schicht_b()` wählt genau die *niedrigste* Suppression für Schicht
    B aus — der entartete Punkt liegt damit strukturell ausserhalb der Top-N und würde nie
    in einen `CandidateReport` gelangen, wenn er nicht hier separat aus einem vollständigeren
    `rank_combined_candidates()`-Ergebnis gezogen würde (früherer Review-Befund: der Bericht
    schrieb zuvor "liegt ausserhalb des gesweepten Bereichs", obwohl er nie geprüft wurde).
    """
    return max(ranked, key=lambda r: r.in_corpus_pre_generation_suppression_rate)
