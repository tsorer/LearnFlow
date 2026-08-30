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

Damit der Reaper eine Zeile anfassen kann, ohne einen eventuell doch noch lebenden Lauf still
zu verwerfen, hat der Optimistic-Lock des Workers eine eigene Spalte bekommen:
`documents.index_version` statt `updated_at` (Details in `08_ERD.md`). Zwei Schreiber zählen
sie hoch — der Upload, weil die Bytes neu sind, und der Reaper, weil er einen Lauf für tot
erklärt. Ein aufwachender Zombie-Job scheitert dadurch **deterministisch** an jeder
geschützten Schreiboperation, statt sich mit dem neuen Versuch um die Chunks zu streiten.

---

*Abhängigkeiten: ADR-001 (Modularer Monolith), ADR-003 (PostgreSQL als einziger Persistenz-Service)*
*Löst auf: Offene Entscheidung aus ADR-Review (Celery+Redis-Widerspruch)*
