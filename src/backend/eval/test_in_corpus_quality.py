"""T-56: Halluzinationsrate, False-Suppression-Rate und Context-Recall/
Precision/MRR gegen die 45 `in_corpus`- und 13 `adversarial`-Fragen des
Gold-Datasets (ADR-009, Abschnitt 2A/2B). Ergänzt
`eval/test_out_of_corpus_refusal.py` (T-28), der nur die 22 `out_of_corpus`-
Fragen deckt -- zusammen decken die beiden Tests alle 80 Fragen.

Wie der Refusal-Test seit T-55 in-process gegen die ASGI-App, in derselben
zurückgerollten Transaktion und gegen dieselben Seed-Defaults
(`eval/conftest.py`) -- zwei Läufe sind damit vergleichbar, egal welche
Schwellen lokal kalibriert sind. Anders als out-of-corpus-Fragen erreichen
diese Fragen wirklich Generierung (und im Self-Check-Grenzband einen zweiten
LLM-Aufruf): das Retrieval-Gate greift bei einer beantwortbaren Frage nicht.

Die Metrik-Logik selbst steht in `eval/metrics.py` (reine Funktionen, isoliert
testbar über `tests/test_eval_metrics.py`) -- dieses Modul treibt nur den
Lauf: Fragen stellen, Antworten einsammeln, die Metriken darüberlegen,
CSV/JSON schreiben, Gates prüfen.

## Was gemessen wird, und woraus

  - **Halluzinationsrate** (Gate: = 0 %) -- über die 45 `in_corpus`- und die
    11 `adversarial`-Fragen mit `expected_refusal: false`, aber nur für
    tatsächlich ausgelieferte Antworten (`eval/metrics.py::check_hallucination`,
    H1/H2). Eine unterdrückte Antwort hat keinen Text, an dem H1/H2 etwas
    prüfen könnten. Die Prüfung selbst braucht keine `expected_source` (H1/H2
    vergleichen nur gegen das zugesagte Korpusdokument, nicht gegen eine
    Seite) -- sie läuft für jede ausgelieferte Antwort im Geltungsbereich,
    unabhängig davon, ob das Dataset eine Quelle nennt. Andernfalls würde eine
    künftige `adversarial`-Frage ohne Quelle (vom Schema erlaubt, siehe
    `tests/test_gold_eval_dataset.py::test_in_corpus_questions_name_a_source`
    -- nur für `in_corpus` erzwungen) im Nenner mitzählen, aber nie bewertet
    werden, und das 0-%-Gate stillschweigend verwässern (Review zu #131).
  - **False-Suppression-Rate** (Gate: <= 15 % Startwert) -- nur über die 45
    `in_corpus`-Fragen, jede Unterdrückung zählt, `generation_truncated`
    eingeschlossen: eine abgeschnittene Antwort ist so wenig beim Nutzer
    angekommen wie eine explizit verweigerte, und das Issue definiert False-
    Suppression über das Ergebnis ("unterdrückt, obwohl der Korpus die
    Antwort hergibt"), nicht über die Ursache. Anders als `configuration_error`
    (siehe unten) ist eine Kürzung kein Infrastrukturfehler, der die Messung
    ungültig macht, sondern ein Pipeline-Verhalten unter den gemessenen
    Budgets -- für das Produktivprofil unwahrscheinlich (grosszügiges
    `max_answer_tokens`), aber kein Grund, den Fall auszunehmen, sollte er
    auftreten. Die `adversarial`-Fragen sind absichtlich Grenzfälle; eine
    Unterdrückung dort ist vertretbares Fail-closed-Verhalten (ADR-008) und
    ginge als falsches Signal in dasselbe Gate wie eine zu breite Frage.
  - **Adversarial-Refusal** (kein Gate, n=2) -- die beiden `adversarial`-
    Fragen mit `expected_refusal: true` (`SKOS-ADV-02`, `SKOS-IPV-02`),
    separat ausgewiesen. Zwei Fragen tragen kein eigenes Gate.
  - **Context-Recall@k/Precision@k, MRR** (kein Gate) -- über alle 56 Fragen
    mit `expected_source` (also nicht die beiden adversarial-Refusals), je
    zwei Schnitte je Frage: top-k (alle Kandidaten) und Kontext (`in_top_n`,
    siehe `eval/metrics.py`). Anders als die Halluzinationsrate braucht diese
    Gruppe die Seiten aus `expected_source` zwingend -- ohne sie gibt es
    nichts, gegen das Recall zählen könnte.

`configuration_error` (dieselbe Ausnahme wie im Refusal-Test) lässt den Lauf
abbrechen statt eine ungültige Messung als False-Suppression zu zählen.
"""

