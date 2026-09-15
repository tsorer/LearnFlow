"""T-57: `python -m eval.calibrate` (`make calibrate`) — der Kalibrierungs-Loop aus
ADR-009. Kein pytest-Gate: ein Sweep hat kein Pass/Fail, das AC dazu ("Test oder Werkzeug")
zieht die Trennung bewusst so.

Ablauf, in der Reihenfolge, in der er auch im Code steht:

1. **Snapshot** (`eval/calibrate_snapshot.py`) — einmal embedden/fetchen für alle 80 Fragen.
2. **Schicht A1** (`eval/calibrate_grid.py`) — k-fold-CV über die Ranking-Parameter auf den
   45 `in_corpus`-Trainingsfragen, offline.
3. **Schicht A2** (`eval/calibrate_grid.py`) — Vor-Generierungs-Gates über alle Kategorien,
   offline; Top-N kombinierte (A1×A2)-Sets für Schicht B, plus der entartete Referenzpunkt
   aus demselben Gitter (`worst_case_candidate`, AC 7).
4. **Schicht B** (`eval/calibrate_run.py`) — echte Läufe für den Train-Split, dedupliziert
   nach Kontext, mit erzwungenem Self-Check.
5. **Schicht C + Auswahl** (`eval/calibrate_report.py`) — Bandschwellen-Gitter, offline auf
   den Schicht-B-Ergebnissen, Auswahl unter den Constraints.
6. **Holdout-Bestätigung** — ein weiterer, kleinerer Schicht-B-Lauf nur für den Gewinner auf
   den Holdout-Fragen; die berichteten Endzahlen sind Holdout-Zahlen (AC 8).
7. **Bericht** — `Docs/10_Kalibrierungsbericht.md`, Rohdaten/Snapshot nach
   `eval/out/calibrate/<timestamp>/`.

Läuft im api-Container (`docker exec ... python -m eval.calibrate`), nicht über HTTP: kein
Rate-Limit, direkter Import von `app.services.retrieval`/`app.services.confidence`, wie das
Issue es für den Sweep vorschreibt.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import pathlib
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, engine
from app.services.retrieval import RetrievalHit
from eval.calibrate_dataset import split_adversarial, split_in_corpus, split_out_of_corpus
from eval.calibrate_grid import (
    COMBINED_TOP_N,
    K_FOLDS,
    CombinedCandidate,
    pre_generation_outcome,
    rank_combined_candidates,
    select_a1_candidates,
    worst_case_candidate,
)
from eval.calibrate_report import (
    CandidateReport,
    evaluate_candidate,
    evaluate_full_grid,
    generate_report_markdown,
    select_winner,
)
from eval.calibrate_run import (
    RunResult,
    chunk_contents,
    dedup_key,
    hydrate_context,
    run_once,
    write_runs,
)
from eval.calibrate_snapshot import (
    QuestionSnapshot,
    build_snapshot,
    compute_index_hash,
    load_snapshot,
    verify_index_hash,
    write_snapshot,
)
from eval.gold_dataset import (
    load_adversarial_questions,
    load_corpus_filenames,
    load_in_corpus_questions,
)

logger = logging.getLogger(__name__)

#: `Docs/` selbst ist nicht in den api-Container gemountet (`docker-compose.yml` mountet nur
#: `./backend:/app` und `../LearningCorpus:/LearningCorpus:ro`), also kann dieses Skript
#: `Docs/10_Kalibrierungsbericht.md` nicht direkt schreiben. Es schreibt stattdessen hierher
#: -- `eval/out/` ist ein Bind-Mount, landet also unverändert auf dem Host -- und `make
#: calibrate` kopiert die feste Datei anschliessend host-seitig nach `Docs/`, auch wenn
#: dieses Skript mit 1 endet (kein Parameter-Set erreicht die Constraints, AC 12) -- der
#: `docker exec`-Aufruf im Makefile ist deshalb mit `-` markiert, sonst bricht Make vor der
#: `cp`-Zeile ab und genau dieser Ausgang landet nie in `Docs/`.
LATEST_REPORT_PATH = pathlib.Path(__file__).parent / "out" / "calibrate" / "latest-report.md"


def _write_report(text: str, out_dir: pathlib.Path) -> None:
    """Schreibt den Bericht an zwei Stellen: versioniert im Lauf-Verzeichnis, und -- fest
    überschrieben -- unter `LATEST_REPORT_PATH`, von wo `make calibrate` ihn host-seitig
    nach `Docs/10_Kalibrierungsbericht.md` kopiert."""
    (out_dir / "Kalibrierungsbericht.md").write_text(text, encoding="utf-8")
    LATEST_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_REPORT_PATH.write_text(text, encoding="utf-8")
    logger.info("Bericht geschrieben: %s", LATEST_REPORT_PATH)


def _out_dir() -> pathlib.Path:
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    path = pathlib.Path(__file__).parent / "out" / "calibrate" / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


async def _run_schicht_b(
    db: AsyncSession,
    snapshot_by_id: dict[str, QuestionSnapshot],
    combined_candidates: Sequence[CombinedCandidate],
    question_ids: list[str],
) -> dict[tuple[str, tuple[str, ...]], RunResult]:
    """Echte Läufe für jede eindeutige `(question_id, context)`-Kombination, die mindestens
    einer der `combined_candidates` erreicht (Dedup über alle Kandidaten hinweg, AC 4)."""
    to_run: dict[tuple[str, tuple[str, ...]], tuple[str, list[RetrievalHit]]] = {}
    for candidate in combined_candidates:
        for qid in question_ids:
            question = snapshot_by_id[qid]
            outcome = pre_generation_outcome(question, candidate.a1, candidate.a2)
            if not outcome.passed:
                continue
            # `outcome.context` statt eines zweiten `context_for()`-Aufrufs -- der Kontext
            # ist in `pre_generation_outcome` schon berechnet worden (Review-Befund).
            key = dedup_key(qid, outcome.context)
            to_run.setdefault(key, (question.question, outcome.context))

    logger.info("Schicht B: %d eindeutige (Frage, Kontext)-Läufe", len(to_run))

    results: dict[tuple[str, tuple[str, ...]], RunResult] = {}
    for key, (question_text, context) in to_run.items():
        chunk_ids = [hit.chunk_id for hit in context]
        contents = await chunk_contents(db, chunk_ids)
        hydrated = hydrate_context(context, contents)
        results[key] = await run_once(question_text, key[0], hydrated)
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reuse-snapshot",
        type=pathlib.Path,
        default=None,
        help=(
            "Vorhandenes snapshot.json wiederverwenden statt neu zu embedden/fetchen "
            "(nur beim Iterieren auf Schicht A/B/C selbst sinnvoll). Bricht ab, wenn der "
            "gespeicherte index_hash nicht mehr zum aktuellen Indexstand passt (AC 1)."
        ),
    )
    return parser.parse_args()


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    async with AsyncSessionLocal() as db:
        try:
            return await _run(db, args)
        finally:
            await engine.dispose()


async def _run(db: AsyncSession, args: argparse.Namespace) -> int:
    out_dir = _out_dir()
    if args.reuse_snapshot is not None:
        logger.info("Snapshot wiederverwenden: %s", args.reuse_snapshot)
        snapshot = load_snapshot(args.reuse_snapshot)
        verify_index_hash(snapshot, await compute_index_hash(db))
    else:
        logger.info("Snapshot...")
        snapshot = await build_snapshot(db)
        write_snapshot(snapshot, out_dir)
    snapshot_by_id = {q.id: q for q in snapshot.questions}
    logger.info(
        "Snapshot: %d Fragen, index_hash=%s", len(snapshot.questions), snapshot.index_hash
    )

    # Einmal geladen, an jeden Aufruf durchgereicht statt bei jedem Kandidaten neu geparst
    # (Review-Befund: `evaluate_full_grid` wertet ~1000 Kandidaten aus, jeder mit eigenem
    # YAML-Parse wäre spürbar langsamer, ohne dass sich der Inhalt je ändert).
    corpus_filenames = load_corpus_filenames()
    expected_pages_in_corpus = {
        q.id: q.expected_source.pages for q in load_in_corpus_questions()
    }
    expected_pages_adversarial = {
        q.id: q.expected_source.pages
        for q in load_adversarial_questions()
        if q.expected_source is not None
    }

    in_corpus_train, in_corpus_holdout = split_in_corpus()
    adversarial_train, adversarial_holdout = split_adversarial()
    ooc_train, ooc_holdout = split_out_of_corpus()

    adversarial_scored_train = [q.id for q in adversarial_train if not q.expected_refusal]
    adversarial_scored_holdout = [q.id for q in adversarial_holdout if not q.expected_refusal]

    logger.info("Schicht A1 (k-fold-CV)...")
    a1_ranked = select_a1_candidates(snapshot.questions, [q.id for q in in_corpus_train])
    logger.info(
        "Top-A1: %s", [(r.candidate, round(r.mean_f1, 3), round(r.f1_std, 3)) for r in a1_ranked]
    )

    logger.info("Schicht A2 (Vor-Generierungs-Gates)...")
    a1_candidates = [r.candidate for r in a1_ranked]
    a2_ranked = rank_combined_candidates(
        snapshot.questions,
        a1_candidates,
        out_of_corpus_train_ids=[q.id for q in ooc_train],
        in_corpus_train_ids=[q.id for q in in_corpus_train],
    )
    combined = [r.combined for r in a2_ranked[:COMBINED_TOP_N]]
    degenerate = worst_case_candidate(a2_ranked)
    logger.info(
        "%d kombinierte Kandidaten gehen in Schicht B; entarteter Referenzpunkt: "
        "Suppression=%.1f%%, Refusal=%.1f%%",
        len(combined),
        degenerate.in_corpus_pre_generation_suppression_rate * 100,
        degenerate.out_of_corpus_refusal_rate * 100,
    )

    train_ids = (
        [q.id for q in in_corpus_train] + adversarial_scored_train + [q.id for q in ooc_train]
    )
    logger.info("Schicht B (Train, echte Läufe)...")
    run_results = await _run_schicht_b(db, snapshot_by_id, combined, train_ids)
    write_runs(list(run_results.values()), out_dir)

    logger.info("Schicht C (Bandschwellen-Gitter, offline)...")
    train_reports: list[CandidateReport] = evaluate_full_grid(
        combined,
        snapshot_by_id,
        run_results,
        [q.id for q in in_corpus_train],
        adversarial_scored_train,
        [q.id for q in ooc_train],
        corpus_filenames,
        expected_pages_in_corpus,
        expected_pages_adversarial,
    )
    winner_train = select_winner(train_reports)

    if winner_train is None:
        logger.warning(
            "Kein Parameter-Set im Gitter erreicht die Constraints "
            "(Halluzination = 0%%, Out-of-Corpus-Refusal >= 90%%)."
        )
        report_text = (
            "# Kalibrierungsbericht (T-57)\n\n"
            f"Lauf vom {snapshot.created_at}. Kein Parameter-Set im gesweepten Gitter "
            "erreichte beide Constraints (Halluzinationsrate = 0 %, "
            "Out-of-Corpus-Refusal ≥ 90 %) gleichzeitig -- siehe `eval/out/calibrate/` "
            "für die vollständigen Rohdaten dieses Laufs. Das Gitter "
            "(`eval/calibrate_grid.py`, `eval/calibrate_report.py`) ist ein Startpunkt, "
            "kein erschöpfender Beweis der Unerreichbarkeit -- ein feineres oder "
            "breiteres Gitter ist der naheliegende nächste Schritt.\n"
        )
        _write_report(report_text, out_dir)
        return 1

    logger.info("Holdout-Bestätigung für den Gewinner...")
    winner_full = winner_train.full
    winner_combined = CombinedCandidate(a1=winner_full.a1, a2=winner_full.a2)
    holdout_ids = (
        [q.id for q in in_corpus_holdout]
        + adversarial_scored_holdout
        + [q.id for q in ooc_holdout]
    )
    holdout_runs = await _run_schicht_b(db, snapshot_by_id, [winner_combined], holdout_ids)
    write_runs(list(holdout_runs.values()), out_dir / "holdout")

    holdout_report = evaluate_candidate(
        winner_full,
        snapshot_by_id,
        holdout_runs,
        [q.id for q in in_corpus_holdout],
        adversarial_scored_holdout,
        [q.id for q in ooc_holdout],
        corpus_filenames,
        expected_pages_in_corpus,
        expected_pages_adversarial,
    )

    report_text = generate_report_markdown(
        train=winner_train,
        holdout=holdout_report,
        holdout_size=len(in_corpus_holdout),
        degenerate=degenerate,
        ran_at=snapshot.created_at,
        k_folds=K_FOLDS,
    )
    _write_report(report_text, out_dir)
    logger.info("Rohdaten: %s", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
