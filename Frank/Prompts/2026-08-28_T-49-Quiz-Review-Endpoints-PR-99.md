# Chatverlauf — T-49 Quiz-Review-Endpoints (lesen, freigeben, ziehen), PR #99

**Datum:** 2026-08-28 – 2026-09-01
**Branch:** `feat/T-49-quiz-review-endpoints`, von `origin/main` abgezweigt. Zwischenzeitlich `main` gemergt (Alembic-Drift), auf Wunsch später auf `main` rebased. Als Squash-Merge `783823a` in `main`.
**Gegenstand:** Issue [#98](https://github.com/tsorer/LearnFlow/issues/98) „[T-49] FastAPI: GET /quiz/questions + PATCH /quiz/questions/{id}" (US-07, Konsument US-08) — vom Umsetzungsplan bis zum gemergten PR.
**Ergebnis:** [PR #99](https://github.com/tsorer/LearnFlow/pull/99), zwei Commits, Approve durch `luenlestra` mit drei Findings, zwei davon im selben PR umgesetzt. Scope bewusst um einen dritten Endpoint erweitert (`GET /api/quiz/questions/sample`). Nebenprodukte: Entscheid-Abschnitt in #98, zwei Kommentare an [#43](https://github.com/tsorer/LearnFlow/issues/43) (T-36), Korrektur des 422-Schemas von `Error` auf `ValidationError`.

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/98 (T-49)

### Claude

Issue gelesen, Codebasis abgeklopft: Tabelle und Constraints liegen bereits vor (Migration `0016` mit `status`-CHECK, `jsonb_array_length(options) = 4`, Spalte `approved_at`) — **keine Migration nötig**. Das Schema `QuizQuestion` steht vollständig in `openapi.yaml`, es fehlen nur die Pfade. `QuizQuestionResponse` und `_to_response` aus T-33 sind wiederverwendbar.

Zwei Muster als Vorlage benannt: „nicht schreibbares Feld → 422" aus dem PUT in `app/routers/admin.py`, 404-Verhalten aus `documents.py`. Und ein Befund, der den Testschnitt prägte: die Suite mockt die Session per `AsyncMock`, es gibt **keine** Fixture mit echter DB — also Regeln als reine Funktionen testen, Endpoints nur auf Verdrahtung.

Plan in sechs Schritten (Spec zuerst, Typen generieren, GET, PATCH, Tests, Abschluss) plus eine Tabelle mit sechs Entscheiden, die nicht still getroffen werden sollten:

| # | Frage | Vorschlag |
|---|---|---|
| 1 | PATCH ohne ein einziges Feld | 422 statt stillem No-op-200 |
| 2 | Was heisst „inhaltliche Änderung"? | Wert weicht ab, nicht „Feld im Payload" |
| 3 | Wiederholtes `status: approved` | stempelt jedes Mal neu (wörtlich die AK) |
| 4 | Bereichsfilter | kein Join, MVP hat einen Bereich |
| 5 | Sortierung | `created_at DESC, id DESC` — Tiebreaker, sonst Blätter-Fehler |
| 6 | Rate Limit | keins, kein LLM-Aufruf |

Zur „Offen"-Frage des Issues (Stichprobe für T-36) die Empfehlung: eigener Endpoint analog `sample_chunks`, nicht Client-Auswahl — sonst müsste der Browser den ganzen Pool laden.

> **Anmerkung im Rückblick:** Entscheid 3 war die Stelle, die der Reviewer später zu Recht bemängelte. Die Begründung „wörtlich die AK" war zu schwach — siehe Turn 9.

---

## 2 — Nutzer

> leg los, Spec-Diff zuerst zeigen

### Claude

Branch von `origin/main`. In `openapi.yaml` zwei Pfade und zwei Schemas ergänzt: `QuizQuestionPage` (`{items, total}`) und `QuizQuestionUpdate` mit `additionalProperties: false` und `minProperties: 1` — das ist die Spec-Seite von „Beleg-Felder sind nicht schreibbar" und landet so auch in den generierten Typen. Spec im Container gegen `openapi_spec_validator` geprüft und verifiziert, dass der Container die geänderte Datei überhaupt sieht (Bind-Mount).

---

## 3 — Nutzer

> mach einen Code-Kommentar, dass question_id verwendet wird, damit es einheitlich ist. Docker ist gestartet

### Claude

Pfadparameter von `{id}` auf `{question_id}` umbenannt, mit YAML-Kommentar an der Stelle: die übrigen Pfade benennen ihren Schlüssel nach der Ressource (`{document_id}`, `{answer_id}`), und der generierte Client benennt sein Argument danach — die Abweichung wäre in jedem Aufruf sichtbar.

Danach Typen generiert und implementiert: `visible_statuses` und `apply_update` als reine Funktionen, darum herum die zwei Routen. Zwei Details, die beim Bauen dazukamen und im Plan nicht standen — `{"status": null}` wird als 422 abgewiesen (die Spalten sind NOT NULL, die Spec deklariert kein Feld nullable), und der Status-Filter für Lernende kurzschliesst vor der DB statt ein `IN ()` abzusetzen.

QA: `ruff` + `mypy` sauber, 472 Tests grün. `ruff format --check` meldet 18 Dateien, davon 17 Bestand — das Projekt erzwingt es nicht (`make qa` ruft es nicht auf), also nichts angefasst.

**Manuell am laufenden Stack durchgespielt.** Dabei zwei Stolpersteine: Port 8000 ist im Compose-Setup nicht publiziert (nur `webapp` auf 80), obwohl `src/README.md` ihn nennt — `curl` antwortet wortlos, die API ist über `http://localhost/api/...` erreichbar. Und für Testdaten wurden vier markierte Zeilen direkt in die Dev-DB geschrieben statt `POST /quiz/generate` aufzurufen, um keinen LLM-Batch auszulösen; danach wieder gelöscht. Alle AK bestätigt, inklusive der vollen Kette der Rücksetz-Regel und aller 422-Fälle.

---

## 4 — Nutzer

> Kommentar an #43 anhängen

### Claude

Kommentar an #43 mit dem Entscheid zur Stichprobe formuliert. Vor dem Posten die eigene Behauptung geprüft, dass `sample_chunks` per `ORDER BY random()` zieht — steht so in `retrieval.py:126`. Gepostet, mit der Einschränkung, dass offen bleibt, ob daraus ein eigenes Ticket wird oder es in T-36 mitläuft.

---

## 5 — Nutzer

> Entscheid: eigenen Endpoint erstellen. Hier und nicht in einem eigenen Issue. Analog sample_chunks

### Claude

`GET /api/quiz/questions/sample` gebaut: Spec, Route, acht Tests. Drei Entscheide dabei benannt — eigener Pfad statt Flag an der Liste (eine Stichprobe ist nicht sortiert und nicht pageable), `approved` **unabhängig von der Rolle** (hier sieht auch der Bereichsverantwortliche das Quiz der Lernenden), und keine Anzahl als Parameter, sondern `QUIZ_LENGTH = 5`.

Kein Join auf `documents` nötig: wird ein Dokument ersetzt, fallen seine Fragen ohnehin auf `pending` zurück, eine freigegebene Frage hat also immer eine aktuelle Quelle.

Smoke-Test mit 8 freigegebenen + 2 offenen Fragen: drei Züge ergaben drei verschiedene Fünfermengen, `total=8`, nie eine `pending`-Frage dabei, leerer Pool → `200 {"items":[],"total":0}` statt Fehler.

---

## 6 — Nutzer

> Issue-Text anpassen und den Offen-Teil mit den Entscheid ersetzen. und auch den Nachtrag beim Issue #43 posten

### Claude

Issue #98 umgeschrieben: Akzeptanzkriterien für den dritten Endpoint ergänzt (als *nachträglich aufgenommen* markiert), der Abschnitt „Offen — hier zu entscheiden" durch „Entschieden (2026-08-28)" ersetzt, mit den Gründen gegen die Client-Auswahl und gegen ein Flag am Lese-Endpoint. Nachtrag an #43 gepostet: entschieden und bereits gebaut.

---

## 7 — Nutzer

> **1. Blocker: falsches 422-Schema in der Spec**
> `openapi.yaml:522-529` (GET) und `openapi.yaml:590-598` (PATCH) referenzieren für `422` das Schema `Error` (`detail: string`). Beide 422 kommen aber aus Pydantic/FastAPI, nicht aus einem handgeworfenen `HTTPException` — der Body ist die Liste […]
> Die Spec hat dafür bereits `ValidationError` (`openapi.yaml:636`), und dessen eigene Beschreibung warnt wörtlich davor: „Bewusst nicht `Error`… ein Client, der beide gleich behandelt, liest den falschen Typ." `/api/query` macht es korrekt (`openapi.yaml:127`). Das `Error` bei `/api/admin/config` (`openapi.yaml:404`) ist kein Präzedenzfall — dort wird `HTTPException(422, detail="…")` mit String geworfen […]
> Folge: `schema.d.ts` typisiert für T-35 beide 422-Bodies als `{detail: string}`. […] Fix: beide `$ref` auf `ValidationError` umstellen und `make generate-api` erneut laufen lassen.

### Claude

Berechtigt. Die Stellen am Code nachgeprüft — `/api/query` nutzt tatsächlich `ValidationError`, und das `Error` bei `/api/admin/config` ist korrekt, weil dort ein String geworfen wird (`admin.py:120`). Beide `$ref` umgestellt, Typen neu generiert, und ein Test-Helfer `assert_validation_error_body` ergänzt, der die **Listenform** von `detail` prüft statt nur den Statuscode — sonst kann die Spec unbemerkt zurückfallen.

---

## 8 — Nutzer

> squash und PR aufmachen

### Claude

Ein Commit (`4599ffc`), nur die eigenen fünf Dateien — zwei fremde Änderungen lagen unabhängig im Working Tree und blieben draussen. PR #99 aufgemacht, mit den fünf nicht selbsterklärenden Entscheiden, einem ausdrücklichen **Scope-Hinweis** (der Sample-Endpoint geht über die ursprünglichen AK hinaus) und im Review-Abschnitt der offenen Angabe, dass das 422-Schema im ersten Stand falsch war und eine generische Response-Schema-Prüfung weiterhin fehlt. CI grün.

---

## 9 — Nutzer

> bewerte das Feedback von https://github.com/tsorer/LearnFlow/pull/99

### Claude

Approve durch `luenlestra` mit drei Findings. Vor der Bewertung die Tatsachenbehauptungen des Reviews geprüft — der Replace-Pfad nullt `approved_at` tatsächlich (`documents.py:243`), und US-08 sagt wörtlich „pro Bereich" (`Docs/02_Requirements.md:172`). Zusätzlich die eigene Commit-Behauptung zum `ValidationError`-Fix im committeten Stand verifiziert.

**Finding 1 (`approved_at` wird bei jedem Speichern neu gestempelt) — berechtigt.** Genau der Entscheid 3 aus dem Plan. Der Reviewer hat aber das stärkere Argument: nicht der zweite Klick, sondern das Board, das beim Speichern *alle* Felder round-trippt, `status` inklusive. Das ist dieselbe Begründung, mit der eine Zeile darüber der Wertvergleich für die Inhaltsfelder gebaut wurde — also eine Inkonsistenz in der eigenen Argumentation, nicht Geschmack.

**Finding 2 (kein Bereichsfilter) — sachlich richtig, Nicht-Blocker korrekt eingeordnet.** Ein Bereichs*parameter* liesse sich heute gar nicht sinnvoll bauen: es gibt kein `area`-Feld am Konto, der Filter wäre eine Konstante.

**Finding 3 (Antwortschlüssel im Payload) — richtige Beobachtung, Begründung zu stark.** „Zwangsläufig" stimmt nicht: ein zustandsloser Prüf-Endpoint würde nichts personenbezogen speichern und den Schlüssel trotzdem im Backend halten. Trade-off, keine Notwendigkeit.

Ergänzt, was das Review **nicht** anspricht: Last-write-wins beim PATCH (kein optimistisches Locking), und `total` im Sample als Poolgrösse in einem Typ namens `QuizQuestionPage` — eine leichte Bedeutungsdehnung.

---

## 10 — Nutzer

> Finding 1 fixen, Spec-Satz für Finding 2 dazu, danach Kommentar auf git posten

### Claude

Beides gebaut — `apply_update` stempelt nur noch bei einer wirklich neuen Freigabe, vier neue Tests; je ein Absatz zur vertagten Bereichsfilterung in beiden Lese-Endpoints der Spec.

Dann **Halt vor dem Commit:** Docker war zwischenzeitlich gestoppt, und die Backend-Tests laufen ausschliesslich im Container. `schema.d.ts` liess sich mit dem lokalen `openapi-typescript` (gleiche Version) regenerieren, aber `ruff`, `mypy` und die Tests nicht. Ohne grüne Tests weder gepusht noch dem Reviewer geschrieben, es sei erledigt.

---

## 11 — Nutzer

> Docker läuft, mach weiter

### Claude

Container hoch, aber die API in einer Restart-Schleife: `Can't locate revision identified by '0017'`. Die Dev-DB stand auf einer Migration, die es auf `main` gibt (aus #101/#103/#104), auf diesem Branch aber nicht — der bekannte Alembic-Drift. `origin/main` in den Branch gemergt statt an der Datenbank zu drehen; konfliktfrei, keine der drei Änderungen berührt `openapi.yaml`, `schema.d.ts` oder `quiz.py`.

Danach voller Durchlauf grün (`ruff`, `mypy`, 484 Tests; Frontend `lint` + `check` + 86 Tests). Die Container-Generierung von `schema.d.ts` ergab exakt denselben Diff wie die lokale — die Datei war also schon die richtige. Commit `1808164` als **eigener** zweiter Commit, damit der Reviewer seinen Stand wiedererkennt. Antwort-Kommentar am PR: Finding 1 übernommen wie vorgeschlagen, Finding 2 als Spec-Absatz, Finding 3 sachlich eingeschränkt, Last-write-wins ausdrücklich als bewusst offen benannt — und offen geschrieben, dass der Fall vorher bekannt und mit der falschen Begründung entschieden worden war.

---

## 12 — Nutzer

> mach bitte ein Rebase auf den main statt eines merges

### Claude

Vorher Sicherungsreferenz `backup/T-49-pre-rebase` gesetzt. Rebase auf `origin/main`, Merge-Commit fällt weg, zwei Commits bleiben (`16c30b9`, `6f2feba`). Zwei Prüfungen vor dem Push: der Baum ist **byte-identisch** zum Stand davor (`git diff backup/… HEAD` leer) und der Branch sitzt linear auf `origin/main`. Push mit `--force-with-lease` statt `--force` — ein zwischenzeitlicher fremder Push wäre abgelehnt worden statt überschrieben. Auf die Folge hingewiesen: geänderte SHAs können ein „stale approval" auslösen.

CI nach dem Rebase grün.

---

## 13 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Format an den bestehenden Dateien im Verzeichnis ausgerichtet. Beim Zusammentragen der Eckdaten aufgefallen, dass **PR #99 inzwischen gemergt** ist (Squash `783823a`, durch `FraMo80`) — im Kopf dieser Datei festgehalten.

---

## Was hängen blieb

- **Der Plan-Entscheid 3 war die Schwachstelle.** Die Regel „ein unverändert zurückgeschickter Wert ist keine Änderung" war für die Inhaltsfelder sorgfältig gebaut und für den Status vergessen — begründet mit dem Wortlaut der AK statt mit dem Verhalten des aufrufenden Boards. Ein Reviewer hat es gefunden; die Asymmetrie wäre beim Schreiben zu sehen gewesen.
- **Zustand mehrfach nebenbei geändert** (Docker gestoppt, Branch gewechselt, `main` weitergelaufen, PR gemergt). Jedes Mal hat sich das Nachprüfen des Ist-Zustands gelohnt statt der Annahme.
- **Der Alembic-Drift** trifft jeden Branch, dessen Migrations-Head hinter der Dev-DB liegt. `main` in den Branch zu holen war der Weg, der die Datenbank des Nutzers in Ruhe lässt.
- **Manuelle AK-Prüfung ohne LLM-Kosten:** Testzeilen mit Marker direkt in die Dev-DB, danach gezielt gelöscht — statt `POST /quiz/generate` und einen echten Batch auszulösen.

## Offen geblieben

- **Last-write-wins beim PATCH.** Zwei Reviewer am selben Board überschreiben einander, kein optimistisches Locking. Ausserhalb des Scopes von #98, ohne Ticket.
- **Keine generische Prüfung „deklariertes Response-Schema passt zum echten Body"** über die ganze API. `tests/test_rbac.py` deckt Pfad und Auth ab, nicht die Schemas — die Fehlerklasse, die zum 422-Blocker führte, bleibt also offen.
- **Bereichsfilter** in beiden Lese-Endpoints, vertagt bis Konten ein `area`-Feld haben (in der Spec dokumentiert).
- **Für T-36 (#43):** die Lösung darf nicht vor der Antwort im DOM stehen, und die Client-Auswertung ist ein Entscheid, keine Zwangsläufigkeit.
