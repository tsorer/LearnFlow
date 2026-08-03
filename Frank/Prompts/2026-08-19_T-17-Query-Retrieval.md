# Chatverlauf — Umsetzung T-17 (POST /query, Hybrid-Retrieval)

**Datum:** 2026-08-15 (Planung, Umsetzung, Commit) / 2026-08-18–19 (Review-Nachgang, Rebase)
**Branch:** `feat/T-17-query-retrieval` → [PR #80](https://github.com/tsorer/LearnFlow/pull/80)
**Gegenstand:** [Issue #24](https://github.com/tsorer/LearnFlow/issues/24) „[T-17] FastAPI: POST /query (Retrieval)"
**Nebenprodukt:** [Issue #79](https://github.com/tsorer/LearnFlow/issues/79) „[T-45] Rate-Limit für POST /api/query"
**Ergebnis:** ein Commit `abf2a6c` (mehrfach umgeschrieben: Squash, dann Rebase auf `main` nach Review)

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen. Entscheidungen aus den Rückfrage-Dialogen sind als Tabellen wiedergegeben.

---

## 1 — Nutzer

> Erstelle einen Plan für die Umsetzung von https://github.com/tsorer/LearnFlow/issues/24 (T-17)

### Claude

*(Plan-Modus — keine Änderungen ausser der Plan-Datei.)*

**Bestandsaufnahme** über zwei parallele Explore-Agenten: Issue #24 via `gh`, der `501`-Platzhalter in `app/routers/query.py`, `embed_texts()` aus T-13, das Chunk-Schema aus Migration `0003` (pgvector `vector(1536)` + HNSW `vector_cosine_ops`, `tsv` + GIN), das async-SQLAlchemy-Setup, die `config`-Tabelle, der `/query`-Vertrag in `openapi.yaml` und die Testmuster.

Befund:

- Die gesamte Infrastruktur steht bereits — `chunks.embedding` **und** `chunks.tsv` werden vom Worker beim Ingest befüllt, die Retrieval-Parameter sind in `0004` geseedet. Es fehlt ausschliesslich die Abfrageseite.
- `QueryResponse` verlangt `answer_id` als Pflichtfeld, und `feedback.answer_id` zeigt darauf → eine Antwort ohne persistierte Zeile wäre für das Feedback wertlos.
- `Niklaus/TechSpike` enthält eine Referenzimplementierung, ist aber laut CLAUDE.md ausdrücklich keine Quelle der Wahrheit (dort z. B. `top_k` als env-Key statt aus der `config`-Tabelle).

**Entscheidungen (Rückfrage-Runde):**

| Frage | Entscheid |
|---|---|
| Antwortmodus zwischen T-17 und T-18 — im Issue ausdrücklich offen gelassen | **`200` mit `suppressed: true`** — mit fortbestehendem `501` wären die AK „folgt dem `QueryResponse`-Schema" und „Platzhalter ist ersetzt" beide unerfüllbar |
| Retrieval-Umfang: AK nennen wörtlich nur Dense/HNSW, ADR-007 verlangt Hybrid | **Hybrid komplett** (Dense + Sparse + RRF) — `tsv`-Spalte und GIN-Index existieren und werden befüllt; Dense-only liesse sie ungenutzt |
| ADR-008 Stufe 1 (Retrieval-Konfidenz) mitnehmen? | **Ja** — `confidence.retrieval_score` ist Pflichtfeld der `ConfidenceInfo`, beide Gates sind LLM-frei und isoliert testbar |

Beim Schreiben des Plans fiel ein **Widerspruch im Vertrag** auf: die `QueryResponse`-Beschreibung sagt „bei `suppressed` bleibt `citations` leer", ADR-008 sieht dagegen ausdrücklich „Weiss ich nicht (+ optional nächstliegende Quellen)" vor. Als Spec-Anpassung in den Plan aufgenommen und dem Nutzer explizit zur Abnahme vorgelegt.

---

## 2 — Nutzer

> setze es bis zum Punkt Verifikation in einem eigenen Worktree um, da parallel bereits eine andere Coding-Session läuft.

### Claude

Worktree `feat/T-17-query-retrieval` angelegt. Dabei aufgefallen: die Worktree-Basis ist `origin/main`, wo T-44 noch nicht gemergt war — `app/exceptions.py` und damit `UserFacingError` existierten dort nicht. Statt eine konkurrierende Exception-Klasse einzuführen, wurde die Fehlerbehandlung auf ein generisches `503` ohne Provider-Details umgestellt; das vermeidet zugleich einen Merge-Konflikt mit T-44.

Umgesetzt in der Reihenfolge Spec → Code → Tests:

1. **`openapi.yaml`** — `501` entfernt, `503` ergänzt (Provider-/DB-Ausfall ist Infrastruktur, keine Unterdrückung), `QueryResponse`-Beschreibung an ADR-008 angeglichen. Spec-Diff vor der Implementierung gezeigt.
2. **`app/services/config.py`** — `PipelineConfig` + `read_pipeline_config()` nach dem Vorbild von `read_confidence_thresholds` (uncached pro Request, Modul-Defaults als Fallback).
3. **`app/services/retrieval.py`** — Dense-SQL (kein Threshold im `WHERE`, damit HNSW den Index bedient und das Limit nicht von einem Post-Filter angefressen wird), Sparse-SQL (selektiert dieselbe Cosine-Similarity mit, damit auch ein reiner Volltext-Treffer einen Score fürs Gate hat), RRF-Fusion mit Similarity-Tie-Break. Bewusst **sequenziell** statt `asyncio.gather`: eine `AsyncSession` hält eine asyncpg-Verbindung, und asyncpg verbietet nebenläufige Operationen darauf.
4. **`app/services/confidence.py`** — Stufe 0 und Stufe 1, rein synchron ohne DB und LLM.
5. **`app/routers/query.py`** — `501` ersetzt, Session/Answer-Persistenz, `debug` nur für Rolle `admin`.

---

## 3 — Nutzer

> der Rest kann nun umgesetzt werden

### Claude

`make qa` liess sich nicht unverändert nutzen: `qa-be` läuft über `docker exec src-api-1`, und dieser Container bedient die Hauptarbeitskopie, nicht den Worktree. Backend-QA daher über einen Wegwerf-Container gegen den Worktree, Frontend-QA über das ohnehin verzeichnisrelative `qa-fe`.

Für den manuellen Durchlauf war eine Entscheidung nötig, weil beide Wege Nebenwirkungen haben:

| Frage | Entscheid |
|---|---|
| Isolierter Zweit-Stack, geteilten Stack übernehmen, oder selbst durchspielen? | **Geteilten Stack übernehmen** — die parallele Session arbeitet danach gegen den T-17-Code |

Dazu musste `Src/.env` in den Worktree kopiert werden (`env_file:` löst relativ zum Compose-File auf; gitignored, nicht committet). Der Backend-Code ist per Bind-Mount eingebunden, der Stack lief nach dem Neustart also direkt gegen den Worktree.

Bemerkenswert im Ausgangszustand: die 6 vorhandenen Chunks der Dev-DB hatten **0 Embeddings** — für den Positivfall musste ein Dokument frisch indexiert werden (SKOS-Richtlinien, 200 Chunks).

**Manueller Durchlauf:**

| Szenario | Ergebnis |
|---|---|
| learner, In-Corpus | `generation_not_implemented`, 5 Quellen mit Seitenzahl, `retrieval_score` 0.7586 |
| learner, Out-of-Corpus | `retrieval_gate`, 0 Quellen, Score 0.2063 |
| learner vs. admin | `debug` null bzw. gefüllt, Stufen + Formel sichtbar |
| `similarity_threshold` auf 0.9 | Gate blockt, Stufe 1 als `ran=false` markiert |
| Reset auf 0.35 | Verhalten sofort zurück, ohne Restart |
| Persistenz | `query_sessions` + `answers` geschrieben, `answer_text` überall `None` |

Als Beobachtung berichtet: die Sparse-Suche liefert wegen der OR-Verknüpfung bei praktisch jeder deutschen Frage volle 20 Treffer, auch out-of-corpus — gewollt, weil Fusion sortiert und das Gate filtert, aber `sparse_count` ist für sich genommen kein Qualitätssignal.

---

## 4 — Nutzer

> erstelle einen Branch und committe es dort

### Claude

Der Branch existierte bereits und war im Worktree ausgecheckt — statt einen zweiten anzulegen wurde das benannt und auf den bestehenden committet (`0b84b7d`, 10 Dateien). Vor dem Commit wurden alle Dateien gelesen, auch die nicht in diesem Kontext geschriebenen; `.env` war nicht im Staging.

---

## 5 — Nutzer

> wechsel auch zum branch T-17, es braucht keinen geteilten Docker-Stack mehr, das SKOS-Dokument kann in der DB bleiben

### Claude

`ExitWorktree` mit `remove` hätte **auch den Branch gelöscht** — und damit den Commit. Stattdessen: Stack gestoppt (`docker compose down` ohne `-v`, damit `learnflow_pgdata` und das SKOS-Dokument bleiben), Worktree mit `keep` verlassen, Verzeichnis separat über `git worktree remove` entfernt (lässt den Branch stehen), dann in der Hauptarbeitskopie ausgecheckt und der Stack von dort neu gestartet.

---

## 6 — Nutzer

> der pre-Review hat folgende Punkte aufgedeckt. Bitte bewerten:
> *(sechs Findings zu Gate-Position, Debug-Text, fehlendem Clamp, fehlendem `422`, toten Verweisen und der undokumentierten Vorentscheidung, dazu vier Kleinigkeiten)*

### Claude

Alle Zeilenangaben nachgeprüft, alle sechs Punkte als berechtigt bestätigt — **mit einem Widerspruch zur vorgeschlagenen Richtung bei Punkt 1**:

> „Gate auf `outcome.candidates`" wäre die schlechtere Variante. Läge ein einziger Chunk über Schwelle auf RRF-Rang 22, passierte das Gate — und T-18 bekäme anschliessend die Ränge 1–5 als Kontext, in denen kein einziger Chunk über Schwelle ist. Das Gate hätte einen Kontext freigegeben, den es nie angeschaut hat.

Vorschlag: Verhalten behalten, ADR-007 präzisieren, die buchstabengetreue Alternative als Kalibrierfrage für den Eval-Spike vermerken.

Punkt 3 (fehlende Bereichsprüfung) wurde **höher gehängt als im Review**: der Modul-Docstring von `config.py` verspricht wörtlich, dass ein unlesbarer Wert die Pipeline nie auf eine ungeschützte Schwelle fallen lässt — `similarity_threshold = "-1"` tat genau das, und `_as_float` bediente auch die Konfidenzbänder.

Ebenso höher gewichtet als im Review: der fehlende Postgres-Integrationstest. `DENSE_SQL`/`SPARSE_SQL` liefen in der CI nur gegen `AsyncMock`; ein Tippfehler im Vektor-Cast wäre grün durchgekommen.

---

## 7 — Nutzer

> T-44 ist nun im main. Ich hab ein Rebase gemacht und der aktuelle Branch ist wieder der T-17. Deinen Vorschlag kannst du so umsetzen.

### Claude

Alle Punkte umgesetzt:

| Punkt | Umsetzung |
|---|---|
| 1 Gate-Position | Verhalten bleibt, Präzisierung in `Docs/04_ADR-007` inkl. Alternative |
| 2 Debug-Text | zählt Kontext-Chunks, Kandidatenzahl in Klammern |
| 3 Clamp | `_as_float` verwirft ausserhalb `[0,1]`, greift auch für die Konfidenzbänder |
| 4 `422` | in der Spec, Typen regeneriert |
| 5 Verweise | drei Spec-Beschreibungen, `CLAUDE.md`, `test_rbac.py` umgehängt |
| Kommentar | „Dense last so that it wins" statt der irreführenden Formulierung |
| e2e-SQL-Test | `e2e/test_retrieval_sql.py`, zwei orthogonale handgebaute Vektoren |

Der e2e-Test scheiterte im ersten Anlauf an einer geschlossenen Event-Loop: `app.database.engine` entsteht beim Import, pytest-asyncio gibt aber jedem Test eine frische Loop. Gelöst über eine Fixture, die den Pool nach jedem Test verwirft — sonst wären die Tests reihenfolgeabhängig gewesen.

Commit `49d6aea`. Backend 172 Tests, e2e 10, Frontend 22 — grün.

---

## 8 — Nutzer

> ja, erstell das Rate-Limit-Issue

### Claude

[Issue #79](https://github.com/tsorer/LearnFlow/issues/79) („[T-45] Rate-Limit für POST /api/query") nach dem Repo-Template angelegt, Label `backend`, abhängig von T-17. Die Frage IP vs. User bewusst als offene Frage stehen gelassen statt selbst entschieden.

---

## 9 — Nutzer

> die offene Frage habe ich in GIT wieder gelöscht. Es muss pro IP-Adresse sein, da man sonst zu einfach Benutzer aussperren kann. (Haben wir schon mal ausdiskutiert). Mach ein Squash-Push und erstelle dann den PR in GIT

### Claude

Entscheid als Projekt-Memory festgehalten, damit er nicht erneut aufgemacht wird. Squash der zwei Commits auf `origin/main` (`4ce9543`), Inhalt per `git diff` als bitidentisch zum Vorzustand nachgewiesen, Push mit `--force-with-lease`.

**Nicht erledigt:** der PR wurde nicht angelegt. Nach dem Schreiben des PR-Textes brach der Turn ab, und auf „Continue from where you left off" kam keine Fortsetzung. Der Nutzer hat [PR #80](https://github.com/tsorer/LearnFlow/pull/80) selbst eröffnet.

---

## 10 — Nutzer

> Review wurde macht.

### Claude

Review von `luenlestra`: `CHANGES_REQUESTED`, zwei Blocker — beide entstanden durch den Fortschritt auf `main`, nicht durch den PR selbst.

**Blocker 1 — Config-Semantik.** `main` hatte inzwischen #82 gemergt: ADR-008 Nachtrag 2026-08-16 dreht die Regel um — *fehlende Zeile → Default, vorhandene kaputte Zeile → `ConfigurationError`*. Der PR führte sechs neue `config`-Keys mit der alten Fallback-Semantik ein, und ein Test zementierte sie sogar für die Konfidenzbänder.

Aufgelöst:

- Die drei Ratios über `_as_threshold`, für die drei Zähler ein eigenes `_as_count` — anderer gültiger Bereich (`>= 1` statt `[0, 1]`), gleiche Fail-closed-Regel.
- **Migration `0012`** statt der vom Review vorgeschlagenen Änderung an `0009`: `0009` ist auf jeder bestehenden Datenbank bereits gelaufen, eine Bearbeitung würde dort nie greifen. `0012` droppt die Constraint und legt sie mit erweitertem `CASE` neu an.
- `create_query` liest die Config nach `_resolve_session` und innerhalb eines `try`; `ConfigurationError` wird zur unterdrückten Antwort mit `confidence: null`, kein 500er.

Am laufenden Stack gegengeprüft — beide Fälle werden von der DB abgewiesen:

```
UPDATE config SET value='0,90' WHERE key='similarity_threshold';
ERROR:  new row for relation "config" violates check constraint "ck_config_confidence_threshold_value"
UPDATE config SET value='0' WHERE key='retrieval_top_k';
ERROR:  new row for relation "config" violates check constraint "ck_config_confidence_threshold_value"
```

**Blocker 2 — `suppression_reason`.** Das Frontend kannte die drei gesendeten Werte nicht und zeigte „⚠ retrieval_gate" statt deutschem Text. Dem Reviewer-Vorschlag gefolgt: `enum` in `openapi.yaml`, `Message.suppression_reason` daraus abgeleitet, `suppressLabels` als `Record<SuppressionReason, string>` — T-18s neue Gründe brechen den Type-Check statt still den Schlüssel anzuzeigen.

**Substanziell:**

- tsquery-Cap schnitt vor der Stoppwort-Entfernung; deutsche Fragen laden vorne Funktionswörter auf, und „Sozialhilfe" fiel aus dem Beispielsatz. Stoppwortliste vor den Slice gezogen. Beim Umsetzen fehlte `das` in der ersten Liste — der neue Test hat es gefangen.
- `refinement_hint`: `TODO (T-26)` mit Verweis auf `Requirements §71`.
- `422`: eigenes `ValidationError`-Schema, weil FastAPI dort `detail` als Liste liefert; der handgeworfene 422 auf `/api/admin/config` bleibt bei `Error`.
- `except Exception`: `TypeError`, `AttributeError`, `NameError`, `ImportError` werden vorher durchgereicht, damit ein Bug nicht wie ein Provider-Ausfall aussieht.
- `re.UNICODE` entfernt, `ef_search`-Verhalten als Kommentar an `DENSE_SQL`.

**DoD „Eval-Gate":** nicht abgehakt, sondern begründet als nicht erfüllbar — T-28 (#35) ist offen, es gibt keinen Runner, und `expected_source_id` im Gold-Dataset steht durchgängig auf `TBD`.

Nebenbei: Docker Desktop war mitten im Durchlauf gestoppt und musste neu gestartet werden.

Commit `abf2a6c`, force-gepusht. Nach dem Rebase: Backend **197** Tests, Frontend **49**, e2e **21** — grün, `alembic upgrade head` bis `0012` durch. Antwort ans Review als PR-Kommentar.

---

## 11 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Dieses Dokument.

---

## Was aus dem Verlauf hängen bleibt

- **Der Vertrag war zweimal die eigentliche Arbeit.** Erst der Widerspruch zwischen `QueryResponse`-Beschreibung und ADR-008 (Punkt 1 der Planung), dann das fehlende `enum` für `suppression_reason` — beide Male hätte „nur implementieren" ein Frontend hinterlassen, das technische Schlüssel anzeigt oder leere Quellenlisten erwartet.
- **`main` bewegt sich schneller als ein PR.** Der Branch war zum Review-Zeitpunkt vier Merges alt, und der eine davon (#82) hatte die Semantik unter dem PR weggezogen. Die grüne CI am Branch-Kopf sagte über den Stand nach dem Rebase nichts.
- **Zwei Findings kamen aus der Arbeit selbst, nicht aus dem Review:** der `.env`-Pfad im Worktree und die reihenfolgeabhängige Event-Loop im e2e-Test. Beides wäre in der CI nie aufgefallen.
- **Migrationen sind nicht editierbar.** Der Reviewer schlug vor, `0009` zu erweitern; auf jeder bereits migrierten Datenbank wäre das wirkungslos geblieben.
