# Kalibrierungsbericht (T-57)

Lauf vom 2026-09-15T19-03-53Z. Erzeugt von `eval/calibrate.py` (`make calibrate`) — Rohdaten und Snapshot in `eval/out/calibrate/`.

## Empfohlenes Parameter-Set

| Parameter | Wert |
|---|---|
| `retrieval_top_k` | 20 |
| `rrf_k` | 20 |
| `context_top_n` | 3 |
| `similarity_threshold` | 0.2 |
| `min_retrieval_confidence` | 0.2 |
| `min_citation_coverage` | 0.3 |
| `confidence_threshold_medium` | 0.3 |
| `confidence_threshold_high` | 0.6 (nicht optimierbar, nach Urteil gesetzt — siehe unten) |
| `self_check_band_low` | 0.3 (an `confidence_threshold_medium` gekoppelt) |
| `self_check_band_high` | 0.6 |

`confidence_threshold_high` unterdrückt nichts — `band_for()` nutzt es nur für die Unterscheidung „mittel“ vs. „hoch“, unterdrückt wird ausschliesslich über `confidence_threshold_medium` (`BAND_LOW`). Der Wert oben ist deshalb kein Sweep-Ergebnis, sondern gleich dem gewinnenden `self_check_band_high` gesetzt, damit „hoch“ exakt dort beginnt, wo der Self-Check nichts mehr beiträgt.

## Ergebnis auf dem Holdout

Holdout: 15 `in_corpus`-Fragen, 7 `out_of_corpus`-Fragen (stratifiziert nach `(corpus, category)`, fester Seed, IDs in `eval/calibrate_dataset.py::HOLDOUT_IDS`). Jede Rate hat ihren eigenen Nenner — die Spalte „Auflösung“ ist deshalb pro Zeile verschieden.

| Metrik | Holdout | Gate | erreicht | Auflösung (1 Frage) |
|---|---|---|---|---|
| Halluzinationsrate | 0.0% | = 0 % | ja | 7.7 pp |
| False-Suppression-Rate (in_corpus) | 26.7% | Zielgrösse, minimiert; CI-Gate ≤ 15% (`eval/test_in_corpus_quality.py`) | nein | 6.7 pp |
| Out-of-Corpus-Refusal-Rate | 85.7% | ≥ 90 % | nein | 14.3 pp |

**Das empfohlene Set würde ausserdem das bestehende CI-Gate (`FALSE_SUPPRESSION_RATE_GATE = 15%`, `eval/test_in_corpus_quality.py`) nicht bestehen** — ein zweiter, vom Refusal-Gate unabhängiger Befund dieses Laufs.

**Auf dem Holdout erfüllt das empfohlene Set nicht beide ADR-009-Constraints (Halluzination, Refusal).** Das Train-Set (unten) erfüllte sie; die Holdout-Bestätigung ist der eigentliche Befund (AC 8) und zeigt eine reale Lücke, keine Rundungsdifferenz — bei 7 Out-of-Corpus-Holdout-Fragen kippt bereits eine einzelne Frage die Rate um mehr als die zulässige Auflösung. Das Set unten ist deshalb ein **Kandidat, keine bestätigte Empfehlung**; siehe „Einordnung“ am Ende dieses Berichts.

## Train-Zahlen (zur Einordnung, nicht die berichteten Endzahlen)

Halluzinationsrate 0.0%, False-Suppression-Rate 40.0%, Out-of-Corpus-Refusal-Rate 93.3% (Train-Split, k-fold-CV für Schicht A1, k=5).

## Der ausgeschlossene entartete Punkt

Der Kandidat mit der höchsten In-Corpus-Vor-Generierungs-Suppression im gesamten A1×A2-Gitter (`retrieval_top_k=10, rrf_k=20, context_top_n=3, similarity_threshold=0.4, min_retrieval_confidence=0.6`) unterdrückt 16.7% der In-Corpus-Trainingsfragen bereits **vor** der Generierung — geschätzt direkt aus Schicht A2 (offline), da eine derart unterdrückende Kombination ohnehin für fast keine Frage eine Antwort generiert. Seine Out-of-Corpus-Refusal-Rate liegt bei 20.0%. Eine Halluzinationsrate ist für ihn nicht definiert (keine ausgelieferte Antwort, an der sie gemessen werden könnte) — nicht 0 %, auch wenn 0 von 0 rechnerisch so aussähe. Dieser Kandidat wird hier ausdrücklich benannt und ausgeschlossen, nicht stillschweigend gefiltert (ADR-009: die Gates sind Constraints, nicht die Zielfunktion) — `select_candidates_for_schicht_b()` wählt gezielt die niedrigste Suppression für echte Läufe, ein derart entarteter Kandidat erreicht Schicht B deshalb nie und wird nicht mit echten Antworten bewertet.

## Methodische Hinweise

- **Stichprobe von 1:** `TEMPERATURE = 0.0` macht die Generierung nicht deterministisch — jeder Kontext wurde in Schicht B genau einmal gesampelt, nicht mehrfach gemittelt.
- **Schicht A1 (Ranking)** wurde über k-fold-Cross-Validation (k=5, stratifiziert nach Korpus) auf dem Train-Split der 45 `in_corpus`-Fragen ausgewählt, primär nach F1 aus Recall und Precision im Kontext-Schnitt (nicht nach Recall allein — Recall wächst mit `context_top_n` nicht-fallend und würde sonst strukturell den grössten Gitterwert bevorzugen), MRR als Tie-Breaker. A1 hat keinen Fit-Schritt; was die Folds hier zusätzlich zu einer einzelnen Auswertung über alle 30 Trainingsfragen hergeben, ist die Streuung von F1 über die Folds (`f1_std` in `eval/calibrate_grid.py::A1Ranked`), nicht ein anderer Mittelwert.
- **`self_check_band_low`** ist an `confidence_threshold_medium` gekoppelt (bewusste Vereinfachung, spiegelt die bestehende Begründung in `app/services/config.py`), kein eigener vierter Freiheitsgrad in Schicht C.

## Einordnung

Der Train-Split (30/9/15 Fragen) wählte dieses Set, weil es dort beide Constraints erfüllte; auf dem unabhängigen Holdout hält die Out-of-Corpus-Refusal-Rate das 90-%-Gate nicht. Bei so kleinen Fragenmengen ist das der erwartbare Preis eines einzelnen Laufs, nicht notwendigerweise ein falsches Parameter-Set — ADR-009s eigener Kommentar zum Issue benennt genau dieses Risiko vorab. Naheliegende nächste Schritte, keiner davon in diesem Lauf umgesetzt: ein zweiter, unabhängiger Lauf zur Bestätigung; ein feineres Gitter um dieses Set herum; oder ein grösseres Gold-Dataset, das die Holdout-Auflösung verbessert. Bis dahin bleibt der bisherige Startwert (`similarity_threshold=0.35` etc.) so lange in Kraft, wie ADR-008 es fail-closed vorschreibt — dieser Bericht ersetzt ihn nicht.

