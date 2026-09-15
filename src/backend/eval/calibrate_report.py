"""T-57: Schicht C (Bandschwellen, offline-Arithmetik) und der Bericht.

Alles hier ist Arithmetik über bereits vorhandene Daten — dem Snapshot (Schicht A) und den
in Schicht B aufgezeichneten echten Läufen (`runs.json`) — kein weiterer LLM-Aufruf. Das
funktioniert nur, weil Schicht B den Self-Check für **jede** generierte Antwort erzwungen
hat (`eval/calibrate_run.py`, AC 5): `evaluate_question` unten entscheidet für ein gegebenes
`(confidence_threshold_medium, self_check_band_high)`-Paar, ob eine Antwort ins
Self-Check-Band fällt, und liest dann nur noch das *schon vorliegende* Verdikt.

Die Zielfunktion (ADR-009): unter den Constraints Halluzination = 0 % und
Out-of-Corpus-Refusal ≥ 90 % die False-Suppression-Rate auf den `in_corpus`-Fragen
minimieren. Der entartete Punkt „alles unterdrücken" bleibt Teil der ausgewerteten Menge und
wird im Bericht explizit als ausgeschlossen benannt (AC 7) — dafür zieht `evaluate_full_grid`
ihn separat aus `calibrate_grid.worst_case_candidate()`, weil `select_candidates_for_schicht_b`
gezielt die *niedrigste* Suppression für Schicht B auswählt und ein wirklich entarteter
Kandidat diese Vorauswahl sonst nie erreichen würde.

**Zur Effizienz:** `evaluate_full_grid` gruppiert nach `(a1, a2)` (den ≤ `COMBINED_TOP_N`
kombinierten Kandidaten) und berechnet Gate/Konfidenz/Kontext (`PreGenState`) einmal pro
Frage und Kombination, statt einmal pro vollem Zehn-Werte-Kandidaten (Review-Befund: bei
~1000 `FullCandidate`s im Standardgitter wäre das dieselbe Arithmetik bis zu 125-mal
wiederholt worden). Nur die Schicht-C-Schwellen (`min_citation_coverage`,
`confidence_threshold_medium`, `self_check_band_high`) variieren innerhalb einer Gruppe.
"""

from __future__ import annotations

import dataclasses
import itertools
from collections.abc import Sequence

from app.services.confidence import (
    BAND_LOW,
    CitationDetail,
    band_for,
    compute_composite,
    in_self_check_band,
)
from app.services.retrieval import RetrievalHit
from eval.calibrate_grid import (
    A1Candidate,
    A2Candidate,
    CombinedCandidate,
    CombinedRanked,
    pre_generation_outcome,
)
from eval.calibrate_run import RunResult, dedup_key
from eval.calibrate_snapshot import QuestionSnapshot
from eval.gates import FALSE_SUPPRESSION_RATE_GATE, HALLUCINATION_RATE_GATE, REFUSAL_RATE_GATE
from eval.metrics import check_hallucination

# --- Gitterwerte (Vorschlag, im Bericht/PR anpassbar) -----------------------

MIN_CITATION_COVERAGE_GRID: tuple[float, ...] = (0.30, 0.40, 0.50, 0.60, 0.70)
CONFIDENCE_THRESHOLD_MEDIUM_GRID: tuple[float, ...] = (0.30, 0.35, 0.40, 0.45, 0.50)
SELF_CHECK_BAND_HIGH_GRID: tuple[float, ...] = (0.60, 0.65, 0.70, 0.75, 0.80)


@dataclasses.dataclass(frozen=True)
class FullCandidate:
    """Alle neun gesweepten Werte — `confidence_threshold_high` fehlt bewusst (AC 9):
    kein Sweep-Parameter, wird erst nach der Auswahl des Gewinners festgelegt."""

    a1: A1Candidate
    a2: A2Candidate
    min_citation_coverage: float
    confidence_threshold_medium: float
    self_check_band_high: float

    @property
    def self_check_band_low(self) -> float:
        """An `confidence_threshold_medium` gekoppelt (Schritt 7 des Plans, spiegelt die
        bestehende Begründung in `app/services/config.py:35-41`): hält das Gitter auf zwei
        statt drei freien Dimensionen, ohne einen eigenen Freiheitsgrad einzuführen, für den
        das Issue keinen eigenen Constraint nennt."""
        return self.confidence_threshold_medium


