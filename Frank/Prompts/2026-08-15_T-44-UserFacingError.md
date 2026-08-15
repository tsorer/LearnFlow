# Chatverlauf — Umsetzung T-44 (Nutzerbestimmte Fehlermeldungen über eigene Exception-Klasse)

**Datum:** 2026-08-12 (Planung und Umsetzung) / 2026-08-15 (Review-Nachgang)
**Branch:** `feat/T-44-user-facing-error` → [PR #77](https://github.com/tsorer/LearnFlow/pull/77)
**Gegenstand:** [Issue #70](https://github.com/tsorer/LearnFlow/issues/70) „[T-44] Nutzerbestimmte Fehlermeldungen ueber eigene Exception-Klasse markieren"
**Ergebnis:** zwei Commits, `fa46104` (vom Nutzer rebased/amendiert) und `d8719fe`, beide gepusht

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen. Entscheidungen aus den Rückfrage-Dialogen sind als Tabellen wiedergegeben.

---

## 1 — Nutzer

> erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/70

### Claude

*(Plan-Modus — keine Änderungen ausser der Plan-Datei.)*

**Bestandsaufnahme:** Issue #70 via `gh`, dazu der Fehlerpfad in `worker/main.py`, die drei Services (`parsing`, `chunking`, `embedding`), die Testdateien, `documents.py`, `openapi.yaml` und die Frontend-Anzeige.

Befund:

- Die gesamte Absicherung hängt an **einer Zeile**: `message = str(exc) if isinstance(exc, ValueError) else "Verarbeitung fehlgeschlagen"` (`worker/main.py:77`).
- `documents.error_message` geht über `GET /documents` **und** `GET /documents/{id}` an jeden Knowledge Owner und wird im Frontend roh in einem `<pre>` gerendert (`Upload.tsx`).
- Sieben eigene `raise ValueError` (2× Worker, 1× parsing, 2× chunking, 2× embedding) und sieben Test-Assertions über vier Testdateien.
- Kein bestehendes Exception-Modul (`app/exceptions.py`, `app/errors.py`, `app/core/` existieren nicht).
- Keine Schnittstellenänderung → **keine** `openapi.yaml`-Anpassung (ADR-010), keine Migration (`error_message` ist bereits `Text`).

**Entscheidungen (Rückfrage-Runde):**

| Frage | Entscheid |
|---|---|
| Die zwei `ValueError` in `chunking.py` (Konfigurationsprüfung), die die AK nicht als nutzerbestimmt listen | **Umformulieren + neue Klasse** — Präfix „Chunk-Konfiguration ungültig", technische Details bleiben im Log |
| Name und Basisklasse | **`UserFacingError(Exception)`** — erbt bewusst *nicht* von `ValueError`, genau die Kopplung, die das Ticket auflöst |

Danach vollständiger Plan mit Klassen-Docstring, Wurfstellen-Tabelle, Testliste (inkl. Regressionstest für einen Fremdfehler, der von `ValueError` erbt) und Verifikationsschritten vorgelegt.

---

## 2 — Nutzer

> wird der Plan von https://github.com/tsorer/LearnFlow/pull/76 beeinflusst?

### Claude

**Nein.** Die Änderungsmengen sind disjunkt: #76 fasst `openapi.yaml`, `app/main.py`, `app/config.py`, drei neue 501-Platzhalter-Router, `test_rbac.py` und das Frontend an; T-44 fasst Worker, Services und deren Tests an. Keine gemeinsame Datei, kein Merge-Konflikt.

Geprüft und im Plan ergänzt:

- Die neuen Drift-Checks (`test_rbac.py` in beide Richtungen, `npm run check` gegen `schema.d.ts`) greifen nur bei Endpoint-Änderungen — T-44 fügt keine Route hinzu.
- `error_message` wandert im Frontend von `types.ts` in das generierte `schema.d.ts`; Feld und Semantik bleiben identisch (`error_message?: string | null`).
- Inhaltlich stützt #76 den Zeitplan: es legt den `/query`-Vertrag für T-17/T-18 fest und rückt die LiteLLM-Completion-Calls im Worker näher — T-44 sollte davor landen.

---

## 3 — Nutzer

> OK, bitte den Plan umsetzen

### Claude

**Umgesetzt:**

- `app/exceptions.py` — neu, `UserFacingError(Exception)`. Der Docstring trägt die Begründung: wer `error_message` sieht, warum nur diese Klasse dort landet, und warum die Basisklasse `Exception` und nicht `ValueError` ist.
- `worker/main.py` — Entscheidungszeile auf `isinstance(exc, UserFacingError)`; `log.exception` unverändert, der vollständige Fehler bleibt im Log. Die beiden eigenen Raises (Dokument nicht gefunden, kein extrahierbarer Text) mitgezogen.
- `services/parsing.py` — Content-Type-Fehler + Docstring; `services/embedding.py` — Vektoranzahl und Dimensionen; `services/chunking.py` — beide Bereichsprüfungen mit dem Präfix „Chunk-Konfiguration ungültig: …", weil die Werte aus der `config`-Tabelle stammen und der Fehler nicht im Dokument liegt.
- Tests: vier bestehende `pytest.raises(ValueError)` umgestellt, zwei neue in `test_worker.py` — ein Fremdfehler, der von `ValueError` erbt und ein API-Key-Fragment trägt, darf nicht in `error_message` landen (plus Gegenprobe, dass ein `UserFacingError` wörtlich durchkommt).

**Checks:** `ruff` ✅ · `mypy app worker` (22 Dateien) ✅ · `pytest` 121 ✅ · Frontend-Gate (`npm ci` + lint + tsc + vitest 11/11) ✅.

**Mutationsprobe:** mit der alten Bedingung `isinstance(exc, ValueError)` schlägt `test_foreign_error_deriving_from_valueerror_stays_out_of_error_message` fehl — der Test fängt genau die Lücke, die das Ticket beschreibt.

**Manuelle Verifikation im laufenden System:**

| AK | Nachweis |
|---|---|
| Nutzerbestimmter Text kommt durch | Leere Markdown-Datei hochgeladen → `error_message: "Kein extrahierbarer Text gefunden"` |
| Fremdfehler wird generisch ersetzt | Temporärer Worker mit ungültigem `LITELLM_API_KEY` → API liefert `"Verarbeitung fehlgeschlagen"` |
| Vollständiger Fehler bleibt im Log | `docker logs` zeigt den `openai.AuthenticationError` inkl. Key-Fragment und `api_base` |

Danach temporärer Worker entfernt, `src-worker-1` wieder gestartet, die drei Testdokumente gelöscht.

**Hindernis:** Docker Desktop lief nicht — gestartet, `make qa` braucht den Stack. `make` gibt es in der Git-Bash nicht; die Recipes wurden direkt als `docker exec` / `docker run` ausgeführt.

---

## 4 — Nutzer

> beim Review kam diese Anmerkung: 1. `worker/main.py:143-144` — der Change macht eine Inkonsistenz auf, die er selbst begründet
>
> `read_chunk_config` macht ein blankes `int(values.get("chunk_size", DEFAULT_CHUNK_SIZE))`. Setzt jemand `UPDATE config SET value='fünfhundert' WHERE key='chunk_size'`, fliegt ein normaler `ValueError` — seit diesem PR kein `UserFacingError` mehr. Jeder Upload scheitert dann mit "Verarbeitung fehlgeschlagen"; vorher kam die `int()`-Meldung durch.
>
> wie kann ein Update auf 'fünfhundert' gemacht werden? Sollte nicht bereits sichergestellt sein, das es ein int-Wert ist? Andererseit macht es sicherlich Sinn darauf hinzuweisen, das der Config-Eintrag ungültig ist.

### Claude

**Zur Frage:** Nein, abgesichert ist es nicht. `config.value` ist eine einzige `Text`-Spalte für Floats (Schwellen), Ints (`chunk_size`, `stale_days`) und alles Weitere — keine Typzusicherung pro Key. Schreibpfade heute: die Alembic-Seeds und manuelles `psql`. Der einzige künftige API-Weg, `PUT /admin/config`, ist ein 501-Platzhalter, dessen TODO die Validierung ausdrücklich als T-37-Aufgabe benennt. Heute also nur mit DB-Zugang auslösbar — aber die Absicherung hinge sonst allein an einem noch offenen Ticket.

**Der Reviewer hat recht, und der Vorher-Zustand war auch nicht gut:** vorher kam Pythons interne Meldung `invalid literal for int() with base 10: 'fünfhundert'` beim Nutzer an — genau die Textsorte, die T-44 aussortiert.

**Umgesetzt:** `_as_int` in `worker/main.py` wirft `UserFacingError` mit derselben Formulierung wie die Bereichsprüfungen in `chunk_blocks`: `Chunk-Konfiguration ungültig: chunk_size ist keine ganze Zahl ('fünfhundert')`. Bewusst **kein** Fallback auf den Default — anders als `_as_float` in `services/config.py`, wo der Default fail-closed eine Laufzeitentscheidung schützt; hier würde er den Korpus still mit Parametern indexieren, die niemand konfiguriert hat.

**Checks:** `ruff` ✅ · `mypy` (25 Dateien) ✅ · `pytest` 127 ✅. Manuell: `chunk_size='fünfhundert'` gesetzt → Upload scheitert mit der neuen Meldung; danach auf `512` zurückgesetzt, Testdokument gelöscht, Worker neu gestartet, Stack healthy.

**Zwei Fehler auf Claude-Seite, offengelegt:**

| Fehler | Ursache und Korrektur |
|---|---|
| Auf dem falschen Branch editiert | Ausgecheckt war `feat/T-17-query-retrieval`; der Nutzer hatte den T-44-Commit zwischenzeitlich rebased, amendiert (`fa46104`), gepusht und den Branch gewechselt. `git status` sah sauber aus, ich hatte den Branch nicht geprüft. Änderung mit `git checkout -- src/backend/worker/main.py` zurückgenommen. |
| Branch aus dem falschen Basis-Branch erzeugt | `feat/T-44-…` wurde aus dem ungemergten `feat/T-17-query-retrieval` abgezweigt statt aus `main` — deshalb der Rebase auf Nutzerseite. |

---

## 5 — Nutzer

> ist gepushed. Den Chatverlauf wieder nach Frank/Prompts exportieren.

### Claude

Git-Stand geprüft (`d8719fe`, synchron mit `origin`, [PR #77](https://github.com/tsorer/LearnFlow/pull/77) offen), Verlauf als diese Datei abgelegt.

---

## Ergebnis

- **Zwei Commits** auf `feat/T-44-user-facing-error`: `fa46104` (Refactor) und `d8719fe` (Review-Nachtrag), beide gepusht, PR #77 offen.
- **Alle fünf Akzeptanzkriterien** aus Issue #70 erfüllt und im laufenden System durchgespielt.
- **Kernbeleg:** der Regressionstest schlägt gegen die alte Bedingung fehl — die Lücke war real, nicht nur theoretisch.
- **Offen für die DoD:** Review durch eine zweite Person.

### Bewusste Abgrenzungen

| Nicht umgesetzt | Grund |
|---|---|
| T-18 (Completion-Calls im Worker) | Eigenes Ticket; T-44 läuft bewusst davor, damit die Falle dort nicht neu entsteht |
| Wertvalidierung in `PUT /admin/config` | Gehört zu T-37; die Prüfung an der Lesestelle ist die Absicherung bis dahin |
| `openapi.yaml`, Migration, Frontend | Keine Schnittstellenänderung → nichts zu tun (ADR-010) |
| Owner-Check auf `GET /documents/{id}` | Dass jeder Knowledge Owner die Meldung sieht, ist ein eigenes Thema, nicht Teil dieses Issues |

### Bekannte offene Punkte

- Die Meldung „Dokument {id} nicht gefunden" enthält weiterhin die interne UUID. Unkritisch, weil der Aufrufer die ID ohnehin kennt.
- Die Formulierung „Chunk-Konfiguration ungültig" ist eine Verhaltensänderung nach aussen — der einzige Punkt, an dem sich der Refactor nicht rein additiv verhält.
- `_as_int` deckt nur die beiden Chunking-Keys ab. Die übrigen `config`-Werte liest `app/services/config.py` mit Fallback-auf-Default, was dort die richtige Wahl ist — die beiden Muster stehen bewusst nebeneinander.
