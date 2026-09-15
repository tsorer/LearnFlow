# ADR-006: Background Worker — pgqueuer statt Celery + Redis

| Feld | Inhalt |
|---|---|
| **Status** | Accepted |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

US-04 verlangt, dass Dokumente nach dem Upload innerhalb von 5 Minuten als Quelle verfügbar sind. Das Processing-Pipeline (Parsing → Chunking → Embedding → pgvector-Indexierung) ist zu aufwändig, um synchron im HTTP-Request ausgeführt zu werden — der Upload würde für grosse Dokumente blockieren. Es braucht deshalb einen Background Worker, der Jobs asynchron abarbeitet.

ADR-001 hat einen modularen Monolithen mit einem einzigen Deployment-Artefakt als Ziel definiert. ADR-002 nannte Celery + Redis als Mitigation für persistente Jobs — ohne diesen Widerspruch zu ADR-001 explizit aufzulösen. Der ADR-Review hat diesen Konflikt als offene Entscheidung mit hoher Priorität markiert.

LearnFlow hat genau **einen Job-Typ**: ein Dokument verarbeiten. Das Volumen ist gering (< 30 Pilotnutzer, 1 Bereich). Betriebskomplexität ist teuer bei 360 h Umsetzungsbudget.

---

## Entscheidung

Wir verwenden **pgqueuer** als Background-Worker-Mechanismus.

Jobs werden in einer PostgreSQL-Tabelle persistiert. Der Worker läuft als separater Python-Prozess im selben Docker-Compose-Stack und nutzt PostgreSQL `LISTEN`/`NOTIFY` für sofortige Job-Benachrichtigung. **Redis entfällt vollständig.**

---

## Begründung

### Warum pgqueuer die bessere Wahl ist

**1. Passt zu ADR-001 (Modularer Monolith)**
pgqueuer braucht keinen neuen Service. Jobs leben in einer Tabelle in der PostgreSQL-Datenbank, die bereits vorhanden ist. Der Monolith bleibt ein echter Monolith — `docker compose up` startet vier Artefakte statt sechs.

**2. Job-Persistenz ist gratis**
Jobs überleben einen Container-Neustart automatisch — sie sind persistierte Datenbankzeilen. Bei Celery + Redis ohne explizite Persistence-Konfiguration gehen ausstehende Jobs bei einem Redis-Neustart verloren.

**3. Ein Backup deckt alles ab**
Jobs, Dokumente, Embeddings und Konfiguration liegen alle in PostgreSQL. Ein einziges Backup-Skript deckt den vollständigen Systemzustand — kein separater Redis-Dump.

**4. Operational Overhead ist für diesen Use Case nicht rechtfertigbar**
Celery + Redis erfordert zwei zusätzliche Container, zwei separate Konfigurationen, zwei separate Health-Checks und eigenes Monitoring. Bei einem einzigen Job-Typ (Dokument verarbeiten) und < 30 Nutzern ist das nicht gerechtfertigt.

**5. Ausreichende Leistung für den Pilot**
pgqueuer via `pg_notify` reagiert in Millisekunden auf neue Jobs. Der Throughput-Engpass liegt beim Embedding-API-Call (Azure OpenAI EU Rate-Limit), nicht beim Queue-Mechanismus. pgqueuer ist für dieses Volumen mehr als ausreichend.

---

## Konsequenzen

### Positive Konsequenzen

- **+** ADR-001-Widerspruch aufgelöst: ein Deployment-Artefakt bleibt ein echtes Ziel.
- **+** Kein Redis: eine Dependency weniger, eine Backup-Strategie weniger, eine Failure-Domain weniger.
- **+** Jobs sind persistent ohne zusätzliche Konfiguration.
- **+** Onboarding: `docker compose up` ohne Redis-Setup-Anleitung.
- **+** Gleiche PostgreSQL-Verbindung wie der API Server — kein neues Netzwerk-Hop.