@dataclasses.dataclass(frozen=True)
class QuestionOutcome:
    question_id: str
    category: str
    #: None heisst: die Antwort wurde ausgeliefert.
    suppression_reason: str | None
    hallucinated: bool | None


def _schicht_c_grid() -> list[tuple[float, float, float]]:
    """`(min_citation_coverage, confidence_threshold_medium, self_check_band_high)`-Tripel.

    Der `medium <= high`-Filter ist mit den heutigen Gitterwerten nie aktiv (Maximum von
    `CONFIDENCE_THRESHOLD_MEDIUM_GRID` liegt unter dem Minimum von `SELF_CHECK_BAND_HIGH_GRID`)
    — er bleibt trotzdem stehen, weil ein invertiertes Band kein gültiger Kandidat ist
    (`app/services/config.py::_pipeline_from`) und ein künftig verbreitertes Gitter ihn
    brauchen würde.
    """
    return [
        (coverage, medium, high)
        for coverage, medium, high in itertools.product(
            MIN_CITATION_COVERAGE_GRID, CONFIDENCE_THRESHOLD_MEDIUM_GRID, SELF_CHECK_BAND_HIGH_GRID
        )
        if medium <= high
    ]


def _citations_for_hallucination(context: list[RetrievalHit]) -> list[dict[str, object]]:
    return [
        {"index": i, "filename": hit.filename, "page": hit.page}
        for i, hit in enumerate(context, start=1)
    ]


@dataclasses.dataclass(frozen=True)
class PreGenState:
    """Alles, was Stufe 0/1 (ADR-007/008) für eine Frage unter einem `(a1, a2)`-Paar
    festlegen — unabhängig von den Schicht-C-Schwellen, deshalb einmal pro `(Frage, a1, a2)`
    berechnet statt einmal pro vollem Kandidaten (siehe Moduldoc)."""

    question_id: str
    category: str
    passed: bool
    context: list[RetrievalHit]
    retrieval_score: float
    corpus_filename: str | None
    expected_pages: tuple[int, ...]
    score_for_hallucination: bool


def compute_pre_gen_states(
    combined: CombinedCandidate,
    snapshot_by_id: dict[str, QuestionSnapshot],
    in_corpus_ids: Sequence[str],
    adversarial_scored_ids: Sequence[str],
    out_of_corpus_ids: Sequence[str],
    corpus_filenames: dict[str, str],
    expected_pages_in_corpus: dict[str, tuple[int, ...]],
    expected_pages_adversarial: dict[str, tuple[int, ...]],
) -> dict[str, PreGenState]:
    """Ein `PreGenState` je Frage, für das gegebene `(a1, a2)`-Paar."""
    states: dict[str, PreGenState] = {}
    for qid in in_corpus_ids:
        question = snapshot_by_id[qid]
        outcome = pre_generation_outcome(question, combined.a1, combined.a2)
        states[qid] = PreGenState(
            question_id=qid,
            category="in_corpus",
            passed=outcome.passed,
            context=outcome.context,
            retrieval_score=outcome.retrieval_detail.result,
            corpus_filename=corpus_filenames.get(question.corpus) if question.corpus else None,
            expected_pages=expected_pages_in_corpus.get(qid, ()),
            score_for_hallucination=True,
        )
    for qid in adversarial_scored_ids:
        question = snapshot_by_id[qid]
        outcome = pre_generation_outcome(question, combined.a1, combined.a2)
        states[qid] = PreGenState(
            question_id=qid,
            category="adversarial",
            passed=outcome.passed,
            context=outcome.context,
            retrieval_score=outcome.retrieval_detail.result,
            corpus_filename=corpus_filenames.get(question.corpus) if question.corpus else None,
            expected_pages=expected_pages_adversarial.get(qid, ()),
            score_for_hallucination=True,
        )
    for qid in out_of_corpus_ids:
        question = snapshot_by_id[qid]
        outcome = pre_generation_outcome(question, combined.a1, combined.a2)
        states[qid] = PreGenState(
            question_id=qid,
            category="out_of_corpus",
            passed=outcome.passed,
            context=outcome.context,
            retrieval_score=outcome.retrieval_detail.result,
            corpus_filename=None,
            expected_pages=(),
            score_for_hallucination=False,
        )
    return states


