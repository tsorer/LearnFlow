# Chatverlauf — T-15 Versionierung (gleicher Dateiname ersetzt Dokument), PR #87

**Datum:** 2026-08-24
**Branch:** `feat/T-15-document-versioning`, von `origin/main` abgezweigt, später auf `main` rebased und zu einem Commit gequetscht. Am Ende auf `main` gewechselt.
**Gegenstand:** Issue [#22](https://github.com/tsorer/LearnFlow/issues/22) „[T-15] Versionierung: gleicher Dateiname ersetzt Dokument" (US-04) — von der Planung bis zum reviewten PR.
**Ergebnis:** [PR #87](https://github.com/tsorer/LearnFlow/pull/87), vier Commits, Approve durch `luenlestra` mit sechs Punkten, alle adressiert. Nebenprodukte: Migration 0013 (Unique-Index), `DocumentStatus`-Enum, Versionsguard im Worker, Folge-Ticket [#92](https://github.com/tsorer/LearnFlow/issues/92), Notizen an [#69](https://github.com/tsorer/LearnFlow/issues/69) und [#40](https://github.com/tsorer/LearnFlow/issues/40).

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/22

### Claude

Issue, `Docs/01_UserStories.md` / `02_Requirements.md` (US-04), `openapi.yaml`, `app/routers/documents.py`, `worker/main.py`, `models/tables.py` und die vorhandenen Tests gelesen. Befund: `upload_document` legt immer eine neue Zeile an; `store_chunks` im Worker löscht bereits `chunks WHERE document_id`, Re-Indexierung derselben id ist also schon idempotent. Das Verhalten steht bereits in den Requirements — kein ADR-/Docs-Update nötig.

Plan mit fünf Entscheiden, je mit Empfehlung:

1. **UPDATE in place** statt Delete+Insert — die `id` bleibt für Frontend-Polling und referenzierende Zeilen stabil.
2. **Chunks sofort beim Upload löschen**, nicht erst beim Re-Indexieren (fail-closed im Sinne von ADR-008).
3. **`200` beim Ersetzen, `201` beim Neuanlegen** — Spec-Änderung, aber ehrlicher Vertrag; `unwrap` im Frontend ist statuscode-agnostisch.
4. Match auf **exaktes** `filename` + `area`, keine Normalisierung.
5. Reset von `status`, `chunk_count`, `error_message`, `validated_at`.

Bewusst ausserhalb: Unique-Index auf `(area, filename)` (bräuchte eine Migration, die Duplikate löscht), Versionshistorie, case-insensitives Matching. Benannt wurde ausserdem das Rennen „Ersetzung während ein Job schon `picked` ist" — mit dem Vorschlag, es als eigenes Issue zu führen. Rückfrage zu 200/201 und zu einem optionalen `updated_at` im Response.

---

## 2 — Nutzer

> Unterscheidung 200/201 finde ich gut. Bitte umsetzen

### Claude

Branch von `origin/main`. Spec zuerst: `200` neben `201` in `openapi.yaml`, Summary angepasst, `make generate-api` (über den Docker-Einzeiler, kein `make` auf dem Rechner), `schema.d.ts` mitcommittet.

Router: `_find_by_filename` (Lookup mit `FOR UPDATE` und `defer(content)`) und `_replace` (Chunk-Delete, Felder-Reset), beides mit `enqueue_document` in einer Transaktion. `app/queue.py` löscht zusätzlich einen noch `queued` liegenden Job desselben Dokuments — sonst embeddet der Worker dieselbe Datei zweimal.

Tests: `make_db()` in `test_documents.py` musste einen Default bekommen (`scalar_one_or_none() -> None`), sonst hätte jeder Upload-Test den Replace-Zweig genommen; dasselbe in `test_rbac.py`. Neu: Compiled-SQL-Tests für Filter und Chunk-Delete, e2e `test_documents_replace.py` gegen die echte DB. Der bestehende Cascade-e2e-Test lädt jetzt unter eindeutigem Dateinamen hoch — sonst hätte ein Rest aus einem abgebrochenen Lauf den nächsten auf `200` statt `201` laufen lassen.

Verifikation: `ruff`, `mypy`, 203 Unit-Tests, 22 e2e, 49 Frontend-Tests grün. Manuell im laufenden System: Upload → `available` mit 1 Chunk → gleicher Name → `200`, gleiche id, Chunks sofort 0 → neu indexiert mit neuem Inhalt.

`updated_at` bewusst weggelassen (nicht bestätigt), das Restrisiko der `picked`-Race erneut benannt.

---

## 3 — Nutzer

> bitte updated_at ergänzen

### Claude

`updated_at` als Pflichtfeld in `DocumentResponse`, beide Zeitstempel in der Spec beschrieben (`created_at` = erster Upload und überlebt die Ersetzung, `updated_at` = aktuelle Fassung). Beide werden im Router **explizit** gesetzt: die Session läuft mit `expire_on_commit=False`, ein serverseitig gefüllter Wert wäre in der Antwort `None` (Insert) bzw. veraltet (Update).

Frontend-Typen neu generiert, `doc()`-Helper in `upload.test.tsx` ergänzt. Manuell geprüft: `created unveraendert: True | updated neuer: True`.

Hinweis: die Upload-UI zeigt gar keinen Zeitstempel an — das Feld steht bereit, angezeigt wird es erst auf Wunsch (T-16-Gebiet).

---

## 4 — Nutzer

> pausiere die e2e-Tests bis wir alle Punkte von diesem Issue umgesetzt haben. Nächste Punkt: in @src/backend/e2e/test_documents_replace.py sind Benutzername/Passwort in Klartext. Ist es in den anderen Tests auch schon so? Passwörter gehören meiner Meinung nach nicht in GIT

### Claude

Ja, das Muster ist älter: `seed_users.py` (alle sechs Accounts), `src/README.md` (Login-Tabelle), `test_login_flow.py`, `test_documents_cascade.py`. Einordnung: bewusste Wegwerf-Platzhalter für den lokalen Stack, `Ops/07_Pilotstart-Checkliste.md` Punkt 1.7 verlangt ihren Ersatz vor dem Pilotstart. Aber: das Repo ist öffentlich, und praktisch relevanter — sobald 1.7 umgesetzt ist, laufen die e2e-Tests gegen keine Umgebung mehr ausser einem frisch geseedeten Stack.

Drei Optionen zur Auswahl gestellt (nur e2e entkoppeln / alles inklusive `seed_users.py` und CI / nur Issue).

---

## 5 — Nutzer (Antwort auf die Rückfrage)

> passe erstmal nur den Test an

### Claude

Statt einer Kopie des Passworts liest das Modul die Zugangsdaten aus `seed_users.py` — dieselbe Quelle, die `tests/test_seed_users.py` bereits importiert; `E2E_OWNER_EMAIL` / `E2E_OWNER_PASSWORD` haben Vorrang. Damit kein Klartext mehr in der Datei und trotzdem kein Setup nötig.

Nebenbei korrigiert: der Kommentar zum Rate-Limit-Budget. Der Limiter keyt auf die Client-IP, ein anderer Benutzer spart also nichts — was zählt, ist ein Login pro Modul.

Verifiziert ohne e2e-Lauf (pausiert): `ruff` grün, Modul importiert sauber, Passwort löst auf den Seed-Wert auf.

---

## 6 — Nutzer

> passe die beiden anderen Tests auch an. Weiterer Punkt: in @src/backend/app/routers/documents.py schreibst du direkt document.status = "pending". Sollte nicht irgendwo die Liste definiert sein und hier ein Parameter statt des Strings verwendet werden?

### Claude

Beide Module umgestellt, `changeme` verschwindet damit ganz aus `e2e/`.

Zur Status-Frage: die Liste existiert — aber nur in der Spec (`DocumentStatus: [pending, processing, available, failed]`), auf der Python-Seite standen die Werte als Literale an jeder Schreibstelle. Dass das nicht Kosmetik ist, zeigt Migration 0006: der Spaltendefault stand einmal auf `queued`, einem Wert, den die Spec nicht kennt, und niemand hat es bemerkt.

Umgesetzt nach dem Muster von `UserRole`: `DocumentStatus(str, Enum)` in `models/tables.py`, auch als `server_default`; Router schreibt Enum-Member; `test_openapi_spec.py` schlägt fehl, sobald Spec und Enum auseinanderlaufen. Bewusste Grenzen: `DocumentResponse.status` bleibt vorerst `str` (als Enum typisiert würde eine kaputte Zeile die ganze Liste mit 500 abbrechen), Worker- und Retrieval-SQL bleiben unangetastet. Gegen echtes Postgres geprüft: `JSON-status: 'pending' | DB-status: 'pending'`.

---

## 7 — Nutzer

> zurück zu dem Punkt hier: Das Restrisiko von vorhin steht unverändert: eine Ersetzung, während der Job der Vorversion schon picked ist, kann deren Chunks nachträglich schreiben. Kannst du das nicht auch gleich hier beheben? Wieso wäre ein Folge-Issue besser?

### Claude

Eingeräumt, dass das Argument fürs Folge-Issue (Scope-Hygiene) schwächer ist als der Punkt dagegen: **die Lücke entsteht erst durch T-15** — vor dieser Änderung wurde für ein Dokument nie ein zweiter Job eingereiht. Ein Issue dafür hiesse, ein selbst gegrabenes Loch zu dokumentieren. Also eingebaut.

Mechanik: `documents.updated_at` als Versions-Token, im selben Statement wie der Inhalt gelesen; `mark_available` veröffentlicht nur `WHERE id = $1 AND updated_at = $3`. Trifft das nichts, fliegt `Superseded` **innerhalb** der Transaktion, deren Abwicklung die eben geschriebenen Chunks verwirft. Dieselbe Bedingung am Fehlerpfad.

Drei neue Worker-Tests, darunter einer, der auf dem `__aexit__`-Argument der Transaktion besteht — sonst wäre er auch grün, wenn die Ausnahme nie fliegt. Gegen die echte DB: `ohne Ersetzung: ('available', 1, ['Erste Fassung A.'])` / `mit Ersetzung: ('pending', 0, [])`.

---

## 8 — Nutzer

> setze die beiden Punkte für DocumentResponse.status und Status-Literale um

### Claude

`DocumentResponse.status` ist jetzt `DocumentStatus`; die Umwandlung sitzt sichtbar in `_to_response`. Worker (drei Writes) und Retrieval-Filter binden den Status als Parameter statt ihn in den SQL-Text zu schreiben. Damit steht die Liste nur noch in `models/tables.py`.

Gegen echtes Postgres geprüft, weil hier drei Dinge passieren, die kein Mock zeigt (asyncpg-Kodierung eines str-Enums, JSON-Serialisierung, gebundener Filter im HNSW-Query): Upload `201 'pending'` → Worker `'available'`, 1 Chunk → Retrieval `20 dense / 10 sparse`, eigenes Dokument gefunden.

---

## 9 — Nutzer

> e2e wieder freigeben, alles laufen lassen

### Claude

`alembic current` = `0012 (head)`, `seed_users.py` durchlaufen, dann alles: `ruff`, `mypy`, 207 Unit-Tests, 22 e2e, 49 Frontend-Tests — grün. Stand gegen die drei Akzeptanzkriterien zusammengefasst; offen aus der DoD nur das Review durch eine zweite Person.

---

## 10 — Nutzer

> mittlerweile hat sich einiges in GIT getan. Mach ein squash und ein rebase an den main. Bereinige die Dokumente in der DB, damit unique funktioniert. Es gibt momentan noch keine produktiven Daten. Klartext-Passwörter in seed_users und in der readme sind akzeptabel.

### Claude

Rebase auf `origin/main` (zwei neue Commits, T-18) lief konfliktfrei; weil `openapi.yaml` und die generierte `schema.d.ts` von beiden Seiten angefasst wurden, Typen danach neu generiert und auf Drift geprüft — kein Diff.

**Migration 0013:** löscht zuerst die älteren Duplikate je `(area, filename)` (`(older.updated_at, older.id) < (newer.updated_at, newer.id)`, Chunks folgen per Cascade), dann Unique-Index. In der Dev-DB gab es keine Duplikate. Datenverlust-Warnung steht im Docstring. Index auch im Modell deklariert; `_find_by_filename` braucht kein `ORDER BY … LIMIT 1` mehr. Neuer e2e-Test lässt einen zweiten Direkt-Insert in eine `UniqueViolationError` laufen.

Danach `reset --soft origin/main`: ein Commit. Läufe: `ruff`, `mypy`, 233 Unit, 23 e2e, 49 Frontend.

---

## 11 — Nutzer

> bitte pushen und den pr erstellen

### Claude

Branch gepusht, [PR #87](https://github.com/tsorer/LearnFlow/pull/87) erstellt (Titel mit Branchnamen prefixed, `Schliesst #22`, Akzeptanzkriterien einzeln abgehakt, zwei bewusst offene Punkte benannt: 500 statt 409 bei gleichzeitigem Erst-Upload, case-sensitives Matching).

---

## 12 — Nutzer

> schau dir das Feedback auf GIT an. Das Thema hatte wir schon mal besprochen, oder?

### Claude

Review von `tsorer` mit zwei Punkten. Antwort: **Punkt 2 ja** — das ist die Kopplung, die beim Bau des Guards benannt wurde (`updated_at` trägt nur, solange ausser der Route niemand es schreibt); der Kommentar stand nur im Worker, wo kein ORM-Schreiber nachliest, und wanderte an die Spalte.

**Punkt 1 war neu und ein echtes Loch:** `prepare_chunks` las `updated_at` im `SELECT`, gab es aber erst per `return` heraus — scheiterte es dazwischen, blieb `version` `None`, und die `IS NULL`-Klausel machte daraus ein Update per id **ohne** Versionsprüfung. Behoben: Lesen als eigener Schritt (`fetch_document`), `IS NULL` ersatzlos gestrichen. Test über die Fehlerstelle parametrisiert. Gegen die echte DB nachgestellt: die frisch indexierte Fassung bleibt `available`.

Nebenbefund: der Arbeitsbaum stand zwischenzeitlich auf `feat/T-23-…` — zurückgewechselt.

---

## 13 — Nutzer

> wird im Frontend sichergestellt, dass nur eine Datei (bzw. eine Datei mit den gleichen Namen) pro Benutzer auf einmal hochgeladen wird. Ich halte es für sehr unwahrscheinlich, dass absichtlich zweimal die gleiche Datei hochgeladen werden soll

### Claude

Nachgesehen: das Frontend serialisiert bereits an drei Stellen — `for … await` über die Dateien, `disabled={uploading}` am Picker, und ein Drop während des Uploads wird mit Meldung abgewiesen (beides getestet). Aus einem Tab ist nie mehr als ein Request unterwegs.

Der kritische Fall ist ausserdem nicht der vermutete: zwei Dateien gleichen Namens in einem Drop laufen nacheinander — `201`, dann `200`, also genau das Feature. Der 500er braucht zwei echt gleichzeitige Requests (zwei Tabs, zwei Verantwortliche, API-Aufruf an der SPA vorbei). Einschätzung deckt sich: der 409 lohnt nicht.

---

## 14 — Nutzer

> pushe den Fix als eigenen Commit und poste die Antwort.

### Claude

`63aee8e` gepusht (eigener Commit statt Force-Push, damit das Delta zum Review sichtbar bleibt), Antwort als [PR-Kommentar](https://github.com/tsorer/LearnFlow/pull/87#issuecomment-5381302936) gepostet.

---

## 15 — Nutzer

> gibt es nicht schon ein Issue für US-08, wo man die Versionsspalte ergänze könnte, so dass es kein eigenes Ticket braucht?

### Claude

Zwei Korrekturen. **US-08 ist die falsche Story** — das ist „Quiz absolvieren"; die Re-Validierung ist **US-06** und laut Entscheid vom 2026-06-04 post-MVP. Die falsche Nummer stand im Spaltenkommentar und in der PR-Antwort.

**Der passende offene Issue existiert:** [#69](https://github.com/tsorer/LearnFlow/issues/69) (T-43, Worker-Reaper). Der schreibt per Definition auf `documents`-Zeilen, und sein viertes AK lautet „Ein Dokument, das gerade regulär verarbeitet wird, wird nicht angefasst" — dieselbe Invariante von der anderen Seite. Kein eigenes Ticket nötig.

---

## 16 — Nutzer

> alle drei bitte

### Claude

`06dea89` gepusht (richtige Story-Nummern, Spaltenkommentar zeigt auf T-43), [Kommentar an #69](https://github.com/tsorer/LearnFlow/issues/69#issuecomment-5381366865) mit den drei Umsetzungsoptionen (rohes SQL, `updated_at` explizit halten, eigene Versionsspalte), [Korrektur am PR](https://github.com/tsorer/LearnFlow/pull/87#issuecomment-5381368110).

---

## 17 — Nutzer

> bewerte das neue Feedback vom PR

### Claude

Approve von `luenlestra` mit sechs Punkten. Alle am Code nachgeprüft; fünf treffen zu, bei einem Widerspruch zur vorgeschlagenen Richtung:

1. **`created_at` vs. `uploaded_by`** — Beobachtung richtig, Lösung andersherum vorgeschlagen: die Zeile beschreibt durchgehend die aktuelle Fassung, `created_at` ist die dokumentierte Ausnahme. Ein Rückbau kostet die Antwort auf „wer hat den Text eingestellt, der jetzt drinsteht".
2. **Invariante nur als Kommentar** — halb erledigt (Notiz an #69 stand schon); zusätzlich möglich: ein Test, der die Worker-Seite festnagelt.
3. **Jeder knowledge_owner überschreibt fremde Dokumente** — stimmt, folgt aus dem einen `PILOT_AREA`; und `unwrap` verwirft den Statuscode, die UI *kann* eine Ersetzung nicht anzeigen.
4. **`status = 'processing'` ohne Versionsbedingung** — richtig gesehen; Vorschlag: reparieren statt begründen (Lesen vorziehen, Bedingung anhängen), spart zusätzlich einen Provider-Durchlauf.
5. **Radius von `DocumentStatus(...)`** — stimmt, ist bewusst, steht nicht dran.
6. **`quiz_questions` überleben** — stimmt und widerspricht dem eigenen Docstring; trotzdem nicht hier löschen, die Semantik gehört zu T-33.

Dazu die Schlussbemerkung des Reviewers: AK 3 ist e2e nicht belegt (Dummy-Key in der CI) — korrekt.

---

## 18 — Nutzer

> Punkt 1: Kommentieren. Den Rest die vorgeschlagen umsetzen.

### Claude

Zwischendurch hing die API in einer Restart-Schleife: die Dev-DB stand auf Revision `0014` aus `feat/T-23-…`. Fremde Migration temporär hereingeholt, API gestoppt (sie hatte per `upgrade head` sofort zurück-migriert), auf `0013` heruntergefahren, Datei entfernt, API gestartet.

Code (`1138755`): Kommentar zu `uploaded_by`; Test, dass keine `UPDATE documents`-Anweisung im Worker `updated_at` in ihrer `SET`-Klausel hat; `mark_processing` mit Versionsbedingung nach dem Lesen — ein überholter Lauf steigt jetzt **vor** dem Embedding aus (`chunks: 0 | Embedding-Aufrufe: 0` gegen die echte DB); Halbsatz zum Radius; Kommentar zu `quiz_questions`.

Drumherum: PR-Text um die Pilot-Entscheidung und die AK-3-Fussnote ergänzt, [#92](https://github.com/tsorer/LearnFlow/issues/92) angelegt (Upload-Rückfrage), [Notiz an #40](https://github.com/tsorer/LearnFlow/issues/40#issuecomment-5397283152), [Antwort im PR](https://github.com/tsorer/LearnFlow/pull/87#issuecomment-5397294372).

Läufe: `ruff`, `mypy`, 238 Unit-Tests, 23 e2e grün; CI `e2e` und `frontend` grün, `backend` noch laufend.

---

## 19 — Nutzer

> bitte wieder zum main wechseln und diesen Chatverlauf nach Frank/Prompts exportieren

### Claude

Auf `main` gewechselt (die T-15-Arbeit liegt auf dem Branch und im PR), dieser Export geschrieben.

---

## Was aus dieser Sitzung hängen bleibt

- **Ein Loch, das die eigene Änderung erst erzeugt, gehört in denselben PR.** Zweimal in dieser Sitzung: erst die `picked`-Race, dann die Lücke im Fehlerpfad, die der Review fand.
- **Ein Guard, der auf einer Verabredung beruht, braucht einen Ort, an dem der nächste Schreiber ihn findet** — nicht den Docstring der Funktion, die ihn nutzt, sondern die Spalte und das Ticket, das sie anfassen wird.
- **Die Dev-DB driftet, sobald jemand den Branch wechselt.** Beim Wechsel zurück auf `feat/T-23-…` ist dort einmal `alembic upgrade head` fällig.
- **Mocks können eine Änderung stillschweigend überstehen.** `make_db()` und `make_active_user_db()` hätten den neuen Lookup als „Dokument existiert" gelesen und Tests grün gehalten, die nichts mehr prüfen.
