# Chatverlauf — T-43 Worker-Reaper (Dokumente aus hängendem `processing` befreien), PR #104

**Datum:** 2026-08-30 – 2026-08-31
**Branch:** `feat/T-43-worker-reaper`, von `origin/main` abgezweigt, später auf `main` rebased. Als Squash-Merge `fbff407` in `main`.
**Gegenstand:** Issue [#69](https://github.com/tsorer/LearnFlow/issues/69) „[T-43] Worker-Reaper: Dokumente aus haengendem Status 'processing' befreien" (US-04) — von der Machbarkeitsfrage bis zum gemergten PR.
**Ergebnis:** [PR #104](https://github.com/tsorer/LearnFlow/pull/104), drei Commits, Approve durch `luenlestra` mit drei Findings, zwei davon noch im PR umgesetzt. Nebenprodukte: Migration 0017 (`index_version`, `index_attempts`, zwei Config-Keys), Ablösung des Versions-Tokens von `updated_at`, Nachtrag in ADR-006, Folge-Issues [#106](https://github.com/tsorer/LearnFlow/issues/106) (T-51) und [#107](https://github.com/tsorer/LearnFlow/issues/107) (T-52).

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> T-43 (https://github.com/tsorer/LearnFlow/issues/69) ist unabhängig von den offnenen PRs und kann umgesetzt werden, oder?

### Claude

Issue gelesen, die vier offenen PRs (#99 T-49, #100 T-28, #101 T-47/48, #103 T-50) auf berührte Dateien geprüft und dem Zielgebiet von T-43 gegenübergestellt. Ergebnis: keine Überschneidung. Insbesondere fügt **keiner** der offenen PRs eine Alembic-Migration hinzu, `0016` ist auf `main` der Head; die Vorbedingungen T-12/T-13 sind drin.

Zwei Hinweise vorab: `docker-compose.yml` liegt in #100 und #101 — falls der Reaper dort etwas bräuchte, gäbe es einen kleinen Konflikt (vermeidbar, weil die Frist laut Akzeptanzkriterium ohnehin aus der `config`-Tabelle kommt). Und der eigentliche Knackpunkt ist der Issue-Kommentar aus #87: seit T-15 ist `documents.updated_at` das Versions-Token des Workers, die Spalte trägt `onupdate=func.now()`, ein ORM-Write des Reapers würde einen noch lebenden Job still seinen Lauf verwerfen lassen. Die drei dort genannten Varianten benannt, Variante 1 (rohes SQL) als Weg des geringsten Widerstands, Variante 3 (eigene Versionsspalte) als die saubere.

Nebenbei: lokales `main` war zwei unveröffentlichte Commits voraus, Feature-Branch also von `origin/main`.

---

## 2 — Nutzer

> Was wäre der Vorteil von Variante 3 und wie gross wäre die Änderung?

### Claude

Drei Vorteile, wobei nur der dritte über „sauberer" hinausgeht:

1. **Die Invariante wird erzwungen statt vereinbart.** Sie hing an einem 12-Zeilen-Kommentar an der Spalte und an einem Test, der im eigenen Docstring einräumt, dass er die ORM-Seite nicht sehen kann.
2. **Zwei Bedeutungen werden entflochten.** `updated_at` ist gleichzeitig Anzeigewert (das Paar mit `created_at` unterscheidet Ersetzung von Erstupload) und Concurrency-Token.
3. **Der Reaper bekommt eine Fähigkeit, die Variante 1 ihm nicht geben kann:** mit einem eigenen Zähler kann er einen hängenden Lauf *für ungültig erklären*. Bei Variante 1 darf er `updated_at` gerade nicht anfassen, hat also kein Mittel zu sagen „dein Lauf ist void" — er reiht neu ein, und wenn der totgeglaubte Job doch lebt, schreiben zwei Läufe dasselbe Dokument.

Aufwandsschätzung als Tabelle: fünf Dateien plus Migration, grob 60–80 Zeilen netto, davon ein guter Teil Kommentar; `openapi.yaml` und `schema.d.ts` unberührt, weil die Spalte intern bleibt. Empfehlung: Variante 3, weil Punkt 3 Variante 1 zu einer Lösung mit bekannter Restlücke macht.

---

## 3 — Nutzer

> ja, erarbeite einen Umsetzungsplan für Variante3

### Claude

Plan-Modus. Drei Entscheidungen vorab abgefragt statt still gewählt: Scope (T-43 komplett in einem PR), Reaper-Aktion (Requeue, nach N Versuchen `failed`), Scheduling (asyncio-Loop im Worker). Plan mit Schritt 0 „Annahmen im laufenden Stack verifizieren" — was sich als die wichtigste Zeile des Plans herausstellte.

Bei der Umsetzung drei Befunde, die den Plan korrigierten:

**pgqueuer sendet keine Heartbeats.** `Heartbeat.__aenter__` startet den Sender nur bei `interval > 0`, und das Intervall ist `retry_timer / 2` — unsere Registrierung nutzt den Default `timedelta(0)`. `heartbeat` trägt damit den Zeitpunkt der Übernahme (`SET status = 'picked', … heartbeat = NOW()`), nicht ein Lebenszeichen. Die Erkennung funktioniert weiterhin und braucht keine neue Spalte, aber die Frist muss den längsten legitimen Lauf übersteigen. Die im Plan behauptete Immunität für langsame Läufe gibt es nicht — als Kommentar an `STUCK_DOCUMENTS` festgehalten.

**Zwei Postgres-Stolpersteine in der Migration**, beide von einer Wegwerf-Datenbank gefunden: `0014` legt einen `DEFERRABLE INITIALLY DEFERRED`-Constraint-Trigger auf `config` und seedet durch ihn hindurch, wodurch Postgres in derselben Alembic-Transaktion jedes `ALTER TABLE config` verweigert („pending trigger events"). Nötig waren `SET CONSTRAINTS ALL IMMEDIATE` und die Reihenfolge Constraint-vor-Seed.

**Die QA lief zunächst gegen fremden Code.** Der laufende Compose-Stack war auf ein anderes Worktree gemountt (`.claude/worktrees/…`, Branch T-50). `docker exec src-api-1 pytest/ruff/mypy` meldete grün, ohne meine Änderungen je gesehen zu haben; verraten hat es nur die neu angelegte Migrationsdatei, die im Container fehlte. Danach alle Checks über `docker run` mit explizitem Mount auf das Arbeitsverzeichnis, Migration und Reaper-SQL gegen eine eigene Wegwerf-DB — die geteilte Dev-DB blieb bewusst unmigriert, um keine Alembic-Drift zu erzeugen.

Ergebnis: `ruff`, `mypy`, 445 Tests grün; Migration `upgrade → downgrade → upgrade` geprüft; Reaper-SQL mit echten Zeilen gegen echtes Postgres (alle vier AK), Wegwerf-Ressourcen wieder entfernt.

---

## 4 — Nutzer

> der Container wurde wieder auf src umgestellt. Benenne den commit noch auf "T-43: reap documents stuck in 'processing'" um

### Claude

Zustand nachgeprüft statt geglaubt: Mount zeigt jetzt auf das Arbeitsverzeichnis, DB steht auf `0017`. Commit-Subject per `--amend` geändert, Body und Co-Author-Trailer unverändert. Danach angeboten, den offenen DoD-Punkt „AK im laufenden System" nachzuholen, mit dem Vorschlag, die Frist auf 60 s zu setzen und ein Dokument künstlich auf `processing` zu stellen, statt einen echten Embedding-Lauf abzuwürgen.

---

## 5 — Nutzer

> zunächst noch diese Punkte verifizieren:
>
> **1. `admin.py` — Invariante gebrochen (das Wichtigste).** admin.py:17 sagt wörtlich: „Die schreibbare Whitelist ist exakt die Menge der Keys, die der CHECK validiert (0012, erweitert durch 0014)." Migration 0017 erweitert diesen CHECK um `processing_timeout_seconds` und `processing_max_attempts` — `WRITABLE_KEYS` und `COUNT_KEYS` bleiben unverändert. Der Kommentar ist damit falsch. […] Die beiden Ausschlussgründe, die der Kommentar selbst nennt, greifen hier nämlich nicht: `chunk_size` ist raus, weil eine Änderung erst nach Re-Indexierung wirkt — der Reaper liest seine Config pro Pass; `stale_days` ist raus, weil Reader und DB-Constraint fehlen — beides existiert hier. […] Falls aufnehmen: die Keys müssen in beide Mengen. `_validate_shape` fällt für alles ausserhalb von `COUNT_KEYS` auf `NUMERIC_UNIT_INTERVAL` durch — `900` würde sonst mit „muss eine Zahl zwischen 0 und 1 sein" abgelehnt.
>
> **2. Fehlermeldung diagnostiziert falsch, wenn das Timeout die Ursache ist.** Weil `heartbeat` bei `retry_timer=0` nur den Zeitpunkt der Übernahme trägt, ist die Bedingung „vor mehr als 900 s beansprucht", nicht „tot". […] nach drei Runden bekommt der Nutzer eine Meldung, die auf einen Worker-Neustart zeigt, der nie stattgefunden hat. Und „erneut hochladen" hilft dann auch nicht.
>
> **3. `index_attempts` wird bei Erfolg nicht zurückgesetzt.** Nur `_replace` setzt den Zähler auf 0 — `mark_available` nicht. […] das Budget soll den Vorfall begrenzen, nicht die Fassung.

*(gekürzt; vollständiger Wortlaut im Transkript)*

### Claude

Alle drei am Code nachgeprüft und bestätigt.

Zu 1: Der Kommentar in `admin.py` war tatsächlich falsch geworden, und beide Ausschlussgründe greifen für die neuen Keys nicht. Aufgenommen in `WRITABLE_KEYS` **und** `COUNT_KEYS`, Kommentar umgeschrieben — mit dem Zusatz, dass der Reader hier im Worker sitzt und nicht in `app/services/config.py`, und dass „wirkt sofort" beim Reaper „spätestens beim nächsten Pass" heisst.

Zu 2: Die Meldung nannte eine Ursache, die die Bedingung gar nicht feststellen kann. Neu formuliert, Ursache offengelassen, „erneut hochladen" gestrichen.

Zu 3: Einzeilig in `mark_available` ergänzt (`index_attempts = 0`), dazu ein Test und nachgezogene Kommentare an Spalte und Migration — das Budget begrenzt den Vorfall, nicht die Fassung.

---

## 6 — Nutzer

> ja, spiel die AK im laufenden System durch

### Claude

Worker neu gestartet (der laufende Prozess hatte die letzten Korrekturen noch nicht), vier Testdokumente angelegt, Frist über `PUT /api/admin/config` auf 60 s — womit gleichzeitig die neu schreibbaren Keys end-to-end belegt waren, inklusive Gegenprobe mit `0.5` → 422.

| AK | Beleg |
|---|---|
| 1 erkannt | Erster Pass um 11:18:51, exakt 225 s nach Worker-Start |
| 2 requeue **oder** `failed` | Verwaistes Dokument → `pending`, sofort übernommen (`job_id=81`), 3,4 s später `Indexed … chunks=1`. Dokument mit 2 von 3 verbrauchten Versuchen → `failed` mit Meldung |
| 3 konfigurierbar | `900 → 60` ohne Neustart; Takt danach 15 s statt 225 s, nachgewiesen an einem später eingefügten Dokument (eingefügt 13:19:26, eingesammelt 13:19:36) |
| 4 laufender Lauf unangetastet | Dokument mit frisch gehaltenem Heartbeat blieb über den Pass hinweg `processing/v1/a0`, während daneben zwei gereapt wurden |

Als Gegenprobe die dokumentierte Kante: nach dem Einstellen der Heartbeat-Auffrischung wurde auch dieses Dokument 46 s später eingesammelt, neu eingereiht und indexiert — das erwartete Verhalten der Übernahme-Semantik, kein Fehlschlag der Toterkennung. Testdaten und Config danach zurückgesetzt.

---

## 7 — Nutzer

> ja, pushen und PR aufmachen

### Claude

Gepusht, [PR #104](https://github.com/tsorer/LearnFlow/pull/104) eröffnet, Titel mit Branchnamen geprefixt, `Schliesst #69`. Im PR-Text neben der Lösung die drei Dinge, die ein Review sonst selbst herausfinden müsste: der `retry_timer`-Befund samt AK-4-Kante, die 225 s bis zum ersten Pass, die zwei Postgres-Stolpersteine.

`frontend` und `backend` grün, **`e2e` rot** — und zwar an einer Stelle, die ich selbst verursacht hatte: `0017` baut die CHECK-Constraint neu und hatte die Schlüsselliste von `0012` übernommen. `0014` hatte sie aber um `self_check_band_low`/`_high` erweitert. Die beiden Keys fielen damit in den `ELSE true`-Arm, wo `1.5`, `-0.1` und `'spaeter'` alle durchgehen — eine fail-open-Lücke genau bei den Werten, auf die sich ADR-008 stützt. Als eigener Commit korrigiert (nicht als Amend, weil der PR schon offen war), mit einem Backend-Test, der das künftig in `make qa` fängt statt erst in der e2e-Stufe. Danach alle drei Checks grün.

---

## 8 — Nutzer

> bewerte das Feedback von https://github.com/tsorer/LearnFlow/pull/104

### Claude

Approve mit drei Findings. Alle drei am Code nachgerechnet:

**Finding 1 (900-s-Default zu knapp)** hält — und ist zu schwach formuliert. Verifiziert: Batches laufen **sequenziell**, `BATCH_SIZE = 64`, `TIMEOUT_SECONDS = 30.0`, `MAX_UPLOAD_BYTES = 10 MiB`. Übersehen hatte der Review `MAX_RETRIES = 2`, das als `num_retries` in denselben Aufruf geht: ein Batch darf drei Anläufe nehmen. Der kritische Fall ist nicht der tote Provider (dann scheitert der Job sauber), sondern der zähe — ein Lauf, der **erfolgreich endet** und ~1740 s braucht. Der vorgeschlagene Wert 1800 hätte die Grenze also nicht überschritten.

**Finding 2 (verwaiste `pgqueuer`-Zeilen)** hält, ist aber Hygiene: die tote Zeile schützt kein Dokument mehr, weil ihr Heartbeat alt ist. Folge-Issue.

**Finding 3 (Auswertungsreihenfolge des JSON-Casts)** hält. Vorgeschlagen war ein Kommentar; ich habe stattdessen einen `CASE`-Guard empfohlen — gleiche Zeilenzahl, aber er entfernt den Fallstrick statt ihn zu beschreiben.

Nicht verifizierbar war die Chunk-Dichte von 185 Chunks/MB, weil Docker gerade nicht lief; als offen markiert, mit dem Hinweis, dass der Schluss nicht daran hängt.

---

## 9 — Nutzer

> ja, mach beides (vorher am besten ein Rebase und prüf den Stand von Docker und der DB)

### Claude

Zustand geprüft: Docker oben, Mount auf dem Arbeitsverzeichnis, DB auf `0017`, Testdaten weg, Config auf den Defaults. `main` war um #101 weitergezogen — Rebase konfliktfrei.

Umgesetzt (`f589531`): Default auf **2700 s** mit der vollständigen Rechnung inklusive Retries als Nachtrag in ADR-006; `CASE`-Guard im `NOT EXISTS` plus Test, der den Cast innerhalb des `CASE` festnagelt. Zusätzlich — und im PR-Kommentar ausdrücklich als nicht verlangte Änderung markiert — das Pass-Intervall bei 300 s gedeckelt: es war an die Frist gekoppelt (`timeout / 4`), der grössere Default hätte die *Erkennung* mitgezogen, was zwei verschiedene Dinge sind.

Zur Gegenprobe bei Finding 3 eine Job-Zeile mit fremdem Entrypoint und Payload `not json at all` angelegt: mit Guard läuft der Reaper durch; **ohne** Guard warf die Abfrage bei dieser Datenmenge ebenfalls nicht, weil der Planer günstig sortierte. Der Absturz liess sich also nicht reproduzieren — was das Argument für den Guard ist, nicht dagegen.

Folge-Issues angelegt: [#106](https://github.com/tsorer/LearnFlow/issues/106) (T-51, Fortschritts-Zeitstempel — der Weg, der AK 4 wirklich schliesst) und [#107](https://github.com/tsorer/LearnFlow/issues/107) (T-52, verwaiste Queue-Zeilen), beide mit den offenen Entscheidungen ausformuliert.

---

## 10 — Nutzer

> schreib den Kommentar auf den Review

### Claude

[Kommentar](https://github.com/tsorer/LearnFlow/pull/104#issuecomment-5480971603) mit vier Abschnitten: Finding 1 übernommen, aber mit korrigierter Rechnung und Begründung für 2700 statt 1800; Finding 3 als Guard statt Kommentar, samt der ehrlichen Notiz, dass sich der Absturz nicht reproduzieren liess; Finding 2 mit den drei Fragen, die es zu einem eigenen Vorgang machen; AK 4 zugespitzt — mit *keinem* Default schliessbar, solange `heartbeat` den Übernahmezeitpunkt trägt.

Dazu eine Deployment-Notiz, die sonst jemanden erwischt hätte: auf bereits migrierten Datenbanken seedet `0017` nicht erneut, `processing_timeout_seconds` bleibt dort auf `900`.

---

## 11 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Dieses Dokument. Beim Sammeln der Metadaten fiel auf, dass PR #104 inzwischen gemergt ist (`fbff407`) und das lokale Repository auf `main` steht — der Verlauf ist entsprechend als abgeschlossen dokumentiert.

---

## Nebenprodukte und Befunde

- **Migration 0017** — `documents.index_version` (Optimistic-Lock-Token ohne `onupdate`), `documents.index_attempts` (Budget des Reapers), Config-Keys `processing_timeout_seconds` / `processing_max_attempts` samt CHECK-Erweiterung.
- **ADR-006, Nachtrag „Crash-Recovery endet nicht am Job"** — der ADR führte Crash-Recovery als Argument für pgqueuer; das gilt für den Job, nicht für das Dokument.
- **Drei Fehler, die erst echte Infrastruktur gefunden hat:** die „pending trigger events" der Migration und der Reihenfolgefehler beim Seed (Wegwerf-DB), die fail-open-Lücke bei der CHECK-Constraint (CI-e2e). Die reine Unit-Suite hätte keinen davon gezeigt.
- **Eine Lehre fürs Setup:** ein laufender Compose-Stack kann auf ein fremdes Worktree gemountet sein. `docker exec src-api-1 pytest` meldet dann grün, ohne den eigenen Code je gesehen zu haben — vor QA im Container einmal `docker inspect src-api-1` gegen das Arbeitsverzeichnis halten.