def evaluate_question(
    state: PreGenState,
    full: FullCandidate,
    run_results: dict[tuple[str, tuple[str, ...]], RunResult],
) -> QuestionOutcome:
    """Der vollständige Suppression-Entscheid für eine Frage unter `full`, ausgehend von
    einem bereits berechneten `PreGenState` (Stufe 0/1).

    Repliziert `app/routers/query.py`s Fluss (Gate → Konfidenz → Citation-Gültigkeit →
    Citation-Coverage → Komposit-Band → Self-Check): die ersten beiden Stufen stecken schon
    in `state.passed`, alles danach ist Arithmetik über den in Schicht B aufgezeichneten
    `RunResult` plus die Schicht-C-Schwellen aus `full`.
    """
    if not state.passed:
        return QuestionOutcome(state.question_id, state.category, "pre_generation_gate", None)

    key = dedup_key(state.question_id, state.context)
    run = run_results.get(key)
    if run is None:
        raise KeyError(
            f"Kein Schicht-B-Lauf für {key} -- der Kandidat wurde nicht vollständig "
            "durchgerechnet (siehe eval/calibrate.py::_run_schicht_b)."
        )

    if run.truncated:
        return QuestionOutcome(state.question_id, state.category, "generation_truncated", None)
    if run.answer is None:
        return QuestionOutcome(state.question_id, state.category, "generation_refused", None)

    citation: CitationDetail = run.citation  # type: ignore[assignment]
    if not citation.valid:
        return QuestionOutcome(state.question_id, state.category, "citation_invalid", None)
    citation_passed = citation.coverage >= full.min_citation_coverage
    if not citation_passed:
        return QuestionOutcome(state.question_id, state.category, "citation_coverage", None)

    composite = compute_composite(state.retrieval_score, citation.coverage)
    band = band_for(composite.result, full.confidence_threshold_medium, full.self_check_band_high)
    if band == BAND_LOW:
        return QuestionOutcome(state.question_id, state.category, "confidence_band", None)
    if in_self_check_band(composite.result, full.self_check_band_low, full.self_check_band_high):
        if run.self_check is None:
            raise KeyError(
                f"{state.question_id}: kein Self-Check-Verdikt im Lauf -- Schicht B muss ihn "
                "für jede Antwort erzwingen (AC 5)."
            )
        if not run.self_check.passed:
            return QuestionOutcome(state.question_id, state.category, "self_check", None)

    hallucinated: bool | None = None
    if state.score_for_hallucination and state.corpus_filename is not None:
        verdict = check_hallucination(
            answer=run.answer,
            citations=_citations_for_hallucination(state.context),
            corpus_filename=state.corpus_filename,
            expected_pages=state.expected_pages,
        )
        hallucinated = verdict.hallucinated

    return QuestionOutcome(state.question_id, state.category, None, hallucinated)


@dataclasses.dataclass(frozen=True)
class CandidateReport:
    full: FullCandidate
    hallucination_rate: float
    false_suppression_rate: float
    out_of_corpus_refusal_rate: float
    meets_constraints: bool
    #: True für den entarteten Punkt "alles unterdrückt" -- False-Suppression 0 %
    #: sieht dort trügerisch gut aus, ist aber kein brauchbares System (AC 7).
    degenerate: bool
    #: Nenner der drei Raten -- getrennt, weil sie sich unterscheiden (Halluzination
    #: läuft nur über ausgelieferte Antworten, False-Suppression nur über in_corpus,
    #: Refusal nur über out_of_corpus). Für die Auflösungsangabe im Bericht (AC 8):
    #: bei 7 Holdout-Fragen ist eine Frage ~14,3 Prozentpunkte, nicht die 6,7 pp, die
    #: die 15 in_corpus-Fragen ergäben.
    hallucination_pool_size: int
    in_corpus_count: int
    out_of_corpus_count: int


