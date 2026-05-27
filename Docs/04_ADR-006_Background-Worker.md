# ADR-006: Background Worker — pgqueuer statt Celery + Redis

| Feld | Inhalt |
|---|---|
| **Status** | Accepted |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

US-04 verlangt, dass Dokumente nach dem Upload innerhalb von 5 Minuten als Quelle verfügbar sind. Das Processing-Pipeline (Parsing → Chunking → Embedding → pgvector-Indexierung) ist zu aufwändig, um synchron im HTTP-Request ausgeführt zu werden — der Upload würde für grosse Dokumente blockieren. Es braucht deshalb einen Background Worker, der Jobs asynchron abarbeitet.

ADR-001 hat einen modularen Monolithen mit einem einzigen Deployment-Artefakt als Ziel definiert. ADR-002 nannte Celery + Redis als Mitigation für persistente Jobs — ohne diesen Widerspruch zu ADR-001 explizit aufzulösen. Der ADR-Review hat diesen Konflikt als offene Entscheidung mit hoher Priorität markiert.

LearnFlow hat genau **einen Job-Typ**: ein Dokument verarbeiten. Das Volumen ist gering (< 30 Pilotnutzer, 1 Bereich). Betriebskomplexität ist teuer bei 360 h Gesamtbudget.

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
pgqueuer via `pg_notify` reagiert in Millisekunden auf neue Jobs. Der Throughput-Engpass liegt beim Embedding-API-Call (OpenAI Rate Limit), nicht beim Queue-Mechanismus. pgqueuer ist für dieses Volumen mehr als ausreichend.

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

## Abgewogene Alternative

| Alternative | Warum verworfen |
|---|---|
| **Celery + Redis** | Zwei zusätzliche Deployment-Artefakte widersprechen ADR-001. Redis bringt keinen Mehrwert für einen einzigen Job-Typ bei < 30 Nutzern. Job-Persistenz muss explizit konfiguriert werden. Operativer Overhead steht in keinem Verhältnis zum Nutzen. |

---

## Auswirkung auf Docs/04_C4_C2_Container.md

Der Container-Diagram-Eintrag für den Worker ist damit konkretisiert:

- **Container:** Background Worker — `pgqueuer` (Python-Library)
- **Kommunikation API → Worker:** `pg_notify` via PostgreSQL (kein Redis-Broker)
- **Deployment:** 4 Container total: `webapp`, `api`, `worker`, `db` — kein `redis`

---

*Abhängigkeiten: ADR-001 (Modularer Monolith), ADR-003 (PostgreSQL als einziger Persistenz-Service)*
*Löst auf: Offene Entscheidung aus ADR-Review (Celery+Redis-Widerspruch)*