### Negative Konsequenzen

- **−** pgqueuer ist weniger bekannt als Celery — kleinere Community, weniger StackOverflow-Treffer. Mitigation: der Job-Typ ist trivial (eine Funktion, ein Retry-Mechanismus), keine exotischen Features nötig.
- **−** Kein eingebautes Monitoring-Dashboard (Celery hat Flower). Mitigation: Job-Status in der `jobs`-Tabelle ist direkt per SQL abfragbar — ausreichend für den Pilot.
- **−** Bei einem späteren Bedarf nach mehreren parallelen Job-Typen mit unterschiedlichen Prioritäten und Rate-Limiting müsste der Entscheid neu bewertet werden. Für den MVP-Scope (ein Job-Typ) kein Problem.

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Celery + Redis** | Zwei zusätzliche Deployment-Artefakte widersprechen ADR-001. Redis bringt keinen Mehrwert für einen einzigen Job-Typ bei < 30 Nutzern. Job-Persistenz muss explizit konfiguriert werden. Operativer Overhead steht in keinem Verhältnis zum Nutzen. |
| **`procrastinate`** | Gleiche Architektur wie pgqueuer (PostgreSQL + `LISTEN`/`NOTIFY`, kein Broker) und reifer/länger battle-tested — adressiert genau den einzigen pgqueuer-Nachteil (kleinere Community). Knapp zugunsten pgqueuer verworfen wegen dessen schlankerer, async-nativer API und geringerem konzeptionellen Overhead für den einen trivialen Job-Typ. Gleichwertige Rückfalloption, falls pgqueuer-Reife zum Problem wird — kein Architekturwechsel, da identisches Postgres-Queue-Muster. |
| **Handgerollt: `SELECT … FOR UPDATE SKIP LOCKED`** | Konsequent zum eigenen Argument „der Job-Typ ist trivial": ein ~30-Zeilen-Worker ohne jede Queue-Library. Verworfen, weil pgqueuer Retry-/Scheduling-/Notify-Mechanik bereits getestet mitbringt — diese selbst korrekt (Nebenläufigkeit, Retries, Crash-Recovery) zu bauen ist mehr Risiko als Ersparnis. Bleibt die Minimal-Fallback-Variante. |
| **FastAPI `BackgroundTasks`** | In ADR-002 bereits ausgeschlossen: nicht persistent — laufende Jobs gehen bei Container-Neustart verloren, verletzt das 5-Minuten-SLA von US-04 im Fehlerfall. Hier nur als Querverweis zur Vollständigkeit. |
| **ARQ / Dramatiq / SAQ** | Alle benötigen Redis (oder einen anderen Broker) als zusätzlichen Service — scheitern aus demselben Grund wie Celery + Redis am Monolith-Ziel (ADR-001). |

---

## Auswirkung auf 05_C4-C2_Container.md

Der Container-Diagram-Eintrag für den Worker ist damit konkretisiert:

- **Container:** Background Worker — `pgqueuer` (Python-Library)
- **Kommunikation API → Worker:** `pg_notify` via PostgreSQL (kein Redis-Broker)
- **Deployment:** 4 Container total: `webapp`, `api`, `worker`, `db` — kein `redis`

---

## Nachtrag 2026-08-30 — Crash-Recovery endet nicht am Job (T-43)

Die Abwägung oben führt „Crash-Recovery" als Argument für pgqueuer, und für den **Job** trifft
das zu: er bleibt persistent in der Tabelle. Für das **Dokument** trifft es nicht zu. Der
Worker setzt `documents.status = 'processing'`, bevor er beginnt; stirbt der Container
dazwischen — Absturz, Neustart, Deployment, OOM —, bleibt die Zeile dort stehen. Sie ist für
Retrieval unsichtbar, nicht als Fehler erkennbar und sieht für den Nutzer aus wie „lädt
ewig". Kein Mechanismus der Bibliothek räumt das auf; die periodische Wiedervorlage
(`retry_timer`) ist bewusst nicht aktiviert, weil sie zwei Läufe gleichzeitig auf dasselbe
Dokument lassen würde.