def _aggregate(full: FullCandidate, outcomes: list[QuestionOutcome]) -> CandidateReport:
    hallucination_pool = [o for o in outcomes if o.suppression_reason is None]
    hallucinated = sum(1 for o in hallucination_pool if o.hallucinated)
    hallucination_rate = hallucinated / len(hallucination_pool) if hallucination_pool else 0.0

    in_corpus_outcomes = [o for o in outcomes if o.category == "in_corpus"]
    suppressed = sum(1 for o in in_corpus_outcomes if o.suppression_reason is not None)
    false_suppression_rate = suppressed / len(in_corpus_outcomes) if in_corpus_outcomes else 0.0

    ooc_outcomes = [o for o in outcomes if o.category == "out_of_corpus"]
    ooc_refused = sum(1 for o in ooc_outcomes if o.suppression_reason is not None)
    refusal_rate = ooc_refused / len(ooc_outcomes) if ooc_outcomes else 0.0

    meets_constraints = (
        hallucination_rate <= HALLUCINATION_RATE_GATE and refusal_rate >= REFUSAL_RATE_GATE
    )
    degenerate = false_suppression_rate >= 0.99  # "praktisch alles unterdrückt"

    return CandidateReport(
        full=full,
        hallucination_rate=hallucination_rate,
        false_suppression_rate=false_suppression_rate,
        out_of_corpus_refusal_rate=refusal_rate,
        meets_constraints=meets_constraints,
        degenerate=degenerate,
        hallucination_pool_size=len(hallucination_pool),
        in_corpus_count=len(in_corpus_outcomes),
        out_of_corpus_count=len(ooc_outcomes),
    )


def evaluate_candidate(
    full: FullCandidate,
    snapshot_by_id: dict[str, QuestionSnapshot],
    run_results: dict[tuple[str, tuple[str, ...]], RunResult],
    in_corpus_ids: Sequence[str],
    adversarial_scored_ids: Sequence[str],
    out_of_corpus_ids: Sequence[str],
    corpus_filenames: dict[str, str],
    expected_pages_in_corpus: dict[str, tuple[int, ...]],
    expected_pages_adversarial: dict[str, tuple[int, ...]],
) -> CandidateReport:
    """Ein einzelner Kandidat (die Holdout-Bestätigung braucht nur diesen einen)."""
    states = compute_pre_gen_states(
        CombinedCandidate(a1=full.a1, a2=full.a2),
        snapshot_by_id,
        in_corpus_ids,
        adversarial_scored_ids,
        out_of_corpus_ids,
        corpus_filenames,
        expected_pages_in_corpus,
        expected_pages_adversarial,
    )
    outcomes = [evaluate_question(state, full, run_results) for state in states.values()]
    return _aggregate(full, outcomes)


def evaluate_full_grid(
    combined_candidates: Sequence[CombinedCandidate],
    snapshot_by_id: dict[str, QuestionSnapshot],
    run_results: dict[tuple[str, tuple[str, ...]], RunResult],
    in_corpus_ids: Sequence[str],
    adversarial_scored_ids: Sequence[str],
    out_of_corpus_ids: Sequence[str],
    corpus_filenames: dict[str, str],
    expected_pages_in_corpus: dict[str, tuple[int, ...]],
    expected_pages_adversarial: dict[str, tuple[int, ...]],
) -> list[CandidateReport]:
    """Der Train-Grid-Lauf: alle `combined_candidates` × das Schicht-C-Gitter.

    Gruppiert nach `(a1, a2)`, damit `PreGenState` nur `len(combined_candidates)`-mal
    berechnet wird, nicht einmal pro Schicht-C-Kombination (siehe Moduldoc).
    """
    schicht_c = _schicht_c_grid()
    reports: list[CandidateReport] = []
    for combined in combined_candidates:
        states = compute_pre_gen_states(
            combined,
            snapshot_by_id,
            in_corpus_ids,
            adversarial_scored_ids,
            out_of_corpus_ids,
            corpus_filenames,
            expected_pages_in_corpus,
            expected_pages_adversarial,
        )
        for coverage, medium, high in schicht_c:
            full = FullCandidate(
                a1=combined.a1,
                a2=combined.a2,
                min_citation_coverage=coverage,
                confidence_threshold_medium=medium,
                self_check_band_high=high,
            )
            outcomes = [evaluate_question(state, full, run_results) for state in states.values()]
            reports.append(_aggregate(full, outcomes))
    return reports


