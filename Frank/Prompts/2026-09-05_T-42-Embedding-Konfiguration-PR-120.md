# Chatverlauf — T-42 Embedding-Konfiguration persistieren, fail-closed absichern (PR #120)

**Datum:** 2026-09-05 bis 2026-09-08
**Branch:** `feat/T-42-embedding-config-persistenz` (von `origin/main` abgezweigt)
**Gegenstand:** [Issue #68](https://github.com/tsorer/LearnFlow/issues/68) (T-42) — `EMBED_MODEL`/`EMBED_DIMENSIONS` waren reine Prozess-Settings, für Postgres unsichtbar: pgvector lehnt einen Vektor falscher *Länge* ab, nie ein falsches *Modell* derselben Länge. Umgesetzt: Migration `0018` (Seed + CHECK-Constraint), fail-closed Startup-Check in API und Worker, `apply_embedding_config.py` als manueller Reconcile-Pfad, Admin-API/Frontend-Anpassung, ADR-Korrekturen — plus zwei vollständige Review-Runden (12 bzw. 6 Befunde) mit Bewertung und Fixes.
**Ergebnis:** [PR #120](https://github.com/tsorer/LearnFlow/pull/120) offen, Backend-Suite (591 Tests) und Frontend-Suite (135 Tests) grün, drei neue/erweiterte e2e-Tests gegen den echten Stack grün. Beide automatisierten Reviews vollständig bearbeitet (10 von 12 bzw. alle 6 Befunde gefixt, committet, gepusht, im PR kommentiert). Wartet auf CI und Review durch eine zweite Person.

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich (sehr lange Pasten — insbesondere die beiden Review-Feedbacks — gekürzt, kenntlich gemacht), Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/68 (T-42)

### Claude

`gh issue view 68` zweimal versucht (kein Output, vermutlich Auth-/Netzwerkproblem im Sandbox-Kontext) — bevor eine Alternative nötig wurde, kam bereits die nächste Anweisung.

---

## 2 — Nutzer

> Leg direkt los mit Branch und Migration.

### Claude

`git status`/`fetch origin main` geprüft (sauber, main unverändert seit letztem Sync). Branch `feat/T-42-embedding-config-persistenz` von `origin/main` erstellt. Migration `0018_embedding_config.py` geschrieben: seedet `embed_model`/`embed_dimensions` (MVP-Defaults zu dem Zeitpunkt), erweitert die geteilte CHECK-Constraint aus `0009`/`0012`/`0014`/`0017` um zwei neue `WHEN`-Zweige — `embed_dimensions` mit einem reinen Regex-Bereich `1-2000` (bewusst kein `value::int <= 2000`, um die Auswertungsreihenfolge-Falle von `CASE`/Cast zu vermeiden, analog ADR-008 Nachtrag 2026-08-16), `embed_model` mit `\S` (nicht leer). Downgrade stellt die 0017-Constraint wieder her.

---

## 3 — Nutzer

> commit this, dann weiter mit Schritt 3

### Claude

Migration committet (`b62002a`). Für die Vergleichslogik `app/exceptions.py` um `EmbeddingConfigError` ergänzt (bewusst weder `UserFacingError` noch `ConfigurationError` — kein Request, den ein Abbruch beantwortet). Neues Modul `app/services/embedding_config.py`: `EmbeddingConfig`-Dataclass, `embedding_config_from()` (parst zwei `config`-Zeilen, fail-closed bei fehlender/kaputter Zeile), `verify_embedding_config()` (reiner Vergleich, wirft bei Abweichung). In `worker/main.py`: `verify_embedding_config_at_startup()` (raw asyncpg, gleicher Split wie `read_chunk_config`), Aufruf in `main()` vor der Queue-Manager-Initialisierung, mit `try/except EmbeddingConfigError: log.exception(...); raise`. In `app/main.py`: `lifespan`-Hook mit derselben Prüfung über eine SQLAlchemy-Session.

---

## 4 — Nutzer

> Ja, mach weiter mit dem Script.

### Claude

`apply_embedding_config.py` geschrieben: bei Dimensionswechsel `chunks.embedding`-Spalte + HNSW-Index neu anlegen, `config` aktualisieren, gesamten Korpus auf `pending` zurücksetzen (`index_version + 1`, `index_attempts = 0`), Chunks löschen, pro Dokument einen `process_document`-Job queuen. `ruff`/`mypy` sauber. Live gegen die Dev-DB getestet: No-op-Fall korrekt erkannt (`Bereits synchron ... Nichts zu tun.`).

Vor dem Test des eigentlichen Reconcile-Pfads per `AskUserQuestion` nachgefragt, weil das Script `DELETE FROM chunks` ausführt und der laufende Worker die neu gequeueten Jobs sofort mit echten OpenAI-Calls verarbeitet hätte (Kosten + Verlust der 206 vorhandenen Chunks). Nutzer wählte **nur gemockte Unit-Tests**. `tests/test_apply_embedding_config.py` geschrieben (Match/No-op, Modellwechsel ohne Dimensionsänderung, Dimensionswechsel inkl. DDL-Reihenfolge, Requeue-Zahl).

---

## 5 — Nutzer

> Ja, mach weiter mit Abschnitt 5 und auch gleich mit den restlichen Schritten

### Claude

**Admin-API/Frontend:** `app/routers/admin.py` — Kommentar ergänzt, warum `embed_model`/`embed_dimensions` nicht in `WRITABLE_KEYS` gehören (Dimensionswechsel bräuchte Schema-Änderung, die ein PUT nicht leisten kann). `tests/test_admin_config.py` um GET/PUT-Fälle erweitert (sichtbar, Änderung abgelehnt, unveränderter Pass-through akzeptiert). Frontend: `params.ts` — `READ_ONLY_PARAM_DEFS` um beide Schlüssel erweitert, veraltete Kommentarstelle korrigiert (fälschlich behauptet, T-42 mache `chunk_size` schreibbar). `admin-params.test.tsx` entsprechend erweitert. Frontend-QA per PowerShell im ephemeren `node:22-alpine`-Container (`npm ci && npm run lint && npm run check && npm run test`) — 135 Tests grün, committet.

**ADR-Korrekturen:** `Docs/04_ADR-003_Datenpersistenz.md` und `Docs/06_Architecture-Draft.md` beschrieben fälschlich eine separate `embeddings`-Tabelle statt `chunks.embedding` seit Migration `0003` — korrigiert. `Docs/04_ADR-005_Embedding-Modell.md` um einen Nachtrag (2026-09-05) ergänzt: konkrete Fail-closed-Entscheidung (harter Abbruch statt Auto-Reindex), `apply_embedding_config.py` als einziger Akzeptanzpfad. Committet.

**Abschluss:** Voller Backend-QA-Lauf (`ruff`, `mypy app worker`, `pytest`) grün. Status gegen Issue-Akzeptanzkriterien und Definition of Done zusammengefasst — offen nur Review durch eine zweite Person und der echte CI-Lauf. Gefragt, ob die 5 Commits vor dem Push gesquasht werden sollen.

---

## 6 — Nutzer

> bewerte folgendes Feedback:
>
> Correctness (high confidence)
> 1. Ops/07_Pilotstart-Checkliste.md:32 — der dokumentierte Recovery-Befehl `docker exec src-api-1 python apply_embedding_config.py` braucht einen laufenden Container, aber genau der Lifespan-Check crash-loopt diesen Container bei jeder Abweichung […]
> 2. apply_embedding_config.py:140 — der Requeue-Loop überspringt app/queue.py's Dedupe-Delete aufgrund einer falschen Prämisse […]
> 3. apply_embedding_config.py:152 — `configured` überspringt die [1,2000]-Grenzprüfung, die die persistierte Seite bekommt […]
> 4. 0018_embedding_config.py:152 — `downgrade()` stellt `chunks.embedding`s reale Breite nie wieder her […]
>
> *(gekürzt — insgesamt 12 Punkte: Test-Coverage-Lücke bei nur SQL-Text-Assertions, docker-compose-Race zwischen Worker und API, hartcodierter `Vector(1536)` im ORM-Modell, fehlendes Trimmen von `embed_model`, Migrations-Stil-Nitpick, fehlende Audit-Felder, `os.environ` statt `Settings.sqlalchemy_url`, fehlender e2e-Test für die CHECK-Constraint)*

### Claude

Jeden der 12 Punkte einzeln gegen den tatsächlichen Code verifiziert (nicht nur gelesen): `docker-compose.yml`s `api`-Command (`alembic upgrade head && uvicorn ...`), `app/queue.py::enqueue_document`s Dedupe-Logik, `app/models/tables.py`s `changed_by`/`changed_at`-Nullability, `tests/test_config_constraint_migration.py`s AST-Test, `seed_users.py`s DB-URL-Muster, `e2e/test_config_self_check_band.py`s Muster für echte-DB-Tests.

Ergebnis: **11 von 12 Punkte bestätigt**, nur #9 (Migrations-Stil) eher ein Nitpick, #11 (`os.environ`) sachlich richtig, aber deckungsgleich mit bestehender `seed_users.py`-Konvention. Dabei selbst eine zusätzliche Lücke gefunden: der statische Regressionswächter `test_the_latest_revision_keeps_every_validated_key` zeigte nach dem vorigen Umbenennen noch auf `0017` statt auf den neuen Head `0018`. Empfehlung: alles ausser #9/#11 fixen.

---

## 7 — Nutzer

> Ja, fix alle bis auf #9 und #11

### Claude

Drei Commits:

1. **`ebe3891`** — `docker-compose.yml`: `worker` hängt jetzt zusätzlich an `api: service_healthy` (sein neuer, eager laufender Startup-Check würde sonst gegen die noch nicht abgeschlossene Migration rennen). `Ops/07_Pilotstart-Checkliste.md` 2.2a: `docker compose run --rm api ...` statt `docker exec src-api-1 ...`, weil letzterer Befehl ins Leere greift, sobald der Container crash-loopt. `apply_embedding_config.py`: Dedupe-Delete gegen doppelte Jobs ergänzt, `configured` läuft jetzt durch denselben Parser (`embedding_config_from`) wie `persisted`, `changed_by`/`changed_at` werden bei der Config-UPDATE explizit gesetzt.
2. **`5959dea`** — `embed_model` wird getrimmt statt nur auf Nicht-Leerheit-nach-Trim geprüft; Downgrade/Upgrade-Drift-Limitation dokumentiert (Startup-Check vergleicht nur zwei *Behauptungen*, nie die reale Spaltenbreite); Warnhinweis an `Chunk.embedding` zu `alembic revision --autogenerate`.
3. **`da5989a`** — Tests: `bound()`-Helper für tatsächlich gebundene Werte statt nur SQL-Text; neuer `e2e/test_config_embedding_constraint.py` (13 Fälle, echtes Postgres, Transaktion+Rollback, nach dem Muster von `test_config_self_check_band.py`); `test_config_constraint_migration.py` auf `0018` als Head umgestellt.

Live verifiziert: `docker compose config -q` (Compose-Syntax gültig), Worker-Neustart mit neuer `depends_on`-Kette (startet sauber, wartet auf `api: healthy`), No-op-Lauf von `apply_embedding_config.py` gegen die Dev-DB, neuer e2e-Test gegen den echten Stack (13/13 grün), voller Backend-Suite-Lauf (591 Tests grün).

---

## 8 — Nutzer

> Squash zu einem Commit, dann pushen und PR eröffnen

### Claude

`git merge-base` mit `origin/main` geprüft (unverändert seit Branch-Erstellung), `git reset --soft` darauf, alle 8 Commits zu einem zusammengefasst (`5330e10`). Voller QA-Lauf (`ruff`, `mypy`, `pytest`) grün. `git push -u origin feat/T-42-embedding-config-persistenz`. `gh pr create` mit Zusammenfassung, Testplan und Hinweis auf die bereits erfolgte interne Review-Runde → [PR #120](https://github.com/tsorer/LearnFlow/pull/120).

---

*(Sitzungswechsel zwischen den Nachrichten — die nächste Anfrage kam in einer neuen Session, aktiver Branch inzwischen `feat/T-36-lara-quiz-ui`.)*

## 9 — Nutzer

> bewerte das Feedback auf github

### Claude

`gh pr list` zeigte vier offene PRs (#117 T-36, #118 T-52, #119 T-32, #120 T-42) mit fast zeitgleichen automatisierten Reviews (~13:08 Uhr) — #117s Feedback war bereits in einer früheren Session behoben und im PR bestätigt. Per `AskUserQuestion` nachgefragt, welches PR gemeint ist — Nutzer wählte **#120**.

Den vollen Review-Kommentar abgerufen (6 Punkte: verwaiste Quizfragen nach `DELETE FROM chunks`, Migration `0018` seedet MVP-Defaults statt der laufenden `Settings`, inkonsistente Normalisierung zwischen Startup-Checks und Script, README widerspricht Script/Checkliste, `os.environ` statt `settings.sqlalchemy_url`, Lücke in der Migrations-Constraint-Testabdeckung). Auf den Branch `feat/T-42-embedding-config-persistenz` gewechselt (T-36-Arbeitsverzeichnis war sauber bis auf unberührte, unversionierte Dateien) und jeden Punkt gegen den echten Code verifiziert — u. a. bestätigt, dass `app/routers/documents.py`s `_replace`-Pfad genau die Quiz-Reset-Logik enthält, die `apply_embedding_config.py` fehlte, und dass `alembic/env.py` bereits `app.config.settings` importiert (die "Migrationen importieren nie App-Code"-Annahme aus Runde 1 war an dieser Stelle falsch).

Alle 6 Punkte bestätigt und direkt gefixt (Commit `d61e24a`):

- `apply_embedding_config.py`: `UPDATE quiz_questions SET status='pending', approved_at=NULL WHERE status='approved'` nach dem `DELETE FROM chunks`, spiegelbildlich zu `documents.py`.
- Migration `0018`: `_rows()` liest jetzt `settings.embed_model`/`embed_dimensions` zur Laufzeit statt hartcodierter Literale; Docstring entsprechend umgeschrieben.
- `app/main.py` + `worker/main.py`: `configured` wird jetzt über `embedding_config_from()` gebaut, nicht mehr roh aus `Settings`.
- `src/README.md`: `docker compose run --rm api ...` statt `docker exec src-api-1 ...`.
- `apply_embedding_config.py`: `settings.sqlalchemy_url` statt `os.environ["DATABASE_URL"]`, Validierung vor Engine-Erstellung verschoben.
- `test_config_constraint_migration.py`: prüft jetzt auch `COUNT_KEYS`, nicht nur `UNIT_INTERVAL_KEYS`.

Live verifiziert: Downgrade/Upgrade-Zyklus mit `-e EMBED_MODEL=bge-m3 -e EMBED_DIMENSIONS=1024` bestätigte, dass die Migration jetzt tatsächlich den überschriebenen Wert seedet (nicht mehr den hartcodierten). Dabei hat `--reload` mitten im Zyklus einen inkonsistenten Zwischenzustand erwischt und den `api`-Container in `unhealthy` hängen lassen — per `docker compose restart api` behoben, Config auf die echten `.env`-Werte zurückgesetzt. Volle Suite (591 Tests) plus die drei Config-Constraint-e2e-Dateien erneut grün. Commit gepusht, Zusammenfassung als PR-Kommentar auf #120 hinterlassen, zurück auf `feat/T-36-lara-quiz-ui` gewechselt.

---

## 10 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Bestehende Exporte in `Frank/Prompts/` als Vorlage gelesen (zuletzt `2026-09-07_T-22-Performance-Test-PR-121.md`) und dieses Dokument nach der dort etablierten Konvention erstellt.