Der Worker führt deshalb neben dem Job-Consumer eine zweite, periodische Aufgabe: einen
**Reaper**, der Dokumente in `'processing'` erkennt, zu denen kein Job mehr in der Queue
liegt, der jünger als `processing_timeout_seconds` beansprucht wurde. Er reiht sie erneut ein
(Re-Verarbeitung ist idempotent) und gibt nach `processing_max_attempts` Versuchen mit
`status = 'failed'` und einer lesbaren Meldung auf — unbegrenzt zu wiederholen hiesse, ein
Dokument, das den Worker zuverlässig umbringt, endlos gegen die Pipeline laufen zu lassen.

### Woher die 2700 s kommen

Weil `heartbeat` bei uns den Zeitpunkt der Übernahme trägt und kein Lebenszeichen ist, muss die
Frist den **längsten legitimen Lauf** übersteigen — sonst wird ein gültiges Dokument
unterbrochen, erneut versucht, wieder unterbrochen und landet nach `processing_max_attempts`
auf `failed`, wo kein erneuter Upload hilft. Die Obergrenze ist rechenbar:

| Grösse | Wert | Quelle |
|---|---|---|
| Upload-Limit | 10 MiB | `MAX_UPLOAD_BYTES`, ADR-003 |
| Chunk-Dichte, dichtestes Korpusdokument | ~185 Chunks/MB | EU AI Act, 2,84 MB → 525 Chunks |
| Chunks bei 10 MB | ~1850 | |
| Batch-Grösse | 64, **sequenziell** abgearbeitet | `embedding.py`, `BATCH_SIZE` |
| Batches | ~29 | |
| Zeitlimit je Versuch | 30 s | `embedding.py`, `TIMEOUT_SECONDS` |
| Versuche je Batch | 1 + 2 Retries | `embedding.py`, `MAX_RETRIES` |

Der kritische Fall ist nicht der tote Provider — dann scheitert der Job selbst und wird sauber
`failed` — sondern der zähe: jeder Batch läuft einmal in sein Zeitlimit und gelingt im zweiten
Anlauf. Das sind ~29 × 60 s ≈ 1740 s für einen Lauf, der **erfolgreich** endet. 2700 s lässt
darüber Luft für Parsing, Chunking und den Chunk-Insert, ohne die Reparatur beliebig träge zu
machen. Die Zahl steht in `config` und ist über die Admin-API änderbar (US-11).

Der Preis ist Wiederherstellungslatenz: ein abgestürzter Lauf wird erst nach dieser Frist
befreit. Der Takt der Schleife ist deshalb bei 300 s gedeckelt statt an die Frist gekoppelt —
ein Pass ist eine indizierte Abfrage, und die Erkennung soll nicht mitwachsen, nur weil die
erzwungene Frist wächst.

Die eigentliche Auflösung dieses Zielkonflikts wäre ein Fortschritts-Zeitstempel, den der
Worker zwischen den Batches hochschreibt: dann misst der Reaper „seit X kein Fortschritt"
statt „seit X beansprucht", und X darf klein sein, unabhängig von der Gesamtdauer. Offen als
eigener Vorgang — umgesetzt im Nachtrag 2026-09-11 unten.

### Ein eigenes Versions-Token

Damit der Reaper eine Zeile anfassen kann, ohne einen eventuell doch noch lebenden Lauf still
zu verwerfen, hat der Optimistic-Lock des Workers eine eigene Spalte bekommen:
`documents.index_version` statt `updated_at` (Details in `08_ERD.md`). Zwei Schreiber zählen
sie hoch — der Upload, weil die Bytes neu sind, und der Reaper, weil er einen Lauf für tot
erklärt. Ein aufwachender Zombie-Job scheitert dadurch **deterministisch** an jeder
geschützten Schreiboperation, statt sich mit dem neuen Versuch um die Chunks zu streiten.

