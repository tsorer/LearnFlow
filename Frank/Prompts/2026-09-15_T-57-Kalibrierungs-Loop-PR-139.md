# Chatverlauf — Kalibrierungs-Loop (T-57, PR #139)

**Datum:** 2026-09-15 bis 2026-09-20
**Branch:** `feat/T-57-kalibrierungs-loop`
**Gegenstand:** Umsetzungsplan für T-57 (Issue [#125](https://github.com/tsorer/LearnFlow/issues/125)), vollständige Implementierung des Kalibrierungs-Loops aus ADR-009 (Snapshot, Schicht A1/A2/B/C, Bericht), ein echter Lauf gegen den Dev-Stack, zwei Runden Review-Nachbesserung (erste Selbstprüfung, zwei GitHub-Reviews von `luenlestra`) und ein Rebase auf `main`.
**Ergebnis:** [PR #139](https://github.com/tsorer/LearnFlow/pull/139), von `luenlestra` **approved**, CI grün, mergefähig. `Docs/10_Kalibrierungsbericht.md` dokumentiert einen durchgeführten Lauf: das gefundene Set erfüllt die Constraints auf dem Train-Split, die Holdout-Bestätigung verfehlt das Out-of-Corpus-Refusal-Gate knapp und liegt über dem bestehenden 15-%-CI-Gate — kein „Accepted"-Set, ADR-007/008/009 entsprechend nachgeführt.

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen — nicht jeder Zwischenschritt (Lint-/Typecheck-/Testläufe, Warten auf Hintergrundprozesse) ist einzeln aufgeführt.

---

## 1 — Nutzer

> Erstelle einen Umsetzungplan für T-57 (https://github.com/tsorer/LearnFlow/issues/125). T-55 und T-56 sind mittlerweile umgesetzt, die Kommentare sind daher eventuell veraltet.

### Claude

Issue #125 vollständig gelesen (inkl. des ausführlichen Klärungskommentars vom 2026-09-10), gegen den aktuellen Code nachgeprüft — T-55/T-56 tatsächlich gemergt, die Entscheidungen im Kommentar weiterhin gültig, der öffentliche `fetch_rows()`-Seam (AC 2) aber noch nicht gebaut. Drei Explore-Agents parallel gestartet (ADR-007/008/009, `eval/`-Verzeichnis, Retrieval-/Confidence-Code), danach gezielt `retrieval.py`, `confidence.py`, `config.py`, `query.py`, `eval/metrics.py`, `eval/gold_dataset.py`, `eval/conftest.py`, `eval/profiles.py` und `eval/test_in_corpus_quality.py` gelesen, um die Pipeline-Schichtung (Snapshot → Schicht A1/A2 offline → Schicht B echte Läufe → Schicht C offline → Bericht) exakt zu verstehen.

Plan-Modus genutzt: Architektur mit neuen Modulen `eval/calibrate_dataset.py`, `eval/calibrate_snapshot.py`, `eval/calibrate_grid.py`, `eval/calibrate_run.py`, `eval/calibrate_report.py`, `eval/calibrate.py` entworfen, jeweils mit Begründung, welche bestehenden Funktionen wiederverwendet werden. Plan zunächst mit einer 3-PR-Aufteilung (analog T-55) vorgeschlagen.

---

## 2 — Nutzer (Ablehnung des ersten Plans)

> t-55 war ein Versuch. Setze alles mit einem PR um.

### Claude

Plan auf einen einzigen Branch/PR umgestellt (Schritte 1–8 bleiben die Commit-Reihenfolge, nur ohne Zwischen-Reviews), erneut zur Freigabe vorgelegt — genehmigt.

Branch `feat/T-57-kalibrierungs-loop` von `origin/main` erstellt. Umsetzung in dieser Reihenfolge:

1. **Seam:** `_fetch()` in `app/services/retrieval.py` → öffentliches `fetch_rows()`, `retrieve()`/`sample_chunks()` darauf umgestellt. Regressionstest in `tests/test_retrieval.py`.
2. **Split:** `eval/calibrate_dataset.py` — stratifizierter Train/Holdout-Split nach `(corpus, category)`, fester Seed 57, `HOLDOUT_IDS` als committetes Literal (berechnet und gegen `_compute_holdout_ids()` verifiziert in `tests/test_calibrate_dataset.py`).
3. **Snapshot:** `eval/calibrate_snapshot.py` — Embedding + `fetch_rows()` für alle 80 Fragen bei `top_k=100`, ohne Chunk-Inhalt, mit Indexstand-Hash (`compute_index_hash`/`verify_index_hash`/`SnapshotStaleError`).
4. **Schicht A1/A2:** `eval/calibrate_grid.py` — k-fold-CV über die Ranking-Parameter, Vor-Generierungs-Gates offline über `passes_retrieval_gate()`/`compute_retrieval_confidence()`.
5. **Schicht B:** `eval/calibrate_run.py` — echte Läufe dedupliziert nach `(question_id, context)`, erzwungener Self-Check für jede Antwort.
6. **Schicht C + Bericht:** `eval/calibrate_report.py` — Bandschwellen-Arithmetik, Constraint-Auswahl, Holdout-Bestätigung, Markdown-Bericht.
7. **CLI:** `eval/calibrate.py` + `make calibrate`-Target (Docs/ ist nicht in den api-Container gemountet, also schreibt das Skript nach `eval/out/calibrate/latest-report.md`, das Makefile kopiert host-seitig nach `Docs/`).

Nach jedem Modul lint/typecheck/test im laufenden Dev-Stack (`docker exec src-api-1 ...`) geprüft. Pipeline mit stark verkleinertem Gitter end-to-end smoke-getestet, bevor der echte, volle Lauf gegen den Dev-Stack gefahren wurde (reale OpenAI-Aufrufe). Ergebnis committet, gesquasht auf einen Commit, gepusht, [PR #139](https://github.com/tsorer/LearnFlow/pull/139) eröffnet.

---

## 3 — Nutzer (Review-Feedback, erste Runde)

> bewerte vorher noch dieses Feedback
>
> [zehn Befunde eines externen Reviews: A1-Ranking ignoriert Precision und wählt strukturell den grössten `context_top_n`-Gitterwert; der entartete Punkt kann Schicht C strukturell nie erreichen; das bestehende 15-%-False-Suppression-CI-Gate fehlt im Bericht; `make calibrate` kopiert den „kein Kandidat"-Bericht nicht; der im Docstring versprochene `SNAPSHOT_TOP_K`-Guard fehlt; ADR-008-Markdown-Bug (fehlende Leerzeile vor `---`); Gate-Konstanten dreifach dupliziert; Dataset wird pro Kandidat neu geparst; Seam-Test beweist nicht, was er behauptet; diverser Kleinkram — plus die methodische Beobachtung, dass k-fold-CV ohne Fit-Schritt keine Generalisierungsschätzung liefert]

### Claude

Alle zehn Punkte einzeln gegen den Code verifiziert (nicht blind übernommen) — alle bestätigt, inklusive des selbst nicht gefundenen methodischen Punkts zur wirkungslosen k-fold-CV. Bewertung mit Einschätzung „bestätigt/schwerwiegend", „bestätigt/billig zu fixen" und „Ermessensfrage" gegliedert, Empfehlung ausgesprochen: 1, 2, 5, 8 beheben und **neu laufen lassen** (verändern die Auswahl selbst), Rest unabhängig fixbar.

---

## 4 — Nutzer

> Ja, setze das um

### Claude

Umgesetzt:

- **A1-Ranking:** F1 aus Recall und Precision statt Recall allein (`_f1()`), plus `f1_std` (Streuung über die Folds) als das, was k-fold-CV ohne Fit-Schritt tatsächlich zusätzlich liefert.
- **Entarteter Punkt:** `worst_case_candidate()` neu in `calibrate_grid.py`, zieht den schlechtesten Kandidaten aus der vollständigen `rank_combined_candidates()`-Rangliste statt aus der für Schicht B vorselektierten Top-N.
- **`PreGenerationOutcome`** um ein `context`-Feld erweitert (spart einen doppelten `context_for()`-Aufruf in `calibrate.py`).
- **`eval/gates.py`** neu: die drei produktiven Reliability-Gates (Halluzination, False-Suppression, Refusal) an einer Stelle, `eval/test_in_corpus_quality.py` und `eval/test_out_of_corpus_refusal.py` importieren jetzt von dort.
- **`calibrate_report.py`** grösstenteils neu geschrieben: `PreGenState` gruppiert Gate/Konfidenz/Kontext nach `(a1, a2)` statt pro vollem Zehn-Werte-Kandidaten neu zu rechnen (~1000 Kandidaten im Standardgitter); Dataset-Loader einmal geladen statt pro Kandidat; False-Suppression-CI-Gate im Bericht ausgewiesen.
- **Makefile:** `cp` läuft jetzt auch, wenn `eval.calibrate` mit Exit-Code 1 endet (kein Kandidat erreicht die Constraints).
- **`SNAPSHOT_TOP_K`-Assert** ergänzt, **ADR-008-Leerzeile** korrigiert.
- **Seam-Test** auf einen echten Spy auf `fetch_rows()` umgestellt statt nur struktureller Vergleich.

Smoke-Test erneut gegen den Dev-Stack gefahren, dann der volle, echte Lauf (reale OpenAI-Aufrufe, Snapshot → Schicht A → Schicht B → Holdout). Ergebnis: Holdout-Refusal-Rate 85,7 % (Gate ≥ 90 %) — derselbe methodische Befund wie vor dem Fix, jetzt aber ohne das Ranking-Artefakt (`context_top_n` nicht mehr trivial das Gitter-Maximum). Bericht und ADR-007/008/009 aktualisiert, gesquasht, gepusht.

---

## 5 — Nutzer

> bewerte das Feedback auf github

### Claude

Reviews/Kommentare von PR #139 via `gh pr view --json reviews` geholt: eine Review von `luenlestra`, Teil A (5 Code-Befunde) und Teil B (Wechselwirkung mit dem parallelen T-62-Branch, #136). Alle fünf Code-Befunde einzeln gegen den Code auf dem PR-Branch nachgeprüft (ohne das lokale Arbeitsverzeichnis anzufassen, dort war zwischenzeitlich ein anderer Branch mit fremden uncommitteten Änderungen ausgecheckt — bewusst unberührt gelassen, stattdessen per `git show origin/<branch>:<pfad>` gelesen):

1. Makefile `-docker exec` schluckt jeden Fehler, nicht nur den beabsichtigten Exit-Code 1.
2. `_run_schicht_b` schreibt Ergebnisse erst am Ende — ein Absturz mittendrin verwirft bereits bezahlte Läufe.
3. Halluzinations-Pool zählt ausgelieferte Out-of-Corpus-Antworten mit (verwässert den Nenner).
4. „gesamtes A1×A2-Gitter" stimmt nicht — `worst_case_candidate()` sieht nur die Top-5-A1-Kandidaten, nicht die vollen 100.
5. Test-Assertion `train_ids | holdout_ids == train_ids.union(holdout_ids)` ist tautologisch.

Alle fünf bestätigt. Teil B (unterschiedliche Holdouts zwischen T-57 und T-62, Kalibrierung vor T-62s Korrektur der Satzzerlegung in `check_citations`) als berechtigt, aber als Team-Koordinationsfrage eingeordnet — nicht einseitig in diesem PR zu entscheiden.

---

## 6 — Nutzer

> mach ein rebase auf den main und setze dann die Punkte um

### Claude

Working Directory geprüft (zwischenzeitlich wieder auf `main`, sauber), Branch ausgecheckt, `git rebase origin/main` — konfliktfrei. Alle fünf Befunde behoben:

1. Makefile: `latest-report.md` wird vor jedem Lauf gelöscht, nur `rc ∈ {0,1}` toleriert, sonst `exit $rc`.
2. `_run_schicht_b`: `write_runs()` im `finally`, `out_dir` als Parameter (auch für den Holdout-Aufruf).
3. `_aggregate()`: Halluzinations-Pool filtert jetzt auf `in_corpus`/`adversarial`.
4. `calibrate.py` ruft `rank_combined_candidates()` zusätzlich mit `a1_grid()` (volles Gitter, 100 statt 5 Kandidaten) für den entarteten Referenzpunkt auf — offline, kein LLM-Aufruf.
5. Test vergleicht jetzt gegen `load_adversarial_questions()`/`load_out_of_corpus_questions()`.

Da 3 und 4 tatsächliche Zahlen ändern, erneut voll gelaufen (entarteter Punkt jetzt 23,3 %/46,7 % statt 16,7 %/20,0 %, deutlich extremer da wirklich das ganze Gitter). `Docs/10_Kalibrierungsbericht.md` und ADR-007/008/009 mit den neuen Zahlen aktualisiert, ADR-008 zusätzlich um einen Nachtrag zur T-62-Kollision ergänzt. Commit, Force-Push (`--force-with-lease`, nötig nach dem Rebase), zusammenfassender Kommentar auf dem PR gepostet.

---

## 7 — Nutzer

> bewerte den neuesten Kommentar auf github

### Claude

Neueste Review von `luenlestra` geholt: **APPROVED**, alle fünf Befunde einzeln gegen Commit `bb137ee` nachgeprüft und bestätigt. Drei nicht-blockierende Anmerkungen (kein automatisches Fortsetzen über `load_runs()`; `docker exec` kann auch bei nicht laufendem Container `rc=1` liefern, scheitert dann aber laut am `cp`; der volle Gitter-Scan kostet ~20× mehr Offline-Rechenzeit, bleibt aber im Sekundenbereich). Zwei neue, ebenfalls nicht-blockierende Punkte:

- Die beobachtete Lauf-zu-Lauf-Streuung (26,7 % → 33,3 % bei identischem Set, `TEMPERATURE=0.0`) steht nur in der Commit-Message, nicht im Bericht selbst.
- Konkrete Zahlen aus T-62s R04-Lauf: `self_check_band_high=0.6` würde beim Produktivmodell 11 von 16 Stufe-3-Läufen streichen, darunter den einzigen echten Treffer — mit der vom Reviewer selbst genannten Einschränkung, dass das unter anderen Schwellen gemessen ist (Indiz, keine Simulation).

Beide Punkte als berechtigt und günstig einzubauen bewertet, PR bereits mergefähig eingeordnet.

---

## 8 — Nutzer

> Ja, bau beide Ergänzungen ein

### Claude

`Docs/10_Kalibrierungsbericht.md`: „Stichprobe von 1"-Hinweis um den konkreten Beleg ergänzt (26,7 % → 33,3 %, plus der unabhängige T-62-Beleg aus `R00_Baseline.md`) — als Hand-Ergänzung zum generierten Bericht, weil es ein retrospektiver Vergleich zweier konkreter Läufe ist, den der Generator nicht automatisch herleiten kann. `Docs/04_ADR-008_Konfidenz-Pipeline.md`: T-62-Kollisionsabsatz um die R04-Zahlen zum Self-Check-Band ergänzt, mit derselben Einschränkung, die der Reviewer genannt hatte. Reiner Doku-Commit, kein neuer Lauf nötig. Commit, Push (Fast-Forward, kein Force nötig), Kommentar auf dem PR gepostet.

---

## 9 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Bestehende Exporte in `Frank/Prompts/` als Vorlage gelesen (zuletzt `2026-09-08_T-54-Review-PR-116.md`) und dieses Dokument nach der dort etablierten Konvention erstellt.
