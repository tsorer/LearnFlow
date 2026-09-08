# Chatverlauf — T-21 Quellenlink: Originaldokument-Viewer (PR #112)

**Datum:** 2026-09-02 (Umsetzung, Review, Fixes); Export dieses Dokuments am 2026-09-08.
**Branch:** `feat/T-21-quellenlink-dokumentviewer` (von `origin/main` abgezweigt).
**Gegenstand:** [Issue #28](https://github.com/tsorer/LearnFlow/issues/28) (T-21, „Quellenlink: Originaldokument-Viewer") — Klick auf einen Quellenverweis öffnet einen Viewer mit hervorgehobenem Abschnitt. Umsetzung als Umsetzungsplan → Implementierung → PR → automatisiertes Review (`claude[bot]`) → mehrere Runden Review-Fixes, dazwischen eine vom Nutzer selbst durchgeführte Rebase-Prüfung.
**Ergebnis:** PR [#112](https://github.com/tsorer/LearnFlow/pull/112) mit sechs Commits: der ursprüngliche Viewer, ein Fix für einen zu weiten Datenzugriff (Fenster statt ganzes Dokument), zwei Runden a11y-/Fokus-Fixes (Punkte 3+6, dann 4+5, letztere zwei zusammengesquasht), ein CI-Lint-Fix, und zuletzt eine Spec-Korrektur (`Citation.page`/`heading` als `required`). Alle Review-Punkte 1–7 behoben, 8–10 bewusst offen gelassen und im PR-Kommentar begründet. Voller Umfang jeweils gegen `ruff`/`mypy`/`pytest` (Backend) und `eslint`/`tsc`/`vitest` (Frontend) verifiziert; jeder a11y-/Fokus-Fix zusätzlich per `git stash` gegen den Vorzustand als echter Regressionstest bestätigt.

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/28 (T-21)

### Claude

Issue #28 gelesen (Akzeptanzkriterien: Klick öffnet Viewer, Abschnitt hervorgehoben, korrektes Originaldokument) sowie das verwandte, bereits gemergte T-20 (#27) — dessen Abschluss-Kommentar hielt fest, dass `CitationEntry` in `MessageBubble.tsx` bereits ein bedienbares Element ist, T-21 aber noch keinen Endpoint für den Dokument*inhalt* hat, und dass `heading` im `Citation`-Schema fehlt (US-01 nennt „Abschnitt"). `openapi.yaml` (Citation-Schema, `/api/documents/{id}`), `app/models/tables.py` (Chunk-Felder `content`/`page`/`heading`), `app/auth/dependencies.py` und `Docs/01_UserStories.md` (US-01) geprüft.

Plan vorgeschlagen: Viewer rendert den geparsten Chunk-Text, nicht das Binär-Original (Begründung: der belegende Abschnitt *ist* der Chunk, exakte Hervorhebung ohne Koordinaten-Rückrechnung, kein PDF.js nötig). Neuer Endpoint `GET /api/documents/{id}/content`, bewusst für jede Rolle erreichbar (nicht nur `knowledge_owner`), `Citation.heading` ergänzt, `DocumentViewer`-Komponente, Umbau von `CitationEntry` (Klick öffnet Viewer statt nur den Auszug aufzuklappen). Zwei offene Fragen gestellt: Chunk-Text- oder Original-Datei-Viewer, und ob Lernende den vollen Dokumenttext sehen dürfen (Sicherheitsentscheid).

---

## 2 — Nutzer

> Chunk-Text-Viewer, und ja, Lernende dürfen den Text sehen

### Claude

Branch `feat/T-21-quellenlink-dokumentviewer` von `origin/main` erstellt. Umgesetzt:

- `openapi.yaml`: `Citation.heading` ergänzt; neuer Endpoint `GET /api/documents/{document_id}/content` → `DocumentContent`/`DocumentContentChunk`, ohne `403` (jede Rolle), mit `409` für ein noch nicht `available` Dokument.
- `app/routers/query.py`: `Citation`-Pydantic-Modell und `_to_citations` um `heading` erweitert.
- `app/routers/documents.py`: neue Route `get_document_content` (`get_current_user`, nicht `require_knowledge_owner`), lädt Chunks sortiert nach `chunk_index`.
- `make generate-api` im Docker-Container ausgeführt (lokales Node 22, da `openapi-typescript` in `node:22-alpine` läuft), `schema.d.ts` aktualisiert.
- Frontend: neue Komponente `DocumentViewer.tsx` (Dialog, Escape schliesst, Fokus auf Schliessen-Button, scrollt zum hervorgehobenen Chunk); `CitationEntry` in `MessageBubble.tsx` umgebaut — Klick öffnet den Viewer, das Aufklappen des Auszugs wurde ein zweiter, sekundärer Button.
- Tests: 8 neue Backend-Tests (`test_documents.py`), Anpassung bestehender Citation-Tests in `query.test.tsx` an die neue Zwei-Buttons-Struktur, ein neuer Test für den kompletten Viewer-Flow.

Backend-QA im laufenden Container (`docker exec src-api-1 ruff check .` / `mypy app worker` / `pytest`) grün. Frontend-Tests scheiterten lokal an einem vorbestehenden Node-24/`undici`-FormData-Problem (unabhängig von dieser Änderung, per `git stash` gegen den Basisstand verifiziert); Workaround: Tests in einem `node:22-alpine`-Container laufen lassen — 124/124 grün. Commit erstellt, PR noch nicht eröffnet.

---

## 3 — Nutzer

> push it and open the PR

### Claude

`git push -u origin feat/T-21-quellenlink-dokumentviewer`, dann `gh pr create` mit Beschreibung, Design-Entscheid und Test-Plan-Checkliste (offene Punkte: `make e2e`, manueller Durchgang, Zweit-Review). PR [#112](https://github.com/tsorer/LearnFlow/pull/112) erstellt.

---

## 4 — Nutzer

> bewerte das Feedback (PR-Kommentar)

### Claude

`gh api repos/tsorer/LearnFlow/issues/112/comments` abgerufen: ein automatisierter Review-Kommentar von `claude[bot]` (ausgelöst durch `@FraMo80: mach ein Review`) mit 10 Punkten. Jeder Punkt einzeln gegen den tatsächlichen Code geprüft (nicht nur den Text übernommen):

1. `select(Chunk)` lädt ungenutzte `embedding`/`tsv`-Spalten mit — **bestätigt**, mehrere MB pro Viewer-Öffnung möglich.
2. Zugriffsbegründung deckt weniger als der Endpoint liefert (Begründung rechtfertigt nur den zitierten Chunk, Endpoint liefert das ganze Dokument) — **bestätigt**, Zitat aus der Spec exakt verifiziert.
3. Fokus-Effekt hängt an `onClose`, das bei jedem Elternrender neu ist → Fokus-Klau — **bestätigt** durch Codelesung.
4. `aria-modal="true"` ohne Focus-Trap/-Restore — **bestätigt**, keine entsprechende Logik im Code.
5. Hervorhebung nur über Farbe/Rahmen, keine textuelle Information — **bestätigt**, direkt AK-relevant.
6. `aria-label` auf dem Auszug-Button verschluckt dessen sichtbaren Text für Screenreader — **bestätigt**, eigene Regression aus dem Umbau von `CitationEntry`.
7. `Citation.heading`/`page` fehlen in `required`, obwohl das Pydantic-Modell sie immer sendet; `DocumentContentChunk` macht es im selben PR richtig — **bestätigt**, Widerspruch in der eigenen Spec.
8. `DocumentContent.status` kann durch die 409-Kurzschaltung nur `"available"` sein — **bestätigt**, harmlos.
9. Testlücken (Highlight-Test prüft nicht wirklich die Hervorhebung, `heading` im Label ungetestet, Viewer-Fehlerpfade ungetestet, irreführender Testname) — alle vier **bestätigt**.
10. Kleinigkeiten (kein Portal, Backdrop-Klick bricht Textauswahl ab, kein Empty-State, `heading` bei PDFs immer `null`) — **bestätigt**, insbesondere der PDF-Punkt (`services/parsing.py`) real und nicht dokumentiert.

Empfehlung: 1, 3, 6 sowie die zwei Zeilen aus 7 vor Merge fixen, 2 als Spec-Korrektur, Rest als Nachtrag.

---

## 5 — Nutzer

> wieso wird das gesamte Dokument geliefert und nicht nur der Chunk?

### Claude

Zwei Gründe erklärt: die Produktanforderung (US-01/AK von #28 verlangen, den Abschnitt *im Kontext* zu sehen, nicht nur den isolierten Chunk, den `CitationEntry` schon vorher aufklappt) und die tatsächliche Lücke, die Punkt 2 der Review trifft (die Zugriffsbegründung deckt nur den zitierten Chunk, nicht den Rest des mitgelieferten Dokuments). Zwei Optionen genannt: (1) Spec-Text auf „jede Rolle darf den Volltext jedes Dokuments im Pilot-Bereich lesen" korrigieren, oder (2) den Endpoint auf ein Fenster um den zitierten Chunk einschränken (`?around=<chunk_id>&window=N`), was nebenbei auch Punkt 1 (unnötige Vektor-Übertragung) und die fehlende Grössenbegrenzung löst. Tendenz zu Option 1 für den Piloten genannt, aber Rückfrage gestellt.

---

## 6 — Nutzer

> Setz Option 2 um

### Claude

- `openapi.yaml`: `GET /api/documents/{document_id}/content` verlangt jetzt `around` (Pflicht, chunk_id) und akzeptiert optional `window` (0–10, Default 2); Begründungstext korrigiert, deckt jetzt genau das, was der Endpoint tut; neuer `404`-Fall für „`around` gehört nicht zu diesem Dokument".
- `app/routers/documents.py`: löst zuerst `chunk_index` des `around`-Chunks auf (404 falls nicht im Dokument), lädt dann nur die Chunks im Fenster `[index-window, index+window]` per Spaltenauswahl (kein `select(Chunk)` mehr — löst dabei Punkt 1 mit).
- Frontend: `getDocumentContent` nimmt `chunk_id` als Pflichtparameter, `DocumentViewer` übergibt `citation.chunk_id`.
- Tests: 8 Backend-Tests neu/angepasst (Fenstergrenzen per SQL-Inspektion mit `literal_binds`, Default-Window, `around` fehlt/passt nicht/zu grosses Window → 422/404); ein Frontend-Test nutzt `api.routeQuery(...)` statt `api.route(...)`, damit die Anfrage nur mit korrektem `around`-Parameter beantwortet wird (ein `RecordedRequest.url` in der Test-Infrastruktur trägt keine Query-String, deshalb dieser indirekte Weg statt einer direkten URL-Assertion).

`make generate-api` erneut im Container ausgeführt. Volle Backend-Suite und 124 Frontend-Tests grün. Commit `572efca`, gepusht.

---

## 7 — Nutzer

> Fix Punkt 3 und 6 auch noch, nur commit

### Claude

- **Punkt 3:** Fokus-auf-Mount in `DocumentViewer.tsx` in einen eigenen `useEffect` mit leerem Dependency-Array ausgelagert (lief vorher an `[onClose]`, das bei jedem Elternrender neu ist); Escape-Listener bleibt separat an `[onClose]`.
- **Punkt 6:** `aria-label` auf dem Auszug-Toggle entfernt; stattdessen `sr-only`-Präfix (bestehende CSS-Klasse, bereits in `QuizCard.tsx` verwendet) vor dem sichtbaren Auszugstext, sodass der Text Teil des Accessible Name bleibt.
- Zwei neue/verschärfte Tests (`toHaveAccessibleName`-Assertion auf den Auszugstext, ein Fokus-Retentions-Test über einen Feedback-Klick als Rerender-Trigger). Beide **vor dem Fix** per `git stash` gegen den unveränderten Code laufen lassen — beide schlugen dort fehl, damit als echte Regressionstests bestätigt — dann den Stash wiederhergestellt.

Commit `9e64a9b`, **nicht gepusht** (Anweisung: nur committen).

---

## 8 — Nutzer

> Fix Punkt 4 und 5 auch noch, nur commit. Prüf, wieso CI/backend auf git rot ist

### Claude

CI-Status über `gh pr checks 112` geprüft: `backend` und `claude-review` rot, `e2e`/`frontend` grün. `gh run view --log-failed` für den `backend`-Job zeigte `ruff` E501 (Zeile 109 statt max. 100 Zeichen) in `make_chunk_row()` (`test_documents.py`) — entstanden, weil zuvor nur `ruff check app/routers/documents.py` statt des ganzen Projekts lief. Behoben. Der `claude-review`-Job scheiterte an einem internen Fehler der Action selbst (`is_error:true` direkt nach der Initialisierung, kein von uns verursachtes Problem, auch kein Required Check laut `CLAUDE.md`).

Danach:
- **Punkt 4:** Focus-Trap ergänzt (Tab zirkuliert per `keydown`-Handler innerhalb des Dialogs, `dialogRef` + `querySelectorAll` über fokussierbare Elemente); Focus-Restore über die Cleanup-Funktion des Mount-Effekts (merkt sich `document.activeElement` vor dem Fokussieren des Schliessen-Buttons, stellt ihn beim Unmount wieder her).
- **Punkt 5:** belegender Chunk trägt jetzt `aria-current="true"` plus einen `sr-only`-Text „Belegender Abschnitt:" statt nur Farbe/Rahmen.
- Drei neue Tests (Highlight-Test um eine echte `aria-current`-Prüfung ergänzt statt nur Textvorkommen zu zählen, Fokus-Restore-Test, Tab-Trap-Test), wieder vorab per `git stash` gegen den Vorzustand als Regressionstests verifiziert (alle drei schlugen dort fehl).

Zwei Commits (`faf2e8d` CI-Fix, `a104caf` Punkt 4/5), **nicht gepusht**.

---

## 9 — Nutzer

> squash die beiden commits und dann push it

### Claude

`git reset --soft HEAD~2`, ein neuer zusammengefasster Commit mit kombinierter Nachricht (`3e545aa`). Da beide Commits zuvor nie gepusht waren, war das ein normaler Fast-Forward-Push, kein Force-Push nötig — `git status` vor dem Push zur Bestätigung geprüft. Gepusht.

---

## 10 — Nutzer

> kommentiere bitte auch noch die Ändernungen beim PR

### Claude

`gh pr comment 112` mit einer Zusammenfassung, adressiert an `@FraMo80`: Punkte 1–6 und der CI-Fix als behoben aufgeführt (mit Commit-Referenzen), Punkte 7–10 als bewusst offen gelassen benannt und kurz begründet (eher Politur als Blocker für ein Pilot-Tool), mit der Einladung, falls davon noch etwas vor dem Merge rein soll.

---

## 11 — Nutzer

> prüf mein Rebase und dann Punkt 7 auch noch fixen und pushen

### Claude

Zwischen dem letzten Push und dieser Anfrage hatte der Nutzer den Branch selbst auf einen aktualisierten `main` rebased (u. a. T-38 Admin-Parameter-Panel dazwischen gemergt). Geprüft: `git status` (kein laufender Rebase, sauberer Baum, „diverged" durch die Historien-Umschreibung), keine Konfliktmarker im Baum, und — als härterer Beweis — der Diff der T-21-spezifischen Backend- und Frontend-Dateien (`openapi.yaml`, `documents.py`, `query.py`, `DocumentViewer.tsx`, `client.ts`, `schema.d.ts`) zwischen den alten und den neuen Commit-Hashes war **byte-identisch**; nur `MessageBubble.tsx` musste sich legitim an die durch T-38 extrahierte `PARAM_LABELS`-Datei anpassen. Volle Backend-Suite und alle 135 Frontend-Tests (10 statt vorher 9 Testdateien, T-38 brachte `admin-params.test.tsx` mit) liefen grün, `ruff`/`lint`/`check` sauber — Rebase als sauber bestätigt.

Danach **Punkt 7:** `openapi.yaml` — `Citation.page`/`heading` in die `required`-Liste aufgenommen (nullable, aber nie fehlend, wie das Pydantic-Modell es schon immer sendet; deckt sich jetzt mit der Konvention, die `DocumentContentChunk` im selben PR bereits richtig anwendet). `make generate-api` neu ausgeführt; zwei Frontend-Test-Fixtures (`confidence.test.tsx`, `query.test.tsx`) brauchten `heading: null`, weil TypeScript das Feld jetzt zu Recht verlangte. Backend-Spec-Tests und volle Frontend-Suite erneut grün. Commit `4ad8789`.

Da der Rebase die Historie umgeschrieben hatte, war ein normaler Push nicht mehr möglich (kein Fast-Forward) — mit `git push --force-with-lease` gepusht (bricht sicherheitshalber ab, falls in der Zwischenzeit jemand anders auf den Branch gepusht hätte).

---

## 12 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Bestehende Exporte in `Frank/Prompts/` als Vorlage gelesen (zuletzt `2026-09-07_T-22-Performance-Test-PR-121.md`) und dieses Dokument nach der dort etablierten Konvention erstellt.
