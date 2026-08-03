# Chatverlauf — Umsetzung T-12 (Background Worker: Parsing + Chunking)

**Datum:** 2026-08-08 (abends) bis 2026-08-09
**Branch:** `feat/T-12-parsing-chunking` (von `main`/`b721eaa`)
**Gegenstand:** [Issue #19](https://github.com/tsorer/LearnFlow/issues/19) „[T-12] Background Worker: Parsing + Chunking"
**Ergebnis:** [PR #65](https://github.com/tsorer/LearnFlow/pull/65) — ein Commit, CI grün (`backend` 1m55s, `frontend` 16s)

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen. Entscheidungen aus den Rückfrage-Dialogen sind als Tabellen wiedergegeben.

---

## 1 — Nutzer

> als nächstes steht die Umsetzung von https://github.com/tsorer/LearnFlow/issues/19 an. Erstelle in git einen neuen Branch und erstellen einen Plan, wie das Issue umgesetzt werden kann. Stelle mir vor der Umsetzung Fragen, bis alle Unklarheiten geklärt sind.

### Claude

**Bestandsaufnahme:** Issue #19 via `gh`, dazu `worker/main.py` (TODO-Platzhalter aus T-11), `models/tables.py`, `routers/documents.py`, `alembic/versions/`, `requirements.txt` sowie ADR-007 und das ERD.

Befund: Tabelle `chunks` existiert bereits samt HNSW- und GIN-Index (Migration 0003) — **keine Schema-Migration nötig**. Upload erlaubt bereits exakt `.pdf/.docx/.md`. Keine API-Änderung → `openapi.yaml` bleibt unberührt (ADR-010). `pypdf` und `python-docx` sind bereits Dependencies, ein Tokenizer fehlt.

**Drei Widersprüche zwischen Issue, ADR und Code identifiziert** und zur Entscheidung vorgelegt, statt still eine Variante zu wählen. Plan-Skizze: `app/services/parsing.py` + `app/services/chunking.py` als reine, isoliert testbare Funktionen (DoD-Kriterium 3), Orchestrierung im Worker.

**Entscheidungen (Rückfrage-Runde 1):**

| Frage | Entscheid |
|---|---|
| Overlap: Issue sagt 50, ADR-007 sagt 64 | **Konfigurierbar über die `config`-Tabelle** |
| PDF-Parser: Issue nennt PyMuPDF, `requirements.txt` hat pypdf | **pypdf behalten** (MIT statt AGPL, bereits vorhanden) |
| Chunker: eigen vs. langchain-text-splitters | **Eigen + tiktoken** |
| `chunks.tsv` (kein Trigger vorhanden) | **In T-12 mitschreiben** |

**Entscheidungen (Rückfrage-Runde 2):**

| Frage | Entscheid |
|---|---|
| Defaults der neuen config-Keys | **512 / 64** (ADR-007) |
| Chunk-Metadaten | **`page` + `heading`, best effort** |
| Dokument ohne extrahierbaren Text | **`status='failed'`** mit Meldung |
| Test-Fixtures | **Kleine Dateien committen** |

**Entscheidung (Rückfrage-Runde 3):** Beim Prüfen des Dockerfiles fiel auf, dass `tiktoken` seine BPE-Dateien beim ersten Aufruf über das Netz lädt (Azure Blob Storage) — relevant für CI-Stabilität und für ein netzrestriktives Deployment (ADR-004). Entscheid: **Token-Zählfunktion injizierbar + Warmup im Dockerfile**.

Danach vollständiger Plan mit Modul-Layout, SQL-Fluss, Testliste und Docs-Updates vorgelegt.

---

## 2 — Nutzer

> ja, setz das so um

### Claude

**Umgesetzt:**

- `app/services/parsing.py` — ein Block je PDF-Seite / DOCX- bzw. Markdown-Absatz, mit `page`/`heading` für die spätere Quellenanzeige (US-01). Markdown-Parser ignoriert `#` innerhalb von Code-Fences.
- `app/services/chunking.py` — rekursives Splitting Überschrift > Absatz > Zeile > Satz > Wort, Overlap-Übertrag, Fallback für Wörter grösser als ein Chunk (PDF-Textlayer ohne Leerzeichen). Blöcke mit gleichem `(heading, page)` bilden eine Sektion; Sektionsgrenzen sind harte Chunk-Grenzen, damit die Metadaten exakt statt geschätzt sind.
- `worker/main.py` — laden → parsen → chunken → alte Chunks löschen (Idempotenz) → Insert inkl. `to_tsvector('german', …)` → `chunk_count` + `available`.
- Migration `0007_chunking_config.py`, Dockerfile-Warmup, `tiktoken` in `requirements.txt`.
- 24 Tests, Fixtures für alle drei Formate.
- ADR-007 und ERD um die config-Keys und Migration 0007 ergänzt.

**Hindernisse und wie sie gelöst wurden:**

- Docker lief nicht, lokal fehlten `pypdf`/`python-docx` → venv im Scratchpad aufgebaut; Fixtures (PDF von Hand, DOCX als OOXML-ZIP) mit der Standardbibliothek deterministisch erzeugt.
- Ein erster mypy-Fehler (`QueueManager`/`AsyncpgDriver`) war ein Artefakt der eigenen venv: `pgqueuer` war ohne Version installiert (1.3.2), das Projekt pinnt `<1.0.0`. Nach Korrektur sauber.

**Checks:** `ruff` ✅ · `mypy` ✅ · `pytest` 53 ✅. Zusatzprüfung mit echtem tiktoken über die Korpus-PDF (SKOS-Richtlinien, 150 Seiten): 200 Chunks, Token min/median/max 50/390/509, kein Chunk über 512, Umlaute intakt (0 Ersatzzeichen).

**Ausdrücklich als offen gemeldet:** die manuelle Verifikation im laufenden System (DoD-Punkt) war mangels Docker-Daemon nicht möglich.

Nebenbei nötig: `.gitattributes` neu angelegt — `core.autocrlf=true` hätte die PDF-Fixture beim Commit zerschossen (Git stufte sie als Text ein). Nach der Regel byte-identisch im Index verifiziert.

---

## 3 — Nutzer

> docker sollte nun laufen, bitte Punkt 1 prüfen

### Claude

api und worker neu gebaut (neue Dependency), Migration `0007` lief beim Start automatisch mit.

**Dabei zwei Blocker aus T-11 gefunden, die die Akzeptanzkriterien unerreichbar machten:**

1. **Der Worker hat nie gearbeitet.** Der Entrypoint war als `lambda` registriert; pgqueuer entscheidet per `iscoroutinefunction()`, ob es awaitet — bei einem Lambda ist das `False`, die zurückgegebene Coroutine wurde verworfen (`RuntimeWarning: coroutine was never awaited`). Jeder Job landete nach ~20 ms als „successful" im `pgqueuer_log`, während das Dokument auf `pending` stehenblieb. Uploads liefen seit T-11 stillschweigend ins Leere — es fiel nur nicht auf, weil der Job-Body bis dahin leer war.
2. **Geteilte DB-Verbindung.** Job-Verarbeitung und pgqueuer-LISTEN/dequeue nutzten dieselbe asyncpg-Connection; sobald echte Arbeit lief, warf der zweite parallele Upload `InterfaceError: another operation is in progress`. Jobs holen sich jetzt eine Verbindung aus einem Pool.

Beide gefixt, weil AK 3 sonst nicht erreichbar ist.

**Verifikation im laufenden System:**

| Prüfung | Ergebnis |
|---|---|
| PDF/DOCX/MD Upload | alle `available`, je 2 Chunks, `chunk_count` = Zeilen in `chunks` |
| Metadaten | PDF `page` 1/2 · DOCX/MD `heading` korrekt · `tsv` gesetzt · `embedding` NULL (T-13) |
| Korpus-PDF, 150 Seiten | `available`, 200 Chunks, ~2 s |
| Deutsche Volltextsuche | 107 Treffer „Sozialhilfe"; „Existenzminimums" trifft via Stemming |
| Leeres Dokument | `failed`, „Kein extrahierbarer Text gefunden" |
| Re-Processing | weiterhin 200 Chunks, keine Duplikate |

`make` existiert in dieser Shell nicht → die `make qa`-Befehle einzeln ausgeführt: Backend `ruff`/`mypy`/`pytest` 53 ✅, Frontend lint/check/test 8 ✅.

**Als Follow-up gemeldet (nicht gefixt):** `app/queue.py` schickt ein `pg_notify` mit nacktem Entrypoint-Namen → pro Upload ein CRITICAL-Traceback im Worker-Log. Dafür Task-Chip hinterlegt. Ausserdem: Verifikations-Uploads liegen als Testdaten in der Dev-DB.

---

## 4 — Nutzer

> Testdaten hab ich gelöscht. Mach bitte ein Squash von den zwei Commits

### Claude

Zustand geprüft (sauberer Baum, Branch nicht gepusht), dann Soft-Reset auf `main` und Neu-Commit. Ergebnis: ein Commit, 16 Dateien. Die Worker-Fixes stehen als eigener Abschnitt in der Commit-Message, damit sie im Review nicht in den 760 Zeilen untergehen. Binär-Fixtures im Diff als `Bin` geführt — die `.gitattributes`-Regel greift.

---

## 5 — Nutzer

> *(Aufgabentext des zuvor hinterlegten Task-Chips, hier gekürzt)* In LearnFlow sendet `src/backend/app/queue.py` am Ende von `enqueue_document`: `pg_notify('ch_pgqueuer', 'process_document')`. pgqueuer 0.26.3 erwartet auf dem Kanal ein JSON-Event (`models.AnyEvent`), nicht den nackten Entrypoint-Namen. […] Aufgabe: das Notify-Payload anpassen oder das manuelle `pg_notify` entfernen, falls pgqueuer den Trigger selbst mitbringt. Version im Blick behalten — ein Pin könnte sinnvoll sein. Verifizieren: Upload, Log frei von Tracebacks, Dokument auf `status='available'`.

### Claude

**Untersuchung ergab: kein Format-Umbau nötig.** Migration `0001` installiert bereits pgqueuers eigenen Trigger `tg_pgqueuer_changed`, der bei jedem INSERT das korrekte `table_changed_event`-JSON auf `ch_pgqueuer` sendet (in der laufenden DB als `tgenabled = O` bestätigt). Das manuelle Notify war also nicht nur falsch formatiert, sondern schlicht überflüssig.

**Entscheidungen (Rückfrage):**

| Frage | Entscheid |
|---|---|
| GitHub-Issue anlegen? | **Nein, direkt fixen** |
| Branch-Basis | **In den T-12-Branch dazu** |
| `pgqueuer` pinnen? | **Spanne beibehalten** |

Zum Pin wurde der Einwand festgehalten: Migration 0001 baut laut Docstring exakt das Schema von 0.26.3 nach, ein Rebuild kann eine neuere 0.x ziehen. Entscheid des Nutzers respektiert, Punkt im PR dokumentiert.

**Umsetzung:** `pg_notify`-Zeile entfernt (mit Kommentar, warum dort bewusst keine steht), `test_queue.py` umgeschrieben — prüft jetzt den INSERT und separat, dass *kein* `pg_notify` mehr gesendet wird.

**Verifikation:** 3 Uploads nach dem Fix → alle `available`; `docker logs src-worker-1 --since 5m` → **0 CRITICAL, 0 Tracebacks**. LISTEN/NOTIFY greift wieder: Upload → Verarbeitung in **70 / 12 / 9 ms** statt Polling-Fallback. `ruff` ✅ · `mypy` ✅ · `pytest` 54 ✅.

---

## 6 — Nutzer

> Squash die beiden Commits auch zusammen

### Claude

Soft-Reset auf `main`, ein Commit `109cc4c`, 18 Dateien. Die nun drei Queue-Fixes als eigener Abschnitt in der Commit-Message.

---

## 7 — Nutzer

> Push und erstelle den PR. Mit Hinweis auf 64, da so in ADR genannt. Hinweis auf pypdf und auch Hinweis auf pg_notify-Fix

### Claude

Branch gepusht, [PR #65](https://github.com/tsorer/LearnFlow/pull/65) erstellt (Titel mit Branchnamen präfixiert, `Closes #19`). Die drei gewünschten Hinweise stehen unter „Drei Hinweise für den Review":

1. **Overlap 64 statt 50** — ADR-007 ist laut CLAUDE.md Single Source of Truth; über die config-Tabelle wäre 50 eine reine Konfigurationsänderung.
2. **pypdf statt PyMuPDF** — bereits Dependency, MIT statt AGPL-3.0, kein 30-MB-Binary.
3. **pg_notify-Fix** — zusammen mit den zwei anderen Queue-Defekten, mit Ursache, Wirkung und der 9–70-ms-Messung.

Dazu im PR: Akzeptanzkriterien mit Nachweisen, Verifikation im laufenden System, `tiktoken` samt Offline-Begründung, `.gitattributes`, und als offener Punkt die `pgqueuer`-Versionsspanne.

CI beobachtet — beide Required Checks grün (`backend` 1m55s, `frontend` 16s). Das Risiko der offenen Versionsspanne hat sich in diesem Lauf nicht materialisiert; das war Glück der Auflösung, keine Garantie.

---

## Ergebnis

- **Ein Commit** `109cc4c` auf `feat/T-12-parsing-chunking`, +777/−31 über 18 Dateien.
- **Alle drei Akzeptanzkriterien** aus Issue #19 erfüllt und im laufenden System durchgespielt.
- **Drei Alt-Defekte** aus T-11 mitbehoben, ohne die T-12 nicht funktionsfähig gewesen wäre.
- **Offen für die DoD:** Review durch eine zweite Person.

### Abweichungen vom Issue-Text (bewusst, im PR begründet)

| Issue | Umgesetzt | Grund |
|---|---|---|
| Overlap 50 Token | 64 (konfigurierbar) | ADR-007 ist Single Source of Truth |
| PyMuPDF | pypdf | MIT statt AGPL-3.0, bereits Dependency |

### Bekannte offene Punkte

- `requirements.txt` erlaubt `pgqueuer>=0.14.0,<1.0.0`, während Migration `0001` exakt das Schema von 0.26.3 nachbaut — ein Rebuild kann auseinanderlaufen.
- `documents.updated_at` wird vom Worker nicht fortgeschrieben (er nutzt rohes SQL, `onupdate` greift nur über das ORM).
