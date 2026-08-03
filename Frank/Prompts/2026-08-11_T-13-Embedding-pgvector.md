# Chatverlauf — Umsetzung T-13 (Background Worker: Embedding + pgvector HNSW-Index)

**Datum:** 2026-08-11
**Branch:** `feat/T-13-embedding-pgvector` (von `main`/`ee77b7a`)
**Gegenstand:** [Issue #20](https://github.com/tsorer/LearnFlow/issues/20) „[T-13] Background Worker: Embedding + pgvector HNSW-Index"
**Ergebnis:** [PR #71](https://github.com/tsorer/LearnFlow/pull/71) — ein Commit `5e7bb3f`, +388/−13 über 5 Dateien

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen. Entscheidungen aus den Rückfrage-Dialogen sind als Tabellen wiedergegeben.

---

## 1 — Nutzer

> Erstelle einen Plan, wie https://github.com/tsorer/LearnFlow/issues/20 umgesetzt werden kann.

### Claude

**Bestandsaufnahme** (Plan-Modus, zwei parallele Explore-Agents): Worker-Pipeline aus T-12, `models/tables.py`, Alembic-Verzeichnis, `app/config.py`, Testmuster in `tests/`, dazu ADR-003/005/007.

Befunde, die den Zuschnitt bestimmt haben:

- **Keine Migration nötig.** `CREATE EXTENSION vector`, `chunks.embedding vector(1536)` und der HNSW-Index `USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)` existieren seit Migration `0003`. Auch `litellm>=1.40.0` und `pgvector>=0.3.0` stehen bereits in `requirements.txt`.
- **Keine `openapi.yaml`-Änderung** — kein Endpoint, Feld oder Statuscode berührt, die „Spec zuerst"-Regel greift nicht.
- **Settings vorhanden, aber ungenutzt:** `embed_model`, `embed_dimensions`, `litellm_*` sind in `config.py` deklariert; im Backend existiert kein einziger LiteLLM-Aufruf.
- **Tests laufen ohne DB** — alles `AsyncMock` mit Assertions auf exakte SQL-Strings. CI setzt `OPENAI_API_KEY: sk-dummy`, Tests dürfen also nie ins Netz.
- **Batchgrösse, Retry- und Timeout-Policy sind in keinem ADR spezifiziert** — offene Designentscheidung.

Ein Detail wurde ausdrücklich gegengeprüft: Der Worker hängt laut `docker-compose.yml` nur im Netz `worker-db`. Das blockiert `api:8000`, nicht den Internet-Egress (das Netz ist nicht `internal: true`) — Provider-Calls aus dem Worker sind also möglich.

**Entscheidungen (Rückfrage):**

| Frage | Entscheid |
|---|---|
| Bestandschunks aus T-12 ohne Embedding | **Kein Backfill** — bei Bedarf neu hochladen |
| ADR-005: aktive Embedding-Config in DB persistieren | **Folge-Issue**, T-13 bleibt scharf geschnitten |

**Plan-Agent zur Validierung eingesetzt — er hat drei Fallstricke aufgedeckt:**

1. `$7::vector` **funktioniert nicht**: Postgres inferiert den Parametertyp dann als `vector`, für den asyncpg keinen Codec hat. Korrekt ist `$7::text::vector`.
2. Ohne Autouse-Fixture für `embed_texts` würde **jeder bestehende Worker-Test** einen echten HTTP-Call versuchen — in CI mit Dummy-Key ein 401 nach Backoff.
3. `litellm.drop_params = True` global gesetzt würde später die Completion-Calls aus T-18 stillschweigend beeinflussen — gehört pro Request übergeben.

Plan mit diesen Korrekturen vorgelegt und freigegeben.

---

## 2 — (Plan freigegeben)

### Claude

**Umgesetzt:**

- **`app/services/embedding.py`** (neu) — `embed_texts()` kapselt den Provider-Call: gebatcht (64), Antwort nach `index` sortiert, Validierung von Item-Anzahl und Vektorlänge. Modell und Dimension aus den Settings (ADR-005). Ohne DB, Worker und Netz isoliert aufrufbar (DoD-Kriterium 3).
- **`worker/main.py`** — `index_document` in `prepare_chunks` + `store_chunks` geteilt. Damit läuft das Embedding **ausserhalb** der Transaktion (sonst idle-in-transaction über die gesamte HTTP-Dauer, VACUUM auf `chunks` blockiert), und die Transaktionsgrenze ist an der Aufrufstelle sichtbar, wo auch der `except`-Block steht.
- **Alles-oder-nichts:** erst werden alle Chunks eingebettet, dann geschrieben. Ein teilweise eingebettetes Dokument bliebe über den `tsv`-Index auffindbar, wäre für die Dense-Suche aber unsichtbar — still reduzierter Recall statt eines fehlgeschlagenen Jobs.
- 13 neue Tests (`test_embedding.py` neu, `test_worker.py` erweitert).

**Hindernisse und wie sie gelöst wurden:**

- **mypy lief in ein 10-Minuten-Timeout.** Ursache: litellm liefert `py.typed` und ist 126 MB gross — `ignore_missing_imports` ist bei getypten Paketen wirkungslos, mypy prüft das ganze Paket durch. `follow_imports = "skip"` bringt `mypy app worker` auf Sekunden. Ohne das wäre jeder CI-Push entsprechend teuer geworden.
- **Alembic-Konflikt in der Dev-DB.** Der Neustart des api-Containers (nötig, um das hängende mypy zu beenden) legte einen seit ~26 h latenten Zustand offen: die DB stand auf Revision `0008`, deren Migration nur auf dem nicht gemergten Branch `feat/T-24-config-confidence-threshold` liegt. Auf `main`/T-13 endet der Head bei `0007` → API in der Restart-Schleife. Sichtbar wird das erst beim Neustart, weil Alembic nur beim Container-Start läuft.

**Entscheidung (Rückfrage):**

| Frage | Entscheid |
|---|---|
| Dev-DB steht auf Revision 0008 aus fremdem Branch | **Sauber auf 0007 downgraden** |

Ein reines `alembic stamp` wäre nicht ausreichend gewesen: die Migration schreibt zwei `config`-Zeilen per reinem `INSERT` ohne `ON CONFLICT`, beim späteren Merge von T-24 hätte `upgrade head` am Duplicate Key geknallt. Also 0008-Datei temporär aus dem fremden Branch geholt, `alembic downgrade 0007` aus dem worker-Container gefahren (die API lief nicht), Datei wieder entfernt. Die zwei `confidence_threshold_*`-Zeilen sind damit weg und kommen auf dem T-24-Branch per `upgrade head` zurück.

**Checks:** `ruff` ✅ · `mypy` ✅ · `pytest` 85 ✅ · Frontend lint/check/test 8 ✅.

**Verifikation im laufenden System:**

| Prüfung | Ergebnis |
|---|---|
| AK-3 Fehler → `failed` | echter Upload durch den Stack: `status = failed`, LiteLLM-Fehlermeldung in `error_message`, keine Chunks geschrieben |
| AK-2 HNSW-Index | gegen echtes Postgres: `Index Scan using ix_chunks_embedding_hnsw`, `vector_dims` 1536, Round-Trip verlustfrei (Transaktion zurückgerollt) |
| AK-1 Embeddings für alle Chunks | **nur teilweise** — Speicherpfad verifiziert, echter Provider-Call nicht |

**Ausdrücklich als offen gemeldet:** `OPENAI_API_KEY` in `.env` ist der Platzhalter `sk-...`, AK-1 gegen den echten Provider daher nicht nachweisbar.

---

## 3 — Nutzer

> AK-1 mit echtem Key nachholen

### Claude

Erst geprüft, ob der Key inzwischen gesetzt ist (Aufruf zeigt den Key nicht an, nur ob er funktioniert) — unverändert Platzhalter.

Darauf hingewiesen, dass der echte Key vom Nutzer selbst einzutragen ist; API-Keys werden nicht von Claude eingegeben, auch nicht auf Zuruf. Vorab zwei Hinweise gegeben: der Lauf kostet echtes Geld auf dem OpenAI-Konto (Bruchteile eines Cents), und es wird ausschliesslich ein synthetisches Testdokument verwendet, damit der ADR-004-Tripwire (keine internen Dokumente über OpenAI Direct) gewahrt bleibt.

---

## 4 — Nutzer

> Key ist drin

### Claude

api und worker **neu erstellt** statt neu gestartet — `docker restart` liest die `env_file` nicht neu, Umgebungsvariablen werden bei der Container-Erstellung gesetzt.

**Verifikation gegen den echten Provider:**

| Prüfung | Ergebnis |
|---|---|
| Provider-Zugang | OK, 1536 Dimensionen |
| Upload → Status | `available`, 4 Chunks, 2 s |
| AK-1 | `embedding IS NULL` = 0, `vector_dims` = 1536, 4 **verschiedene** Vektoren |
| AK-2 | `Index Scan using ix_chunks_embedding_hnsw` mit echtem Query-Vektor |

**Semantische Stichprobe** als Beleg, dass jeder Vektor beim richtigen Chunk gelandet ist: die Frage „Wie werden die Ergebnisse zweier Suchen zusammengeführt?" trifft `Abschnitt Retrieval` mit Cosine **0,565**, die übrigen Chunks folgen bei 0,32 und 0,30. Ein vertauschter `index` in der Provider-Antwort würde keinen Fehler werfen, sondern später falsche Quellenangaben erzeugen — das kann die Mock-Suite prinzipiell nicht sehen.

Nebenbefund für T-17: die Trennung liegt sauber um den ADR-007-Schwellenwert von 0,35 (Treffer darüber, Nicht-Treffer darunter). Testdokument anschliessend gelöscht, Chunks per Cascade mit (0 verbleibend).

---

## 5 — Nutzer

> zunächst noch das Folge-Issue in Github erstellen

### Claude

Vor dem Anlegen im Team-Repo die Konventionen geprüft (`.github/ISSUE_TEMPLATE/task.md`, freie Nummern, vorhandene Labels) und rückgefragt, welche der beiden im Plan genannten Folge-Issues gemeint sind.

**Entscheidung (Rückfrage):** beide.

- [#68 (T-42)](https://github.com/tsorer/LearnFlow/issues/68) — aktive Embedding-Konfiguration in der `config`-Tabelle persistieren. Begründung im Issue schärfer gefasst als im Plan: der eigentliche Schaden ist nicht die fehlende DB-Zeile, sondern dass ein Modellwechsel Vektoren zweier Modelle im selben HNSW-Index mischt — Cosine-Distanzen zwischen ihnen sind bedeutungslos, das Retrieval liefert stillen Unsinn.
- [#69 (T-43)](https://github.com/tsorer/LearnFlow/issues/69) — Reaper für Dokumente, die nach einem Worker-Absturz dauerhaft in `processing` hängen. Galt schon vor T-13, das Zeitfenster ist durch das Embedding aber deutlich grösser.

Story Points bewusst nicht gesetzt — laut Template gehören sie ins Project Board.

---

## 6 — Nutzer

> das Pre-Review hat diese beiden Punkte ergeben. Bitte bewerten.
> 1. Provider-Fehlertexte gehen ungefiltert an den API-Client — `str(exc)` landet in `documents.error_message` und wird an jeden authentifizierten Nutzer zurückgegeben. Vorschlag: `message = str(exc) if isinstance(exc, ValueError) else "Verarbeitung fehlgeschlagen"`
> 2. Der API-Key wird nie explizit übergeben — funktioniert nur, weil docker-compose `env_file` nutzt. `settings.openai_api_key` ist toter Code. Fix: `api_key=settings.litellm_api_key or settings.openai_api_key`

### Claude

**Beide Befunde selbst nachgeprüft, bevor umgesetzt wurde — beide halten stand.**

**Befund 1 — berechtigt, und der schwerwiegendere.** Kette nachverfolgt: `error_message` geht über `GET /documents/{id}` heraus, und der Endpoint verlangt nur `get_current_user`, nicht `require_knowledge_owner` — ein Learner sieht das Feld also auch. Vor T-13 standen dort ausschliesslich eigene, für Nutzer formulierte Texte; dass sich der Charakter des Feldes durch die Änderung verschiebt, war übersehen worden. Der Beleg lag bereits vor: im ersten Verifikationslauf mit Platzhalter-Key landete der komplette OpenAI-401 samt Key-Echo in dem Feld.

Ein vom Vorschlag offengelassener Punkt wurde vor der Übernahme geprüft: der Filter trägt nur, wenn kein litellm-Fehler von `ValueError` erbt. Alle elf relevanten Exception-Typen der installierten Version hängen an `openai.APIError` — keiner ist ein `ValueError`. `json.JSONDecodeError` wäre einer, steht aber ausserhalb des `try` und erreicht den Handler nie.

**Befund 2 — berechtigt, und der ursprüngliche Code-Kommentar war falsch.** Dort stand, ein zweiter Pfad über `settings.openai_api_key` wäre „Ballast". Verkehrt herum gedacht: das Feld ist ein *Pflicht*-Setting, also nicht eine redundante zweite Quelle, sondern die deklarierte — und sie war toter Code. Dass es trotzdem lief, war ein Nebeneffekt von `env_file` in Compose, nicht Absicht. Per `grep` bestätigt: `openai_api_key` kommt ausser in der Deklaration nirgends vor.

**Umgesetzt** (Commit `ea795d8`, später in den Squash eingegangen), Tests nachgezogen: der AK-3-Test prüft jetzt zusätzlich, dass ein provider-förmiger Text mit Key-Fragment in **keinem** abgesetzten SQL vorkommt; zwei neue Tests decken Key-Fallback und Vorrang des Gateway-Keys ab.

**Verifikation am realen Code-Pfad gegen die echte DB:** eine echte `litellm.AuthenticationError` mit Key-Fragment und `api_base` im Text hinterlässt `status = failed` und `error_message = 'Verarbeitung fehlgeschlagen'`; Fragment und `api_base` nachweislich nicht im Feld, vollständiger Traceback im Worker-Log. Regressionscheck: der explizite Key bricht den funktionierenden Pfad nicht. `ruff` ✅ · `mypy` ✅ · `pytest` 87 ✅.

**Zwei Folgerungen ausserhalb von T-13 gemeldet, nicht angefasst:** der Filter schützt nur diese eine Stelle (T-18 bringt Completion-Calls in denselben Worker), und `GET /documents/{id}` gibt Metadaten jedes Dokuments an jede Rolle heraus, ohne Bezug zum Uploader — eine Frage an T-14.

---

## 7 — Nutzer

> erstelle für Punkt 1 ein Issue

### Claude

[#70 (T-44)](https://github.com/tsorer/LearnFlow/issues/70) — nutzerbestimmte Fehlermeldungen über eine eigene Exception-Klasse markieren.

Im Body begründet, warum das ein eigenes Ticket verdient: der `isinstance(ValueError)`-Filter ist eine **Konvention ohne Absicherung**. Er trägt nur, solange kein Fremdtyp `ValueError` erbt (heute geprüft, bei einem Versions-Upgrade prüft es niemand nach), und `ValueError` sagt an der Wurfstelle nichts darüber aus, ob ein Text für Nutzer bestimmt ist. Zeitbezug vermerkt: sinnvollerweise vor oder mit **T-18**, danach ist die Falle bereits doppelt gestellt.

Der zweite Punkt (Rollenprüfung an `GET /documents/{id}`) wurde bewusst nicht mit aufgenommen — gehört zur Berechtigungslogik in T-14, nicht zum Fehlerpfad.

---

## 8 — Nutzer

> ich hab gesqushed und gepushed. Du kannst den PR erstellen.

### Claude

Ist-Zustand geprüft: ein Commit `5e7bb3f`, Remote identisch zu lokal, Arbeitsbaum leer, Diff gegen `main` genau die fünf erwarteten Dateien. Zusätzlich verifiziert, dass beide Review-Fixes im Squash enthalten sind.

[PR #71](https://github.com/tsorer/LearnFlow/pull/71) erstellt (Titel mit Branchnamen präfixiert, `Closes #20`). Aufbau so, dass ein Reviewer die nicht offensichtlichen Entscheidungen nicht rekonstruieren muss: warum das Embedding ausserhalb der Transaktion läuft, warum alles-oder-nichts geschrieben wird, und warum `$7::text::vector` dort steht — das ist die Zeile, an der sonst jemand „vereinfacht" und einen Encoding-Fehler produziert. Dazu die beiden Pre-Review-Fixes als eigener Abschnitt und der Hinweis, dass der Worker ohne `--reload` läuft (sonst prüft der Reviewer den alten Code).

---

## Ergebnis

- **Ein Commit** `5e7bb3f` auf `feat/T-13-embedding-pgvector`, +388/−13 über 5 Dateien.
- **Alle drei Akzeptanzkriterien** aus Issue #20 erfüllt und gegen den echten Provider im laufenden System durchgespielt.
- **Zwei Pre-Review-Befunde** geprüft, bestätigt und behoben.
- **Keine Migration, keine Spec-Änderung** — Schema und Index standen seit `0003`.
- **Offen für die DoD:** CI grün, Review durch eine zweite Person.

### Drei Fallstricke, die im Verlauf aufgedeckt wurden

| Fallstrick | Auflösung |
|---|---|
| `$7::vector` — asyncpg hat keinen Codec für den Extension-Typ | `$7::text::vector` mit `json.dumps` |
| litellm liefert `py.typed`, mypy prüft 126 MB durch (>10 min) | `follow_imports = "skip"` |
| Provider-Fehlertext mit Key-Fragment an jeden authentifizierten Nutzer | nur `ValueError`-Texte in `error_message` |

### Folge-Issues

- [#68 (T-42)](https://github.com/tsorer/LearnFlow/issues/68) — aktive Embedding-Konfiguration in der `config`-Tabelle persistieren (ADR-005)
- [#69 (T-43)](https://github.com/tsorer/LearnFlow/issues/69) — Reaper für Dokumente, die in `processing` hängen
- [#70 (T-44)](https://github.com/tsorer/LearnFlow/issues/70) — eigene Exception-Klasse für nutzerbestimmte Meldungen (vor oder mit T-18)

### Bekannte offene Punkte

- Ein 10-MB-Dokument (~2000 Chunks) hält im Worker grob 150–200 MB Peak; der Container hat kein Memory-Limit.
- Der Job hält über die gesamte Embedding-Dauer eine Pool-Connection (`max_size=5`) — bei mehr als 5 parallelen Uploads entsteht Queueing.
- Ältere Azure-OpenAI-API-Versionen limitieren `input` auf 16 Elemente; beim Wechsel auf Azure EU ist `BATCH_SIZE` zu prüfen (Pilotstart-Checkliste).
- Die zwei `confidence_threshold_*`-Zeilen aus T-24 fehlen in der Dev-DB, bis auf jenem Branch `alembic upgrade head` läuft.
- Der Worker läuft ohne `--reload` — nach Worker-Änderungen ist `docker compose up -d worker` nötig.
