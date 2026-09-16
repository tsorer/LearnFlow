# Chatverlauf — T-56 In-Corpus-Eval (Halluzinationsrate, False-Suppression, Context-Recall)

**Datum:** 2026-09-11 bis 2026-09-14
**Branch:** `feat/T-56-in-corpus-eval`, von `origin/main`.
**Gegenstand:** [#124](https://github.com/tsorer/LearnFlow/issues/124) „[T-56] In-Corpus-Eval: Halluzinationsrate, False-Suppression und Context-Recall messen" (ADR-009 Abschnitt 2). Der bestehende Eval-Harness deckte nur die 22 `out_of_corpus`-Fragen (T-28); die 45 `in_corpus`- und 13 `adversarial`-Fragen des Gold-Datasets wertete keine Instanz aus.
**Ergebnis:** [PR #133](https://github.com/tsorer/LearnFlow/pull/133), zwei Commits (`8f2fd4c` squashter Feature-Commit, `8222a12` Review-Fix), approved von `luenlestra`, CI grün, offen zum Mergen.

> Nutzer-Prompts wörtlich aus dem Sitzungstranskript. Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/124. Frage bei Unklarheiten nach

### Claude

Issue, ADR-009, den bestehenden Harness (`eval/test_out_of_corpus_refusal.py`, `eval/conftest.py` seit T-55 in-process, `eval/gold_dataset.py`, `eval/profiles.py`, `eval/compare.py`), das Gold-Dataset (`LearningCorpus/gold-eval-dataset.yaml`, 80 Fragen: 45/22/13) und die openapi-Schemas (`QueryResponse`, `ChunkDebugInfo`, `Citation`) gelesen. Festgestellt: lokales `main` lag hinter `origin/main` (T-55 war zwischenzeitlich gemergt).

Drei Rückfragen gestellt:

1. Operationalisierung der Halluzinationsrate — deterministisch mit Quellen-Join, nur Coverage/Validity (zirkulär), oder zusätzlich ein LLM-Judge.
2. Umgang mit den 13 `adversarial`-Fragen — auswerten und getrennt ausweisen, wie `in_corpus` behandeln, oder ausnehmen.
3. Verhalten, wenn der erste Lauf die Gates nicht hält.

Nutzer fragte bei Option 3 der ersten Frage nach: „Mit Punkt 3 ist ein weiteres Modell gemeint oder wieso Modellwahl?" — bestätigt: ADR-009 verlangt für den Judge ausdrücklich ein zweites, stärkeres Modell, nicht das Antwortmodell selbst, was eine neue Profil-Konfiguration, einen eigenen ADR-009/ADR-004-Entscheid und zusätzliche Kosten pro Lauf bedeutet hätte. Mit dieser Präzisierung erneut gefragt — Nutzer entschied sich für deterministisch, kein Judge. Bei Frage 2 „Auswerten, getrennt ausweisen" gewählt. Bei Frage 3 bestätigt, dass ein reissendes Gate ein Befund ist, kein Grund zum Aufweichen: „Genau genommen ändern wir nichts sondern es wird nur sichtbar, was auch schon vorher nicht stimmt, oder? Daher ist Punkt 1 wohl die beste Wahl."

Umsetzungsplan geliefert: `eval/metrics.py` (reine Metrik-Logik, isoliert testbar) mit H1/H2-Halluzinationsprüfung über einen Quellen-Join statt reiner Coverage, `eval/gold_dataset.py`-Erweiterung um `corpus`/`expected_source` und `load_adversarial_questions`, ein zweiter Testlauf `eval/test_in_corpus_quality.py`, Korrekturen an zwei veralteten Annahmen im Issue (Laufzeitschätzung, `eval_out_dir`-Kollision zwischen zwei Tests in einem `make eval`), keine Spec-Änderung nötig.

---

## 2 — Nutzer

> du kannst es direkt umsetzen

*(Modellwechsel auf Sonnet 5 per `/model` unmittelbar davor.)*

### Claude

Branch `feat/T-56-in-corpus-eval` von `origin/main` erstellt. Umgesetzt:

- `eval/gold_dataset.py`: `InCorpusQuestion` um `corpus`/`expected_source` erweitert (additiv, `perf/` bleibt unberührt), neue `AdversarialQuestion`/`ExpectedSource`-Dataclasses, `load_adversarial_questions()`, `load_corpus_filenames()`.
- `eval/metrics.py` (neu): `check_hallucination` (H1: erfundene Referenz, H2: keine benutzte Citation aus dem zugesagten Korpusdokument) über `app/services/confidence.check_citations`; `retrieval_metrics` (Recall als Seitendeckung, Precision, MRR) über zwei Schnitte (top-k, Kontext/`in_top_n`).
- `eval/test_in_corpus_quality.py` (neu): Halluzinationsrate (Gate = 0 %) über `in_corpus` + `adversarial` ohne erwartete Verweigerung, False-Suppression (Gate ≤ 15 %) nur über `in_corpus`, Adversarial-Refusal separat (n=2, kein Gate), Recall/Precision/MRR ohne Gate. CSV und `run.json` analog zum Refusal-Test.
- `Docs/04_ADR-009_Eval-Strategie.md` und `Ops/09_CI-Runbook.md` nachgeführt.

---

## 3 — Nutzer

> bewerte dieses Feedback:
>
> [xhigh-Code-Review, 15 Befunde gegen `feat/T-56-in-corpus-eval` (1 Commit, 8 Dateien) gepostet, u. a.: leerer Halluzinations-Pool besteht das 0-%-Gate trivial; unbewertete Fragen verwässern das Gate; Gate benutzt `==` statt `<=`; abgeschnittene Generierungen zählen als False-Suppression; `expected_refusal` auf einer Union ohne das Attribut gelesen; CSV fehlen Felder für T-57; `run.json` fehlen die im Bericht zitierten Aggregate; Login-Fixture und Admin-Konstanten dupliziert; `in_corpus_out_dir` dupliziert `eval_out_dir`; verschachteltes Output-Verzeichnis umgeht `compare.py`s Scan; Runbook behauptet Overrides in `run.json`, die nicht geschrieben werden; Befunde-Tabelle nennt 13 adversarial, nur 11 bewertet; `_load()` parst das Dataset bei jedem Aufruf neu; `retrieval_metrics` durchläuft `chunks` dreimal; ein Guard filtert unerreichbare Indizes.]

### Claude

Jeden Befund einzeln gegen den tatsächlichen Code verifiziert statt die Titel zu glauben: `mypy eval` separat laufen lassen (bestätigte den `union-attr`-Fehler exakt auf der genannten Zeile), `tests/test_gold_eval_dataset.py` gegen die behauptete Schema-Lücke gelesen, CSV-Spalten der beiden Testdateien diff't, `run.json`/Befunde-Dokument gegen die tatsächlich geschriebenen Felder abgeglichen. Ergebnis: 12 von 15 Befunden bestätigt (davon 7 klare Korrektheits-/Dokumentationsfehler, 3 legitime Duplikations-/Architekturschulden), 2 berechtigte, aber diskutable Designfragen (Gate-Operator, Umgang mit `generation_truncated`), 3 Geschmacksfragen ohne Handlungsbedarf (`_load()`-Caching, dreifacher Chunk-Durchlauf, „unreachable" Guard als bewusste Verteidigung im Fail-closed-Stil).

---

## 4 — Nutzer

> Ja, setz die Fixes um

### Claude

Umgesetzt: `<=` statt `==` beim Halluzinations-Gate; Entkopplung der Halluzinationsprüfung von `expected_source` (verhindert die Verwässerung durch unbewertete Fragen); `isinstance(q, AdversarialQuestion)` direkt in der Bedingung statt einer zwischengespeicherten Bool-Variable (mypy verengt nur bei einer isinstance-Prüfung am Zugriffsort); `retrieval_score`/`self_check_ran`/`self_check_verdict` in die CSV aufgenommen; Recall/Precision/MRR-Aggregate je Kategorie in `run.json`; `overrides`-Block in `run.json` ergänzt (Runbook-Zusage stimmt wieder); `_ADMIN`/`EMAIL`/`PASSWORD` und die `token`-Fixture nach `eval/conftest.py` verschoben, geteilter `_out_dir`-Helper für `eval_out_dir` und `in_corpus_out_dir`; `generation_truncated` als bewusste Entscheidung im Modul-Docstring begründet statt stillschweigend gezählt; Befunde-Dokument mit korrekter Fragenzahl (11 statt 13) neu erzeugt.

---

## 5 — Nutzer

> squash, push und dann den PR erstellen

### Claude

Beide Commits (Feature + Review-Fixes) per `git reset --soft origin/main` zu einem Commit zusammengefasst (`8f2fd4c`, Konvention: ein Commit für den Review). Branch gepusht, [PR #133](https://github.com/tsorer/LearnFlow/pull/133) erstellt (Titel mit Branchname-Präfix), Body mit Zusammenfassung, erstem Messlauf (Halluzinationsrate 0 %, False-Suppression 33–38 % über dem 15-%-Startwert — erwarteter Befund für T-57, nicht aufgeweicht) und den behobenen Review-Punkten.

---

## 6 — Nutzer

> bewerte das Feedback auf github

### Claude

`gh pr view`/`gh api` gegen PR #133 abgefragt: Approval von `luenlestra` mit einem nicht-blockierenden Inline-Hinweis auf `test_in_corpus_quality.py:279` (`body.get("debug") or {}` lässt einen fehlenden Debug-Block still auf leere Metriken fallen). Gegen `app/routers/documents.py`/`app/routers/query.py` verifiziert: `GET /api/documents` (die Präcondition) verlangt keine Admin-Rolle, `debug` ist aber nur für Admins gefüllt — ein falsch konfiguriertes `E2E_ADMIN_EMAIL`/`-PASSWORD` würde damit unbemerkt jede Recall/Precision/MRR-Messung auf 0.0 fallen lassen statt laut abzubrechen. Befund als real eingestuft (nicht als Nitpick abgetan), Fix übernommen (`assert body.get("debug") is not None` direkt nach `suppressed`), als eigener Commit `8222a12` gepusht (Konvention: Korrekturen während des Reviews einzeln, nicht in den Feature-Commit amended), im Review-Thread geantwortet und den Thread über die GraphQL-API aufgelöst.

---

## 7 — Nutzer

> auf github ist alles grün, das reicht. Poste noch einen Kommentar, das die Korrekturen umgesetzt wurden

### Claude

Kommentar auf PR #133 gepostet: Hinweis auf den fixierten `debug`-Guard (`8222a12`) und grüne CI.

---

*(Export erstellt am 2026-09-20.)*