def select_winner(reports: Sequence[CandidateReport]) -> CandidateReport | None:
    """Unter den Constraint-erfüllenden, nicht-entarteten Kandidaten der mit der
    niedrigsten False-Suppression-Rate. `None`, wenn keiner die Constraints erreicht (AC 12
    deckt diesen Ausgang ausdrücklich ab -- kein erfundener Gewinner)."""
    eligible = [r for r in reports if r.meets_constraints and not r.degenerate]
    if not eligible:
        return None
    return min(eligible, key=lambda r: r.false_suppression_rate)


def confidence_threshold_high_for(winner: FullCandidate) -> float:
    """Nach Urteil gesetzt, nicht gesweept (AC 9): gleich dem gewinnenden
    `self_check_band_high`, damit "hoch" exakt dort beginnt, wo der Self-Check nichts mehr
    beiträgt -- `band_for()` nutzt `high` ausschliesslich für die Unterscheidung "mittel"
    vs. "hoch" (`app/routers/query.py:440ff`), nie für eine Unterdrückung."""
    return winner.self_check_band_high


def generate_report_markdown(
    *,
    train: CandidateReport,
    holdout: CandidateReport,
    holdout_size: int,
    degenerate: CombinedRanked | None,
    ran_at: str,
    k_folds: int,
) -> str:
    """Der Bericht nach `Docs/10_Kalibrierungsbericht.md` (AC 10).

    Nimmt fertige Ergebnisse statt selbst zu rechnen — `eval/calibrate.py` orchestriert
    Snapshot/Grid/Run/Auswahl und übergibt hier nur noch, was ausgewiesen wird. `degenerate`
    kommt direkt aus `calibrate_grid.worst_case_candidate()` (Schicht A2, offline) statt aus
    einem `CandidateReport`: eine tatsächlich entartete Kombination generiert für praktisch
    keine Frage eine Antwort, ihre Halluzinationsrate ist deshalb nicht definiert, nicht 0 %.
    """
    full = train.full
    high = confidence_threshold_high_for(full)

    def _resolution(count: int) -> str:
        return f"{round(100 / count, 1)} pp" if count else "n/a"

    hallucination_meets = holdout.hallucination_rate <= HALLUCINATION_RATE_GATE
    refusal_meets = holdout.out_of_corpus_refusal_rate >= REFUSAL_RATE_GATE
    holdout_meets_constraints = hallucination_meets and refusal_meets
    false_suppression_ci_meets = holdout.false_suppression_rate <= FALSE_SUPPRESSION_RATE_GATE

    lines = [
        "# Kalibrierungsbericht (T-57)",
        "",
        f"Lauf vom {ran_at}. Erzeugt von `eval/calibrate.py` (`make calibrate`) — "
        "Rohdaten und Snapshot in `eval/out/calibrate/`.",
        "",
        "## Empfohlenes Parameter-Set",
        "",
        "| Parameter | Wert |",
        "|---|---|",
        f"| `retrieval_top_k` | {full.a1.retrieval_top_k} |",
        f"| `rrf_k` | {full.a1.rrf_k} |",
        f"| `context_top_n` | {full.a1.context_top_n} |",
        f"| `similarity_threshold` | {full.a2.similarity_threshold} |",
        f"| `min_retrieval_confidence` | {full.a2.min_retrieval_confidence} |",
        f"| `min_citation_coverage` | {full.min_citation_coverage} |",
        f"| `confidence_threshold_medium` | {full.confidence_threshold_medium} |",
        f"| `confidence_threshold_high` | {high} (nicht optimierbar, nach Urteil gesetzt — "
        "siehe unten) |",
        f"| `self_check_band_low` | {full.self_check_band_low} (an "
        "`confidence_threshold_medium` gekoppelt) |",
        f"| `self_check_band_high` | {full.self_check_band_high} |",
        "",
        "`confidence_threshold_high` unterdrückt nichts — `band_for()` nutzt es nur für die "
        "Unterscheidung „mittel“ vs. „hoch“, unterdrückt wird ausschliesslich über "
        "`confidence_threshold_medium` (`BAND_LOW`). Der Wert oben ist deshalb kein "
        "Sweep-Ergebnis, sondern gleich dem gewinnenden `self_check_band_high` gesetzt, "
        "damit „hoch“ exakt dort beginnt, wo der Self-Check nichts mehr beiträgt.",
        "",
        "## Ergebnis auf dem Holdout",
        "",
        f"Holdout: {holdout_size} `in_corpus`-Fragen, {holdout.out_of_corpus_count} "
        "`out_of_corpus`-Fragen (stratifiziert nach `(corpus, category)`, fester Seed, "
        "IDs in `eval/calibrate_dataset.py::HOLDOUT_IDS`). Jede Rate hat ihren eigenen "
        "Nenner — die Spalte „Auflösung“ ist deshalb pro Zeile verschieden.",
        "",
        "| Metrik | Holdout | Gate | erreicht | Auflösung (1 Frage) |",
        "|---|---|---|---|---|",
        f"| Halluzinationsrate | {holdout.hallucination_rate:.1%} | = 0 % | "
        f"{'ja' if hallucination_meets else 'nein'} | "
        f"{_resolution(holdout.hallucination_pool_size)} |",
        f"| False-Suppression-Rate (in_corpus) | {holdout.false_suppression_rate:.1%} | "
        f"Zielgrösse, minimiert; CI-Gate ≤ {FALSE_SUPPRESSION_RATE_GATE:.0%} "
        f"(`eval/test_in_corpus_quality.py`) | "
        f"{'ja' if false_suppression_ci_meets else 'nein'} | "
        f"{_resolution(holdout.in_corpus_count)} |",
        f"| Out-of-Corpus-Refusal-Rate | {holdout.out_of_corpus_refusal_rate:.1%} | ≥ 90 % | "
        f"{'ja' if refusal_meets else 'nein'} | {_resolution(holdout.out_of_corpus_count)} |",
        "",
    ]
    if not false_suppression_ci_meets:
        lines += [
            f"**Das empfohlene Set würde ausserdem das bestehende CI-Gate "
            f"(`FALSE_SUPPRESSION_RATE_GATE = {FALSE_SUPPRESSION_RATE_GATE:.0%}`, "
            "`eval/test_in_corpus_quality.py`) nicht bestehen** — ein zweiter, vom "
            "Refusal-Gate unabhängiger Befund dieses Laufs.",
            "",
        ]
    if not holdout_meets_constraints:
        lines += [
            "**Auf dem Holdout erfüllt das empfohlene Set nicht beide ADR-009-Constraints "
            "(Halluzination, Refusal).** Das Train-Set (unten) erfüllte sie; die "
            "Holdout-Bestätigung ist der eigentliche Befund (AC 8) und zeigt eine reale "
            f"Lücke, keine Rundungsdifferenz — bei {holdout.out_of_corpus_count} "
            "Out-of-Corpus-Holdout-Fragen kippt bereits eine einzelne Frage die Rate um "
            "mehr als die zulässige Auflösung. Das Set unten ist deshalb ein **Kandidat, "
            "keine bestätigte Empfehlung**; siehe „Einordnung“ am Ende dieses Berichts.",
            "",
        ]
    lines += [
        "## Train-Zahlen (zur Einordnung, nicht die berichteten Endzahlen)",
        "",
        f"Halluzinationsrate {train.hallucination_rate:.1%}, False-Suppression-Rate "
        f"{train.false_suppression_rate:.1%}, Out-of-Corpus-Refusal-Rate "
        f"{train.out_of_corpus_refusal_rate:.1%} (Train-Split, k-fold-CV für Schicht A1, "
        f"k={k_folds}).",
        "",
        "## Der ausgeschlossene entartete Punkt",
        "",
    ]
    if degenerate is not None:
        lines += [
            'Der Kandidat mit der höchsten In-Corpus-Vor-Generierungs-Suppression im '
            "gesamten A1×A2-Gitter (`retrieval_top_k="
            f"{degenerate.combined.a1.retrieval_top_k}, rrf_k={degenerate.combined.a1.rrf_k}, "
            f"context_top_n={degenerate.combined.a1.context_top_n}, "
            f"similarity_threshold={degenerate.combined.a2.similarity_threshold}, "
            f"min_retrieval_confidence={degenerate.combined.a2.min_retrieval_confidence}`) "
            f"unterdrückt {degenerate.in_corpus_pre_generation_suppression_rate:.1%} der "
            "In-Corpus-Trainingsfragen bereits **vor** der Generierung — geschätzt direkt "
            "aus Schicht A2 (offline), da eine derart unterdrückende Kombination ohnehin für "
            "fast keine Frage eine Antwort generiert. Seine Out-of-Corpus-Refusal-Rate liegt "
            f"bei {degenerate.out_of_corpus_refusal_rate:.1%}. Eine Halluzinationsrate ist für "
            "ihn nicht definiert (keine ausgelieferte Antwort, an der sie gemessen werden "
            "könnte) — nicht 0 %, auch wenn 0 von 0 rechnerisch so aussähe. Dieser Kandidat "
            "wird hier ausdrücklich benannt und ausgeschlossen, nicht stillschweigend "
            "gefiltert (ADR-009: die Gates sind Constraints, nicht die Zielfunktion) — "
            "`select_candidates_for_schicht_b()` wählt gezielt die niedrigste Suppression "
            "für echte Läufe, ein derart entarteter Kandidat erreicht Schicht B deshalb nie "
            "und wird nicht mit echten Antworten bewertet.",
        ]
    else:
        lines += [
            "Kein Kandidat im Gitter konnte ermittelt werden (leeres A1×A2-Gitter) — sollte "
            "bei einem regulären Lauf nicht vorkommen.",
        ]
    lines += [
        "",
        "## Methodische Hinweise",
        "",
        "- **Stichprobe von 1:** `TEMPERATURE = 0.0` macht die Generierung nicht "
        "deterministisch — jeder Kontext wurde in Schicht B genau einmal gesampelt, nicht "
        "mehrfach gemittelt.",
        f"- **Schicht A1 (Ranking)** wurde über k-fold-Cross-Validation (k={k_folds}, "
        "stratifiziert nach Korpus) auf dem Train-Split der 45 `in_corpus`-Fragen "
        "ausgewählt, primär nach F1 aus Recall und Precision im Kontext-Schnitt (nicht nach "
        "Recall allein — Recall wächst mit `context_top_n` nicht-fallend und würde sonst "
        "strukturell den grössten Gitterwert bevorzugen), MRR als Tie-Breaker. A1 hat keinen "
        "Fit-Schritt; was die Folds hier zusätzlich zu einer einzelnen Auswertung über alle "
        "30 Trainingsfragen hergeben, ist die Streuung von F1 über die Folds (`f1_std` in "
        "`eval/calibrate_grid.py::A1Ranked`), nicht ein anderer Mittelwert.",
        "- **`self_check_band_low`** ist an `confidence_threshold_medium` gekoppelt "
        "(bewusste Vereinfachung, spiegelt die bestehende Begründung in "
        "`app/services/config.py`), kein eigener vierter Freiheitsgrad in Schicht C.",
        "",
    ]
    if not holdout_meets_constraints:
        lines += [
            "## Einordnung",
            "",
            "Der Train-Split (30/9/15 Fragen) wählte dieses Set, weil es dort beide "
            "Constraints erfüllte; auf dem unabhängigen Holdout hält die "
            "Out-of-Corpus-Refusal-Rate das 90-%-Gate nicht. Bei so kleinen Fragenmengen "
            "ist das der erwartbare Preis eines einzelnen Laufs, nicht notwendigerweise ein "
            "falsches Parameter-Set — ADR-009s eigener Kommentar zum Issue benennt genau "
            "dieses Risiko vorab. Naheliegende nächste Schritte, keiner davon in diesem "
            "Lauf umgesetzt: ein zweiter, unabhängiger Lauf zur Bestätigung; ein feineres "
            "Gitter um dieses Set herum; oder ein grösseres Gold-Dataset, das die "
            "Holdout-Auflösung verbessert. Bis dahin bleibt der bisherige Startwert "
            "(`similarity_threshold=0.35` etc.) so lange in Kraft, wie ADR-008 es fail-closed "
            "vorschreibt — dieser Bericht ersetzt ihn nicht.",
            "",
        ]
    return "\n".join(lines) + "\n"