import csv
import json
import os
import pathlib
from typing import Any

import httpx
import pytest

from eval.conftest import _out_dir
from eval.gold_dataset import (
    AdversarialQuestion,
    InCorpusQuestion,
    assert_corpus_is_indexed_async,
    load_adversarial_questions,
    load_corpus_filenames,
    load_in_corpus_questions,
)
from eval.metrics import check_hallucination, retrieval_metrics
from eval.profiles import Profile

HALLUCINATION_RATE_GATE = 0.0  # ADR-009 Gruppe A, hartes Gate
FALSE_SUPPRESSION_RATE_GATE = 0.15  # ADR-009 Gruppe A, Startwert

# Dieselbe Ausnahme wie im Refusal-Test: ein infrastruktureller Fehlschlag,
# kein fachliches Ergebnis.
CONFIGURATION_ERROR = "configuration_error"

CSV_COLUMNS = [
    "id",
    "category",
    "corpus",
    "expected_refusal",
    "suppressed",
    "suppression_reason",
    "hallucinated",
    "hallucination_reason",
    "grounded_in_expected_pages",
    "confidence_score",
    "confidence_band",
    "retrieval_score",
    "citation_coverage",
    "self_check_ran",
    "self_check_verdict",
    "recall_top_k",
    "precision_top_k",
    "mrr_top_k",
    "recall_context",
    "precision_context",
    "mrr_context",
]

#: Für den Aggregat-Block in run.json (Fix zu Review-Befund #7): dieselben
#: sechs Metriken, die eval/compare.py-artig gemittelt werden, für beide
#: Kategorien getrennt.
_RETRIEVAL_METRIC_FIELDS = (
    "recall_top_k",
    "precision_top_k",
    "mrr_top_k",
    "recall_context",
    "precision_context",
    "mrr_context",
)


@pytest.fixture
def in_corpus_out_dir(profile: Profile) -> pathlib.Path:
    """`eval/out/<profil>/in-corpus/<zeitstempel>/` -- ein eigenes
    Unterverzeichnis, nicht `eval_out_dir` (aus `eval/conftest.py`, für den
    Refusal-Test); Begründung für `"in-corpus"` als eigene Ebene steht bei
    `eval/conftest.py::_out_dir`.
    """
    return _out_dir(profile, "in-corpus")


def _avg(values: list[float | None]) -> float | None:
    """Mittelwert über die vorhandenen Werte, `None` wenn keiner vorliegt --
    für den Aggregat-Block in run.json. Eine unbewertete Frage (kein
    `expected_source`, kommt heute nicht vor) liefert `None` und fällt aus der
    Mittelung heraus, statt sie als 0 zu verfälschen.
    """
    present = [v for v in values if v is not None]
    return round(sum(present) / len(present), 4) if present else None


