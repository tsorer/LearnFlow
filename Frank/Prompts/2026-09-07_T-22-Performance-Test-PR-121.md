# Chatverlauf — T-22 p95-Latenz-Test lokal statt CI-Job (PR #121)

**Datum:** 2026-09-06 / 2026-09-07
**Branch:** `feat/T-22-performance-test-lokal` (von `origin/main` abgezweigt); Repo steht zum Zeitpunkt des Exports wieder auf `main`, weil PR #121 zwischenzeitlich gemergt wurde.
**Gegenstand:** [Issue #29](https://github.com/tsorer/LearnFlow/issues/29) (T-22, „Performance-Test: p95-Latenz <= 10s") — Umsetzung als lokaler `make perf`-Test statt CI-Job (Muster von T-28/`make eval`), plus ein Alembic-Drift auf der lokalen Dev-DB, der den Testlauf blockierte, plus Review-Feedback auf [PR #121](https://github.com/tsorer/LearnFlow/pull/121) und dessen Behebung.
**Ergebnis:** PR #121 gemergt (`12c4ad6`). Gemessener Wert: **p95 = 4.53 s** (mean 2.44 s, min 0.84 s, max 5.09 s, 45 In-Corpus-Fragen, 5 Konten parallel) — unter der 10 s-NFA. ADR-008 mit dem Messwert aktualisiert, Issue #29 Akzeptanzkriterium 1 abgehakt. Zwei Review-Befunde (`_run_account` ohne 429-Retry, fragile Admin-Suche) gefixt und nachgepusht.

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich (sehr lange Terminal-Pasten gekürzt, kenntlich gemacht), Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> Ja, so umsetzen

*(Bestätigung eines zuvor vorgelegten Plans: neuer `perf/`-Ordner mit `test_query_latency.py`, `load_in_corpus_questions()`/`assert_corpus_is_indexed()` in `eval/gold_dataset.py`, `make perf`-Target, Doku in `Ops/09_CI-Runbook.md` und ADR-008 — nach dem Muster von `make eval`/T-28, kein eigener CI-Job mangels `OPENAI_API_KEY`-Secret.)*

### Claude

Branch `feat/T-22-performance-test-lokal` von `origin/main` erstellt. Referenzdateien gelesen (`eval/gold_dataset.py`, `eval/test_out_of_corpus_refusal.py`, `e2e/test_query_rate_limit.py`, `seed_users.py`, `Makefile`, `Ops/09_CI-Runbook.md`, ADR-008-Ausschnitte, `pyproject.toml`-`testpaths`) und `LearningCorpus/gold-eval-dataset.yaml` auf 45 `in_corpus`-Fragen geprüft. Umgesetzt:

- `eval/gold_dataset.py`: `load_in_corpus_questions()` ergänzt, `assert_corpus_is_indexed()` aus `test_out_of_corpus_refusal.py` hierher verschoben (jetzt zwei Aufrufer).
- `test_out_of_corpus_refusal.py` auf den verschobenen Helper umgestellt.
- Neu `perf/__init__.py`, `perf/test_query_latency.py`: 5 der 6 Seed-Konten (Login-Limit 5/Min/IP), sequenzielle Logins, danach Round-Robin-Split der 45 Fragen über die 5 Konten, jedes Konto sequenziell gegen sich selbst (Query-Limit 10/Min/Konto), alle 5 Konten parallel via `asyncio.gather`. p95 über `statistics.quantiles(..., n=100)[94]`, CSV-Export nach `perf/out/latency-results.csv`, Gate `p95 <= 10.0`.
- `Makefile`: `perf`-Target nach dem `eval`-Muster.
- `Ops/09_CI-Runbook.md`: drei kleine Ergänzungen (Begründung „kein CI-Job", `make perf` in der Befehlsliste, im Schlussabsatz).
- ADR-008: „Offen bleibt die Latenz" auf „kann jetzt lokal vermessen werden" umformuliert (noch ohne echten Wert).

---

## 2 — Nutzer

> was mache ich falsch?
>
> C:\Projects\CAS\LearnFlow\LearnFlow\Ops>wsl
> frank@Notebook82:/mnt/c/Projects/CAS/LearnFlow/LearnFlow/Ops$ make perf
> make: *** No rule to make target 'perf'.  Stop.
> frank@Notebook82:/mnt/c/Projects/CAS/LearnFlow/LearnFlow/Ops$ make up
> make: *** No rule to make target 'up'.  Stop.
> [...]
> frank@Notebook82:/mnt/c/Projects/CAS/LearnFlow/LearnFlow$ make perf
> make: *** No rule to make target 'perf'.  Stop.

### Claude

Zwei Ursachen erklärt: das `Makefile` liegt in `src/`, nicht im Repo-Root oder in `Ops/`; ausserdem hat der Nutzer vermutlich noch `main` ausgecheckt, wo `make perf` (Teil von PR #121) noch nicht existiert. Befehle für beides genannt (`cd src`, `git checkout feat/T-22-performance-test-lokal`).

---

## 3 — Nutzer

> frank@Notebook82:/mnt/c/Projects/CAS/LearnFlow/LearnFlow/src$ make up && make seed && make seed-corpus && make perf
> docker compose up -d --build
> unable to get image 'src-api': failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory
> make: *** [Makefile:5: up] Error 1

### Claude

Per `AskUserQuestion` geklärt, ob Docker Desktop überhaupt läuft (Antwort: ja) — damit war die Ursache auf die WSL-Integration eingegrenzt: Docker Desktop läuft, aber die genutzte WSL-Distro ist unter **Settings → Resources → WSL Integration** nicht aktiviert. Anleitung zum Aktivieren plus `docker ps` als Verifikationsbefehl gegeben.

---

## 4 — Nutzer

> frank@Notebook82:/mnt/c/Projects/CAS/LearnFlow/LearnFlow/src$ make up && make seed && make seed-corpus && make perf
> [+] Building 326.5s (36/36) FINISHED
> [...lange Docker-Build-Ausgabe, gekürzt...]
> [+] up 7/7
>  ✔ Container src-db-1     Healthy
>  ✔ Container src-worker-1 Started
>  ✘ Container src-api-1    Error dependency api failed to start
>  ✔ Container src-webapp-1 Recreated
> dependency failed to start: container src-api-1 is unhealthy
> make: *** [Makefile:5: up] Error 1

### Claude

Docker-Integration lief jetzt, `src-api-1` aber unhealthy. Um Logs statt Vermutungen gebeten (`docker logs src-api-1 --tail 50`), mit dem Hinweis, dass das nach dem bekannten Alembic-Drift-Muster aussieht (Memory `learnflow-dev-db-alembic-drift`: Dev-DB überlebt Branch-Wechsel, eine fremde Migration kann die API in eine Restart-Schleife schicken).

---

## 5 — Nutzer

> docker logs src-api-1 --tail 50
> ERROR [alembic.util.messaging] Can't locate revision identified by '0018'
> FAILED: Can't locate revision identified by '0018'
> [...]

### Claude

Bestätigt: lokale Migrationen (`src/backend/alembic/versions/`) und `origin/main` enden beide bei `0017`; die DB steht auf `0018`. Alle Remote-Branches durchsucht — `0018_embedding_config.py` existiert nur auf dem nicht gemergten `feat/T-42-embedding-config-persistenz`. Die Datei per `git show` extrahiert und temporär nach `src/backend/alembic/versions/` gelegt (bind-gemountet, landet automatisch im Container), damit Alembic die Revisionskette wieder auflösen kann. Anleitung gegeben: `docker exec src-worker-1 alembic downgrade 0017`, danach die Datei wieder entfernen, `alembic_version` in der DB gegenprüfen, dann `make up && make seed && make seed-corpus && make perf` erneut.

---

## 6 — Nutzer

> kannst du hier perf laufen lassen?

### Claude

Da Bash-Tool und Nutzer-WSL dieselbe Windows-Maschine teilen (`C:\...` ⇆ `/mnt/c/...`), direkt `docker ps` geprüft: `src-api-1` und `src-worker-1` liefen bereits gesund. Vor dem Lauf den `OPENAI_API_KEY` im Container geprüft, ohne ihn auszugeben (Länge, kein `dummy`-Substring) — ein echter Key war gesetzt. Erster Testlauf schlug fehl (`ConnectError: No address associated with hostname` für `webapp`) — `src-webapp-1` war nur `Created`, nie gestartet; mit `docker compose up -d` nachgestartet, dabei wurden `src-api-1`/`src-worker-1` neu erzeugt. Danach aufgefallen: die temporäre `0018_embedding_config.py` war noch nicht entfernt, `alembic_version` stand nach dem Neustart wieder auf `0018` (die API validiert beim Start nur strukturell, nicht inhaltlich gegen den eigenen Branch). Testlauf im Hintergrund gestartet (5/Min-Login-Fenster abwarten, dann `pytest perf`); nach Ablauf lief der Test durch:

```
Query latency: p95=4.53s mean=2.44s min=0.84s max=5.09s (45 requests)
1 passed in 27.51s
```

Vorschlag gemacht, ADR-008 mit dem Messwert zu aktualisieren und Issue #29 Akzeptanzkriterium 1 abzuhaken.

---

## 7 — Nutzer

> Ja, so machen

### Claude

- ADR-008 (`Docs/04_ADR-008_Konfidenz-Pipeline.md`): „Offen bleibt die Latenz" durch „Latenz gemessen (T-22, #29, 2026-09-06)" mit den vier Kennzahlen ersetzt; Punkt 5 der „Offenen Punkte" als erledigt markiert.
- `.gitignore`: `src/backend/perf/out/` ergänzt (analog `eval/out/`), da `perf/out/` als generierter Output beim `perf`-Lauf entstanden war.
- Issue #29: Akzeptanzkriterium „p95-Latenz <= 10s unter Normallast" abgehakt, mit dem Messwert als Kommentar in der Checkbox-Zeile. Die anderen beiden Kriterien bewusst nicht angerührt.
- Commit `T-22 docs(adr-008): record measured p95 latency (4.53s) for stage 3 (#29)`, gepusht auf `feat/T-22-performance-test-lokal`.

*(Vorausgegangen war bereits die Anpassung von Issue #29 im Rahmen der ursprünglichen Plan-Umsetzung: die Akzeptanzkriterien „Test läuft in CI" durch „Test lokal ausführbar mit echtem Key (`make perf`)…" ersetzt und die Beschreibung von k6/pytest-benchmark auf die tatsächliche pytest/httpx-Umsetzung korrigiert, nach expliziter Bestätigung „Ja, Issue #29 anpassen".)*

---

## 8 — Nutzer

> bewerte das Feedback auf github

### Claude

PR #121 über `gh pr view --json comments` abgerufen: ein automatisierter Review-Kommentar mit zwei Befunden. Beide gegen den aktuellen Code verifiziert:

1. **Kein 429-Handling in `_run_account`** (`perf/test_query_latency.py:90`) — zutreffend. Hartes `assert r.status_code == 200` statt Retry wie im Refusal-Test; aktuell unkritisch (9 Anfragen/Konto bei Limit 10), aber fragil, falls der Fragenpool wächst.
2. **Admin-Suche über den `ACCOUNTS`-Slice statt der vollen `USERS`-Liste** (`perf/test_query_latency.py:120`) — zutreffend. Funktioniert nur, weil der Admin zufällig in `USERS[:5]` liegt; eine Umsortierung von `seed_users.USERS` würde mit `StopIteration` crashen.

Beide als echte, gut lokalisierte Robustheitslücken eingestuft (kein Rauschen, kein akuter Bug) und einen Fix für beide vorgeschlagen.

---

## 9 — Nutzer

> Ja, so machen

### Claude

- `_query_with_retry` (async, analog `eval/test_out_of_corpus_refusal.py`) ergänzt: 429 → `Retry-After`/`RATE_LIMIT_RETRY_S` abwarten, bis zu `MAX_RETRIES = 2`, danach `pytest.fail`; die gemessene Latenz zählt nur den erfolgreichen Versuch.
- Admin-Suche läuft jetzt über die volle `USERS`-Liste, mit einer Assertion, dass der gefundene Admin auch tatsächlich unter den geloggten `ACCOUNTS` ist (klare Fehlermeldung statt `StopIteration`).
- `ruff check`, `mypy app worker perf eval` und `pytest perf eval --collect-only` im Container gegengeprüft, alle grün.
- Commit `T-22 fix(perf): 429 retry and robust admin lookup (review #121)`, gepusht.

*(Ausserhalb dieser Konversation, ohne Merge-Anweisung von Claude, wurde PR #121 anschliessend gemergt — sichtbar am Repo-Zustand beim Export: lokaler Branch ist wieder `main`, `git log` zeigt den Merge-Commit `12c4ad6`.)*

---

## 10 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Bestehende Exporte in `Frank/Prompts/` als Vorlage gelesen (zuletzt `2026-08-24_PR-91-Review-T-45.md`) und dieses Dokument nach der dort etablierten Konvention erstellt.
