# Chatverlauf — T-51 + T-61 Fortschritts-Zeitstempel statt Übernahme-Zeitpunkt, PR #134

**Datum:** 2026-09-11 – 2026-09-16 (Export am 2026-09-20)
**Branch:** `feat/T-51-fortschritts-zeitstempel`, von `origin/main` abgezweigt. Squash-Merge in `main` (Merge-Commit `8de1c9f`, 2026-09-15).
**Gegenstand:** Issue [#106](https://github.com/tsorer/LearnFlow/issues/106) „[T-51] Reaper: Fortschritts-Zeitstempel statt Übernahme-Zeitpunkt" (US-04) zusammen mit [#132](https://github.com/tsorer/LearnFlow/issues/132) (T-61, Obergrenze für `processing_timeout_seconds`) — von der Planung bis zum gemergten PR, plus die Auswertung des GitHub-Feedbacks auf einem parallelen PR (#135, T-58).
**Ergebnis:** [PR #134](https://github.com/tsorer/LearnFlow/pull/134), gemergt. Migration `0020` (`documents.index_progress_at`, `processing_stall_seconds`, Obergrenze `[120, 999999]` für beide Sekunden-Keys), `worker/main.py` neu strukturiert (`note_progress`, `reap_stuck_documents` auf `index_progress_at` statt `pgqueuer.heartbeat`), Nachtrag in ADR-006. Review-Runde 1 (drei Findings, alle übernommen), Review-Runde 2 (Nebenläufigkeits-Finding, `asyncio.to_thread`-Fix, approved), Review-Runde 3 (approved mit einem optionalen ADR-Hinweis — **dieser Punkt ist beim Export noch offen**, siehe Abschnitt „Offen" am Ende).

> Rekonstruktion aus dem exportierten Sitzungs-Transkript. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen. Lokale Slash-Commands (`/model`) sind ausgelassen.

---

## 1 — Nutzer

> Erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/106

### Claude

Issue #106 gelesen, dazu #69 (T-43, Ursprung des Reapers) und den vollständigen Review-Verlauf auf PR #104 — dort hatte der Reviewer bereits die Heartbeat-Semantik seziert und Folge-Issues #106 (T-51) und #107 (T-52, gemergt als PR #118) benannt. Issue #132 (T-61, Obergrenze für `processing_timeout_seconds`) zusätzlich gelesen, weil es dieselbe CHECK-Constraint berührt.

Zwei parallele `Explore`-Agents recherchierten Reaper-Implementierung/Worker-Struktur bzw. Migrationskonventionen/ADR-006, während ein `Plan`-Agent den Entwurf gegenprüfte. Dabei verifiziert, nicht nur übernommen: die pgqueuer-`Heartbeat`-Klasse direkt im Container gelesen (bestätigt `retry_timer=timedelta(0)` schaltet den Sender aus), Spec-/Test-Berührungspunkte (`openapi.yaml`, `schema.d.ts`, `admin.py`-Key-Listen) durchsucht, ein dritter unabhängiger Schreibpfad auf `index_version` (`apply_embedding_config.py`) gefunden.

Eine offene Designfrage per `AskUserQuestion` geklärt (Ablage des Zeitstempels: eigene Spalte auf `documents`, nicht eine Zeile in `pgqueuer`). Der Plan-Agent fand mehrere substanzielle Punkte, die einzeln gegen den Code verifiziert und übernommen wurden, bevor der Plan final geschrieben wurde. Entscheidung, T-61 mit ins selbe PR zu ziehen: beide Tickets bauen dieselbe CHECK-Constraint (`ck_config_confidence_threshold_value`) neu — getrennt wäre der Preis ein Merge-Konflikt, der zu einem fail-open-Arm führen kann (das Muster, das schon in #104 als reale Gefahr belegt war).

Nach `ExitPlanMode` und Freigabe: Branch `feat/T-51-fortschritts-zeitstempel` von `origin/main`. **Schritt 0** des Plans — Annahmen am laufenden Stack messen statt schätzen:

| Grösse | Wert |
|---|---|
| m₁ (Parsing, ~576 Seiten/2100 Chunks, EU-AI-Act-Dokument auf 10 MiB skaliert) | 29,33 s |
| m₂ (Chunking) | 2,85 s |
| m₃ (`store_chunks` + `mark_available`, 1850 Chunks, echte DB) | 4,39 s |
| Embedding-Batch-Retry (rechenbar, harter Boden) | ~120 s |
| **stall = max(120, 29.33, 2.85, 4.39) × 2** | **240 s → aufgerundet 300 s** |
| Overflow `make_interval(secs=>$1)` (echtes Postgres) | ~212,66 Mrd. s (~6739 Jahre) |
| Overflow `make_interval(secs=>$1) * 2` | ~106,33 Mrd. s (~3369 Jahre) |

Daraus die Obergrenze für T-61: **[120, 999999]** für beide Sekunden-Keys — die Obergrenze verwirft exakt den in #132 belegten Wert `999999999`.

Umsetzung in der Reihenfolge des Plans:
1. **Spec zuerst** (ADR-010): `processing_stall_seconds` in `openapi.yaml`, `make generate-api` im Node-Container, minimaler Diff in `schema.d.ts`.
2. **Migration `0020`**: `documents.index_progress_at` (kein `onupdate`, wie `index_version`/`index_attempts` aus `0017`), neuer Key `processing_stall_seconds`, CHECK-Erweiterung `[120, 999999]` für beide Sekunden-Keys. Gegen die echte DB verifiziert: `upgrade` → Boundary-Werte akzeptiert/abgelehnt exakt wie gemessen → `downgrade 0019` → `upgrade`, dazu der Nachweis, dass `ADD COLUMN ... DEFAULT now()` über `atthasmissing` den Fast-Path nimmt, keinen Table-Rewrite auslöst.
3. **Modell**: `index_progress_at`-Spalte, Pin-Test `onupdate is None` erweitert.
4. **`worker/main.py`**: `process_document` bekommt `note_run_progress` (schreibt unter derselben `index_version`-Bedingung wie jeder andere Write), `prepare_chunks` ruft es nach Parsing und nach Chunking auf, `embed_texts` je Batch. `reap_stuck_documents` vergleicht nur noch `index_progress_at` — die `NOT EXISTS`-Subquery gegen `pgqueuer` samt JSON-Cast-Guard (Review auf #104) entfällt ersatzlos. `read_reaper_config` um `processing_stall_seconds` erweitert, `reaper_interval` folgt jetzt `stall_seconds` statt `timeout_seconds`.
5. **QA**: `ruff`, `mypy`, vollständiger Unit- und e2e-Testlauf (100 %, Exit 0) — der letzte Durchlauf lief im Hintergrund; ein `ScheduleWakeup` holte das Ergebnis nach und bestätigte grün.
6. **Manuelle Verifikation** gegen den laufenden Dev-Stack: echter Upload lief sauber durch, ein künstlich auf `processing` mit alter Uhr gesetztes Dokument wurde vom Reaper erkannt, requeued, erfolgreich neu indexiert; Testdaten und Config zurückgesetzt.
7. Docs aktualisiert (ADR-006-Nachtrag „Woher die 300 s kommen", ERD, RAG-Pipeline-Referenz, Pilotstart-Checkliste).

Commit `18a571c`, **nicht gepusht** — Push/PR macht Claude nur auf explizite Ansage (Memory-Konvention).

---

## 2 — Nutzer

> bewerte das Feedback:
>
> Code-Review6 Ergebnisse
> 0020_index_progress_at.py
> - Bestätigt: Migration tightens CHECK without clamping old data
> - Plausibel: T-51 and T-61 bundled into one irreversible migration
>
> main.py
> - Plausibel: Per-phase stall is stricter than old total timeout
> - Plausibel: Default reaper poll interval drops 4x, unremarked
> - Plausibel: Seconds bounds duplicated with no cross-check
> - Plausibel: max_attempts parsing duplicates _clamped_seconds shape
>
> [vollständiger Review-Text mit Einordnung der sechs Findings]

### Claude

Jeden der sechs Punkte gegen den tatsächlichen Code geprüft, nicht nur bewertet:

- **Finding 1 (Migration ohne Datenbereinigung) — bestätigt und reproduziert:** `alembic downgrade 0019`, `processing_timeout_seconds` per `psql` auf einen unter der alten Regel gültigen Wert gesetzt (`900000000`), `alembic upgrade head` bricht mit `CheckViolationError` ab. **Gefixt:** Migration klammert bestehende Werte jetzt vor `ALTER TABLE ADD CONSTRAINT`, `numeric`-Cast gegen Overflow bei astronomischen Altwerten. Alle drei Fälle (zu klein, zu gross, astronomisch) erneut gegen echte DB verifiziert.
- **Finding 4 (Sekunden-Grenzen dreifach dupliziert)** — bestätigt, Duplikation selbst ist etabliertes Repo-Muster, aber ohne Cross-Check. Zwei neue Tests in `test_config_constraint_migration.py` (`0020`s Regex/Keys gegen `admin.py`, `MIN_`/`MAX_PROCESSING_SECONDS` gegen dieselbe Regex).
- **Finding 5 (`max_attempts`-Parsing dupliziert `_clamped_seconds`)** — `_clamped_seconds` zu `_clamped_int` verallgemeinert (`maximum=None` für den bewusst unbegrenzten Fall).
- **Finding 2 (Stall pro Phase strenger, `chunk_size`)** — real, aber eng (nur per `psql`, kein Admin-API-Pfad): als bekannte Restlücke in ADR-006-Nachtrag und Docstring dokumentiert statt strukturell gefixt.
- **Finding 3 (Poll-Intervall 300s→75s „unremarked")** — Fakt stimmt, war aber im ADR-Nachtrag bereits explizit benannt; Framing „unremarked" zurückgewiesen, Code-Kommentar trotzdem um den Vorher/Nachher-Vergleich ergänzt.
- **Finding 6 (T-51/T-61 in einer nicht separat revertierbaren Migration)** — Fakt stimmt, war aber bewusste, im Plan begründete Entscheidung (gemeinsame CHECK-Constraint, Merge-Konflikt-Risiko sonst); kein Code-Fix.

Fixes gegen die echte DB verifiziert (Clamp nach oben auf 999999, nach unten auf 120, astronomischer Wert ohne Overflow), volle QA (`ruff`, `mypy`, `pytest tests e2e -q`, 100 %) grün. Commit `d2fad7d` — zweiter Commit auf demselben Branch, laut Memory-Konvention bleiben Korrekturen vor dem PR einzeln statt sofort gesquasht.

---

## 3 — Nutzer

> ja, bitte squashen und pushen

### Claude

Beide Commits (`18a571c`, `d2fad7d`) per `git reset --soft main` + Neu-Commit zu einem zusammengeführt (`2f7ddde`), Commit-Message kombiniert beide Begründungen. Gepusht.

---

## 4 — Nutzer

> ja, PR erstellen

### Claude

[PR #134](https://github.com/tsorer/LearnFlow/pull/134) erstellt, Titel mit Branchnamen präfixt, schliesst #106 und #132, Basis `main`.

---

## 5 — Nutzer

> bewerte das Feedback auf github. Hatten wir nicht schon mal festgestellt, dass nicht mehrere Uploads der gleichen Datei praktisch unmöglich sind? Was wären mögliche Seiteneffekte der vorgeschlagenen Lösung?

### Claude

Zunächst das falsche PR geprüft (#135, T-58-Restyling, aktueller Branch zu dem Zeitpunkt) — dort nur ein WCAG-Kontrast-Review ohne Bezug zu Uploads gefunden. Dann PR #134 selbst: **Changes Requested** von `luenlestra`, ein Inline-Finding auf `worker/main.py:274`.

Das Finding technisch nachvollzogen: `asyncpg.create_pool(..., max_size=5)` plus pgqueuer dispatcht mehrere Jobs auf **eine** Event-Loop; `parse_document`/`chunk_blocks` liefen synchron ohne eigenen Yield-Punkt. Szenario des Reviewers (5 × 10-MiB-Dokumente gleichzeitig) durchgerechnet und bestätigt: unter der alten 2700-s-Frist folgenlos, unter den neuen 300 s nicht mehr.

Zur Nutzerfrage: ja, „mehrere Uploads **derselben** Datei" hatten wir in #104 als praktisch unmöglich festgestellt (Unique-Index `(area, filename)`, T-15 — ein Re-Upload ersetzt die Job-Zeile des vorigen). Das beantwortet dieses Finding aber nicht, weil der Reviewer **5 verschiedene** Dokumente beschreibt, keine Duplikate — eine normale Situation beim Bulk-Upload eines Korpus.

Seitenanalyse von `asyncio.to_thread` als Fix: kein Durchsatzgewinn (GIL serialisiert weiterhin, `pypdf`/`python-docx` sind reines Python), aber die Loop bleibt für andere Coroutinen (`note_progress`, `reaper_loop`) offen. Risiken benannt: Thread-Sicherheit der Libraries nur durch Smoke-Test verifizierbar, mögliche Test-Flakiness durch echte Thread-Nebenläufigkeit. Empfehlung: übernehmen, mit Vorab-Smoke-Test.

---

## 6 — Nutzer

> ja, umsetzen. Du kannst zum branch t-51 wechseln

### Claude

Auf `feat/T-51-fortschritts-zeitstempel` gewechselt, `parse_document`/`chunk_blocks` in `prepare_chunks` auf `asyncio.to_thread` umgestellt, Docstring um die Begründung erweitert.

Zwei selbst geschriebene Smoke-Tests gegen echte Nebenläufigkeit (nicht nur die vorhandenen Unit-Tests) im Container gefahren:
- **Cross-Contamination:** 5 verschiedene Dokumente (3 reale Korpus-PDFs, `sample.docx`, `hyphenated.pdf`) 3× parallel über `asyncio.gather` geparst — Chunk-Anzahl und SHA-256 stimmen in jeder Runde exakt mit dem sequenziellen Baseline überein.
- **Loop-Reaktionsfähigkeit:** Heartbeat-Coroutine (200 ms-Takt) neben 6 gleichzeitigen Parses — grösste Taktlücke 0,91 s, gegen einen an das 300-s-Stall-Budget gekoppelten Bar (10×-Sicherheitsmarge → 30 s) klar bestanden. Durchsatz selbst sank leicht (0,91×), wie erwartet.

Danach fiel auf, dass die DB aus der vorherigen Session noch auf Revision `0019` stand (Rest der Migrationstests) und das Login-Rate-Limit ausgeschöpft war — beides Altlasten, kein neuer Bug: `alembic upgrade head`, `docker restart src-api-1`, danach 100 % grün. Commit `3ca1189`, gepusht, Antwort mit den Testergebnissen auf PR #134 gepostet.

---

## 7 — Nutzer

> bewerte das Feedback auf github

### Claude

Re-Review von `luenlestra` gelesen: **approved**, Change Request erledigt. Geprüft: Thread-Sicherheit von `tiktoken` (`_lock` in `get_encoding`, tiktoken 0.14.0) konkret verifiziert, eigene Nachrechnung des Restrisikos bestätigt (5× 10-MiB gleichzeitig, GIL-serialisiert ≈ 160 s bis zum ersten Progress-Write, ≈ 2× Reserve gegen 300 s).

Einziger verbleibender Punkt, unblockierend: die Erkenntnis „300 s hält unter Last nur, weil Parsing/Chunking in Threads laufen" stand bisher nur im Docstring, nicht im ADR — Risiko, dass `to_thread` später als vermeintlich unnötige Komplexität entfernt wird. Bewertet als berechtigt und passend zum bestehenden Stil des ADR-Nachtrags. ADR-006 um einen Absatz ergänzt (Rechnung mit den ~160 s / 2× Reserve, explizit als Voraussetzung markiert).

**Beim Commit-Versuch stellte sich heraus, dass das Arbeitsverzeichnis inzwischen auf einem anderen Branch stand** (`docs/christoph-architecture-diagrams`, vermutlich von aussen gewechselt) — der ADR-Commit landete dort zuerst, wurde bemerkt (Commit-Hash und `git status` nach dem fehlgeschlagenen Push zeigten den falschen Branch), per `git reset --hard HEAD~1` von dort entfernt (unproblematisch: letzter Commit, nicht gepusht). Beim Versuch, auf `feat/T-51-fortschritts-zeitstempel` zurückzuwechseln, stellte sich heraus: **PR #134 war bereits gemerged** (2026-09-15, Merge-Commit `8de1c9f`), der Branch serverseitig gelöscht. Der ADR-Nachtrag ist damit kein PR-Zusatz mehr, sondern ein eigenständiger Follow-up auf `main`. Beim Versuch, dafür `main` zu aktualisieren (`git checkout main && git pull`), hat der Nutzer das Tool abgebrochen — **die ADR-Ergänzung ist seither nicht committet.**

---

## 8 — Nutzer

> [Request interrupted by user for tool use]

*(Keine inhaltliche Nachricht — die Unterbrechung des `git checkout main`-Aufrufs aus Turn 7. Kein weiterer Auftrag in dieser Session bis Turn 9, vier Tage später.)*

### Claude

„No response requested."

---

## 9 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Bestehende Dateien in `Frank/Prompts/` als Formatvorlage gelesen. Sitzungstranskript über `mcp__ccd_session_mgmt__export_transcript` exportiert (zuverlässiger als eine Rekonstruktion aus dem eigenen, teils komprimierten Kontext), als JSONL entpackt, mit einem kleinen Node-Skript auf die echten Nutzer-Prompts und Assistant-Texte reduziert (574 Einträge, davon 14 echte Nutzer-Turns), gegen den eigenen Kenntnisstand abgeglichen — deckte dabei den vollständigen Plan-Mode-Teil auf (Schritt 0 bis zum ersten Commit), der im laufenden Kontext bereits zusammengefasst/nicht mehr sichtbar war. Diese Datei geschrieben.

---

## Offen

- **ADR-006-Ergänzung** (asyncio.to_thread als Voraussetzung der 300-s-Frist, Review-Kommentar aus Turn 7) ist lokal **nicht mehr vorhanden** — der Commit wurde vom falschen Branch per `git reset --hard` entfernt und nie neu geschrieben. Muss auf einem neuen Branch von `main` nachgezogen werden (kleiner, eigenständiger Doku-PR, da #134 bereits gemerged ist).
- Reviewer-Hinweis dazu war ausdrücklich **optional/nicht blockierend** — PR #134 ist bereits gemerged und braucht diesen Nachtrag nicht mehr zwingend, ist aber weiterhin sinnvoll, um zu verhindern, dass `to_thread` später als überflüssig entfernt wird.