## Nachtrag 2026-09-11 — Fortschritt statt Übernahme (T-51, #106; T-61, #132)

Der vorherige Nachtrag hat den Zielkonflikt benannt, aber nicht aufgelöst: `heartbeat` trägt
den Übernahmezeitpunkt, nicht ein Lebenszeichen, also musste die Frist gleichzeitig „länger
als der längste legitime Lauf" und „kurz genug für eine zügige Reparatur" sein. 2700 s hat
diesen Konflikt zugunsten der ersten Hälfte entschieden — Wiederherstellung im schlechtesten
Fall nach ~45 Minuten, AK 4 aus #69 nur wahrscheinlich statt erzwungen.

**Die Auflösung:** `documents.index_progress_at`, eine neue Spalte, die der Worker selbst an
Phasengrenzen hochschreibt — nach dem Parsen, nach dem Chunking, nach jedem Embedding-Batch
(`mark_processing`/`note_progress` in `worker/main.py`), jeweils unter derselben
`index_version`-Bedingung wie jeder andere Schreibzugriff auf die Zeile. Der Reaper misst jetzt
„seit X kein Fortschritt" statt „seit X beansprucht" — die `NOT EXISTS`-Subquery gegen
`pgqueuer` samt JSON-Cast-Guard (Review zu #104) entfällt ersatzlos, `STUCK_DOCUMENTS`
vergleicht nur noch `d.index_progress_at` gegen `now() - make_interval(secs => $1)`.

Eine eigene Spalte statt eines aufgefrischten `pgqueuer.heartbeat`, weil Letzteres nicht an
`index_version` gebunden werden kann: die Zeile ist dokument-, nicht versionsgebunden, und ein
Worker, der die Verbindung verliert, gereapt wird und sich danach erholt, würde mit seiner
alten Zeile das Dokument dauerhaft „lebendig" halten — genau der Zustand, den der Mechanismus
beseitigen soll.

**Zwei Config-Keys statt einem:** `processing_timeout_seconds` (2700 s) behält seine
Bedeutung und Herleitung von oben unverändert, treibt aber nur noch
`DELETE_ORPHANED_PICKED_ROWS` (T-52) — den Sweep verwaister `pgqueuer`-Zeilen, der weiterhin
`heartbeat` liest. Ein neuer Key, `processing_stall_seconds` (300 s), entscheidet jetzt das
Reapen selbst. Der alte Key wird nicht umgedeutet: eine stillschweigende Umdeutung hätte jede
bestehende Installation unter ihrem alten, viel zu grossen Wert in die neue, viel strengere
Semantik gezwungen — dieselbe Deployment-Falle, die T-43 schon vermied, als es
`documents.index_version` statt `updated_at` einführte.

**Woher 300 s kommen — gemessen, nicht geschätzt**, gegen die grösste Lücke, die ein
gesunder Lauf zwischen zwei Fortschritts-Meldungen überbrücken können muss:

| Lücke | Wert | Quelle |
|---|---|---|
| Parsing (dichtestes Korpusdokument, auf 10 MiB skaliert, ~2100 Chunks) | ~29 s | gemessen, `parse_document` |
| Chunking derselben Menge | ~3 s | gemessen, `chunk_blocks` |
| `store_chunks` + `mark_available` (~1850 Chunks, echte DB) | ~5 s | gemessen |
| Ein Embedding-Batch, einmal im Zeitlimit, dann erfolgreich | **~120 s** | rechenbar: `TIMEOUT_SECONDS × (1 + MAX_RETRIES)` = 90 s + LiteLLM-Backoff |

Die Embedding-Lücke ist der harte Boden: darunter würde ein kerngesunder Lauf gereapt, dessen
Provider einmal zickt — genau der Fehlerfall, den die 2700-s-Herleitung oben vermeiden wollte.
`stall = max(120, 29, 3, 5) × 2 = 240 s`, aufgerundet auf **300 s** mit Reserve gegen
Backoff-Varianz. Der Takt der Schleife folgt jetzt `stall_seconds` (`min(max(stall/4, 5), 300)`)
statt `timeout_seconds`; Erkennungslatenz liegt damit bei `stall + Takt` ≈ 300 + 75 = 375 s,
statt bei bis zu 45 Minuten. Der Takt selbst sinkt damit gegenüber dem alten Default um das
Vierfache (300 s → 75 s) — ein zusätzlicher, indizierter Query alle 75 statt alle 300 s, laut
Kommentar über `REAPER_PASSES_PER_STALL` in `worker/main.py` bewusst in Kauf genommen, weil ein
Pass keine spürbare Last ist.

**Bekannte Restlücke:** die 300 s sind gegen `chunk_size = 512` (ADR-007-Default) gemessen.
`chunk_size` hat keinen DB-Constraint und ist nur per `psql` änderbar (`app/routers/admin.py`
nimmt ihn bewusst nicht in die Admin-API auf, siehe dortiger Kommentar) — ein sehr kleiner Wert
dort vervielfacht die Chunk-Zahl und damit Chunking- und Insert-Dauer, ohne dass ein
`note_progress`-Checkpoint innerhalb dieser beiden Phasen liegt. Unter dem alten 2700-s-Budget
folgenlos, unter 300 s könnte eine drastische `chunk_size`-Kalibrierung einen gesunden Lauf
reapen. Das ist eine Operator-Aktion (kein Admin-API-Pfad), keine Provider- oder Laststörung,
und ausserhalb des Scopes dieses Tickets — wer `chunk_size` kalibriert, sollte diese Kopplung
kennen.

**Zu US-04:** die 5 Minuten dort gelten dem Normalpfad Upload → verfügbar, nicht dem
Reparaturpfad. Vollständige Wiederherstellung eines abgestürzten Laufs ist Erkennung plus ein
kompletter Neulauf und kann die 5 Minuten grundsätzlich nicht halten. Das AK dieses Tickets
sagt entsprechend „innerhalb weniger Minuten erkannt", nicht „wiederhergestellt".

**T-61 (#132), in derselben Migration (0020) miterledigt:** `processing_timeout_seconds` stand
bis dahin nur nach unten begrenzt (`>= 1`) — belegt war, dass `999999` (~11,5 Tage) klaglos
angenommen wurde, was das Reapen (vor T-51) bzw. den Zeilen-Sweep (seither) faktisch
abschaltet, ohne dass irgendwo etwas rot wird. Beide Sekunden-Keys teilen sich jetzt einen
eigenen CHECK-Zweig mit Ober- **und** Untergrenze, `[120, 999999]`, vor dem `COUNT_KEYS`-Zweig
platziert (`CASE` nimmt den ersten Treffer). Die Grenzen sind gegen dieses Setup gemessen, nicht
geraten: `now() - make_interval(secs => $1)` überläuft bei ~2,127 × 10¹¹ s (~6739 Jahre vor
`now()`, Postgres' früheste darstellbare Zeit), die verdoppelte Variante des Sweeps
(`... * 2`) bei der Hälfte, ~1,063 × 10¹¹ s (~3369 Jahre) — beide vier Grössenordnungen über
der neuen Obergrenze. `read_reaper_config` klemmt zusätzlich in beide Richtungen, symmetrisch
zur bisherigen Untergrenze, für eine Datenbank, die älter als Migration 0020 ist.

---

*Abhängigkeiten: ADR-001 (Modularer Monolith), ADR-003 (PostgreSQL als einziger Persistenz-Service)*
*Löst auf: Offene Entscheidung aus ADR-Review (Celery+Redis-Widerspruch)*