def _write_run_json(
    out_dir: pathlib.Path,
    profile: Profile,
    measured_config: dict[str, object],
    *,
    hallucination_rate: float,
    hallucination_pool_size: int,
    false_suppression_rate: float,
    in_corpus_count: int,
    adversarial_refusal_rate: float | None,
    adversarial_refusal_count: int,
    retrieval_metrics_summary: dict[str, dict[str, float | int | None]],
) -> None:
    (out_dir / "run.json").write_text(
        json.dumps(
            {
                "profile": profile.name,
                "model": profile.model,
                "gated": profile.gated,
                # Wie im Refusal-Test: was ein Profil überschreiben darf, ist
                # in eval/profiles.py begründet (Review zu #131, Runbook nennt
                # "Überschreibungen" als festen Bestandteil von run.json).
                "overrides": {
                    "timeout_seconds": profile.timeout_seconds,
                    "max_answer_tokens": profile.max_answer_tokens,
                    "self_check_timeout_seconds": profile.self_check_timeout_seconds,
                    "max_verdict_tokens": profile.max_verdict_tokens,
                    "extra_completion_kwargs": profile.extra_completion_kwargs,
                },
                "measured_config": {k: str(v) for k, v in measured_config.items()},
                "hallucination_rate": round(hallucination_rate, 4),
                "hallucination_pool_size": hallucination_pool_size,
                "hallucination_gate": HALLUCINATION_RATE_GATE,
                "false_suppression_rate": round(false_suppression_rate, 4),
                "in_corpus_count": in_corpus_count,
                "false_suppression_gate": FALSE_SUPPRESSION_RATE_GATE,
                "adversarial_refusal_rate": (
                    round(adversarial_refusal_rate, 4)
                    if adversarial_refusal_rate is not None
                    else None
                ),
                "adversarial_refusal_count": adversarial_refusal_count,
                # Gruppe B (ADR-009): kein Gate, aber die Aggregate, die ein
                # Bericht zitiert, müssen aus run.json rekonstruierbar sein --
                # vorher nur per Ad-hoc-Skript über results.csv (Review #7).
                "retrieval_metrics": retrieval_metrics_summary,
                # Vom Makefile gesetzt, wie im Refusal-Test.
                "git_sha": os.environ.get("EVAL_GIT_SHA"),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


async def test_in_corpus_quality(
    client: httpx.AsyncClient,
    token: str,
    profile: Profile,
    measured_config: dict[str, object],
    in_corpus_out_dir: pathlib.Path,
    llm_trace: list[dict[str, Any]],
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    await assert_corpus_is_indexed_async(client, headers)

    filenames = load_corpus_filenames()
    in_corpus = load_in_corpus_questions()
    adversarial = load_adversarial_questions()
    # Wie im Refusal-Test: eine spätere Änderung an den Seeds, die die Menge
    # unter das im Issue zugesagte Mass drückt, soll das Gate melden statt
    # eine kleinere, leichtere Stichprobe still durchzuwinken.
    assert len(in_corpus) >= 40, (
        f"Expected at least 40 in-corpus questions, found {len(in_corpus)}"
    )
    assert len(adversarial) >= 10, (
        f"Expected at least 10 adversarial questions, found {len(adversarial)}"
    )

    questions: list[tuple[InCorpusQuestion | AdversarialQuestion, str]] = [
        *((q, "in_corpus") for q in in_corpus),
        *((q, "adversarial") for q in adversarial),
    ]

    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    results_csv = in_corpus_out_dir / "results.csv"

    with results_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)

        for q, category in questions:
            # `isinstance(q, ...)` direkt in der Ternary, nicht über eine
            # zwischengespeicherte bool-Variable: mypy verengt die Union nur
            # aus einer isinstance-Prüfung auf `q` selbst am Ort des Zugriffs,
            # nicht aus einem Vergleich auf der Nebenvariable `category` --
            # und auch nicht mehr, sobald das isinstance-Ergebnis erst in
            # einer eigenen Variable zwischenlandet (Review #5 -- `mypy eval`
            # meldete hier einen union-attr-Fehler, unsichtbar für `make qa`,
            # das nur `mypy app worker` prüft).
            expected_refusal = (
                q.expected_refusal if isinstance(q, AdversarialQuestion) else False
            )
            # Geltungsbereich der Halluzinationsprüfung (siehe Moduldoc): jede
            # Frage ausser den beiden adversarial-Refusal-Fällen.
            scored_for_hallucination = not (category == "adversarial" and expected_refusal)

            trace_from = len(llm_trace)
            r = await client.post("/api/query", json={"question": q.question}, headers=headers)
            assert r.status_code == 200, r.text
            body = r.json()
            details.append(
                {
                    "id": q.id,
                    "category": category,
                    "question": q.question,
                    "response": body,
                    "llm_trace": llm_trace[trace_from:],
                }
            )

            reason = body.get("suppression_reason")
            # Eine ungültige Messung soll den Lauf laut abbrechen statt eine
            # Infrastruktur-Panne als False-Suppression zu zählen (Review zu
            # #128, dieselbe Begründung wie im Refusal-Test).
            assert reason != CONFIGURATION_ERROR, (
                f"{q.id}: configuration_error -- Lauf ungültig (Konfiguration "
                f"unlesbar), siehe {results_csv}. Schwellenwerte prüfen statt "
                "das Ergebnis zu werten."
            )
            suppressed = bool(body["suppressed"])
            debug = body.get("debug") or {}
            confidence = body.get("confidence") or {}

            hallucinated: bool | None = None
            hallucination_reason: str | None = None
            grounded: bool | None = None
            if not suppressed and scored_for_hallucination:
                # `()` wenn das Dataset keine Seiten nennt: H1/H2 brauchen nur
                # das zugesagte Korpusdokument, nicht dessen Seiten --
                # `grounded_in_expected_pages` (Zusatzsignal, kein Gate) wird
                # dann einfach False, aber die Halluzinationsprüfung selbst
                # bleibt scharf (siehe Moduldoc, Review #2).
                expected_pages = q.expected_source.pages if q.expected_source else ()
                verdict = check_hallucination(
                    answer=body.get("message") or "",
                    citations=body.get("citations") or [],
                    corpus_filename=filenames[q.corpus],
                    expected_pages=expected_pages,
                )
                hallucinated = verdict.hallucinated
                hallucination_reason = verdict.reason
                grounded = verdict.grounded_in_expected_pages

            recall_k = precision_k = mrr_k = None
            recall_ctx = precision_ctx = mrr_ctx = None
            if q.expected_source is not None:
                chunks = debug.get("chunks") or []
                context_chunks = [c for c in chunks if c.get("in_top_n")]

                expected_pages = q.expected_source.pages
                m_top_k = retrieval_metrics(
                    chunks, corpus_filename=filenames[q.corpus], expected_pages=expected_pages
                )
                m_context = retrieval_metrics(
                    context_chunks,
                    corpus_filename=filenames[q.corpus],
                    expected_pages=expected_pages,
                )
                recall_k, precision_k, mrr_k = m_top_k.recall, m_top_k.precision, m_top_k.mrr
                recall_ctx, precision_ctx, mrr_ctx = (
                    m_context.recall,
                    m_context.precision,
                    m_context.mrr,
                )

            writer.writerow(
                [
                    q.id,
                    category,
                    q.corpus,
                    expected_refusal,
                    suppressed,
                    reason,
                    hallucinated,
                    hallucination_reason,
                    grounded,
                    confidence.get("score"),
                    confidence.get("band"),
                    confidence.get("retrieval_score"),
                    confidence.get("citation_coverage"),
                    debug.get("self_check_ran"),
                    debug.get("self_check_verdict"),
                    recall_k,
                    precision_k,
                    mrr_k,
                    recall_ctx,
                    precision_ctx,
                    mrr_ctx,
                ]
            )
            f.flush()  # eine Zeile überlebt, auch wenn eine spätere Frage abbricht

            rows.append(
                {
                    "category": category,
                    "expected_refusal": expected_refusal,
                    "scored_for_hallucination": scored_for_hallucination,
                    "suppressed": suppressed,
                    "hallucinated": hallucinated,
                    "recall_top_k": recall_k,
                    "precision_top_k": precision_k,
                    "mrr_top_k": mrr_k,
                    "recall_context": recall_ctx,
                    "precision_context": precision_ctx,
                    "mrr_context": mrr_ctx,
                }
            )

    # -- Halluzinationsrate: siehe scored_for_hallucination oben, nur
    #    ausgelieferte Antworten (Moduldoc). --
    hallucination_pool = [
        row for row in rows if row["scored_for_hallucination"] and not row["suppressed"]
    ]
    hallucinated_count = sum(1 for row in hallucination_pool if row["hallucinated"])
    hallucination_rate = (
        hallucinated_count / len(hallucination_pool) if hallucination_pool else 0.0
    )

    # -- False-Suppression: nur in_corpus, jede Unterdrückung zählt
    #    (generation_truncated eingeschlossen -- siehe Moduldoc). --
    in_corpus_rows = [row for row in rows if row["category"] == "in_corpus"]
    suppressed_count = sum(1 for row in in_corpus_rows if row["suppressed"])
    false_suppression_rate = suppressed_count / len(in_corpus_rows)

    # -- Adversarial-Refusal: n=2, kein Gate. --
    adversarial_refusal_rows = [
        row for row in rows if row["category"] == "adversarial" and row["expected_refusal"]
    ]
    adversarial_refused = sum(1 for row in adversarial_refusal_rows if row["suppressed"])
    adversarial_refusal_rate = (
        adversarial_refused / len(adversarial_refusal_rows) if adversarial_refusal_rows else None
    )

    # -- Gruppe B, gemittelt je Kategorie (kein Gate, Eingabe für T-57). --
    retrieval_metrics_summary: dict[str, dict[str, float | int | None]] = {}
    for category in ("in_corpus", "adversarial"):
        category_rows = [row for row in rows if row["category"] == category]
        summary: dict[str, float | int | None] = {
            field: _avg([row[field] for row in category_rows]) for field in _RETRIEVAL_METRIC_FIELDS
        }
        # Wie viele der Fragen dieser Kategorie tatsächlich in die Mittelung
        # eingingen -- die beiden adversarial-Refusal-Fragen haben keine
        # expected_source und damit kein recall_top_k (Review #12: der
        # Vorläuferbericht beschriftete die Fragenzahl fix statt sie aus dem
        # Lauf zu lesen).
        summary["scored_questions"] = sum(
            1 for row in category_rows if row["recall_top_k"] is not None
        )
        retrieval_metrics_summary[category] = summary

    _write_run_json(
        in_corpus_out_dir,
        profile,
        measured_config,
        hallucination_rate=hallucination_rate,
        hallucination_pool_size=len(hallucination_pool),
        false_suppression_rate=false_suppression_rate,
        in_corpus_count=len(in_corpus_rows),
        adversarial_refusal_rate=adversarial_refusal_rate,
        adversarial_refusal_count=len(adversarial_refusal_rows),
        retrieval_metrics_summary=retrieval_metrics_summary,
    )
    (in_corpus_out_dir / "details.json").write_text(
        json.dumps(details, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"\nProfil {profile.name} ({profile.model})")
    print(
        f"Halluzinationsrate: {hallucination_rate:.1%} "
        f"({hallucinated_count}/{len(hallucination_pool)} ausgelieferte Antworten)"
    )
    print(
        f"False-Suppression-Rate: {false_suppression_rate:.1%} "
        f"({suppressed_count}/{len(in_corpus_rows)} in_corpus-Fragen)"
    )
    if adversarial_refusal_rate is not None:
        print(
            f"Adversarial-Refusal: {adversarial_refusal_rate:.0%} "
            f"({adversarial_refused}/{len(adversarial_refusal_rows)}) -- kein Gate"
        )
    print(f"Per-question results: {in_corpus_out_dir}")

    if not profile.gated:
        # Ein Vergleichslauf ist eine Messreihe, kein Release-Gate (T-55).
        print(f"Profil {profile.name} ist nicht gated -- Ergebnis gemeldet, kein Gate.")
        return

    # `<=`, nicht `==`: liest wie jede andere Schwelle in dieser Codebase
    # (confidence.py, das False-Suppression-Gate direkt darunter) und bleibt
    # korrekt, sollte das Gate je eine Toleranz statt eines exakten Nullpunkts
    # bekommen. Heute rechnerisch gleichwertig -- hallucinated_count/n mit
    # hallucinated_count=0 ergibt exakt 0.0 -- aber `<=` ist die richtige
    # Semantik für "Gate", nicht `==` (Review #3).
    assert hallucination_rate <= HALLUCINATION_RATE_GATE, (
        f"Halluzinationsrate {hallucination_rate:.1%} über dem 0%-Gate (ADR-009): "
        f"{hallucinated_count}/{len(hallucination_pool)} ausgelieferte Antworten waren "
        f"halluziniert (H1/H2, eval/metrics.py). Details: {in_corpus_out_dir}"
    )
    assert false_suppression_rate <= FALSE_SUPPRESSION_RATE_GATE, (
        f"False-Suppression-Rate {false_suppression_rate:.1%} über dem "
        f"{FALSE_SUPPRESSION_RATE_GATE:.0%}-Startwert (ADR-009): "
        f"{suppressed_count}/{len(in_corpus_rows)} in_corpus-Fragen wurden unterdrückt. "
        f"Details: {in_corpus_out_dir}"
    )
