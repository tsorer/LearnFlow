# Advocatus Diaboli — Modularer Monolith
*LearnFlow · BFH CAS ADAI 2026 · Modul 3 Tag 2*

---

## Prompt

> Wir haben uns für Modularer Monolith entschieden.
>
> Spiele jetzt den Advocatus Diaboli:
> 1. Warum ist diese Entscheidung für uns FALSCH?
> 2. Was werden wir in 6 Monaten bereuen?
> 3. Welches Pattern wäre ehrlich gesagt besser — und warum?
> 4. Was müssen wir tun damit unsere Wahl wirklich funktioniert?

---

## Resultat

### 1. Warum diese Entscheidung FALSCH ist

**Der Kernfehler: LearnFlow ist kein Web-App mit einem KI-Feature. Es ist eine KI-Pipeline mit einer Web-UI.**

Die RAG-Pipeline (Chunking → Embedding → Retrieval → LLM-Generierung → Konfidenz-Check) hat fundamental andere Ressourcen-Charakteristiken als Auth, Quiz und Feedback:

| Modul | CPU | Memory | Latenz | Skalierungsbedarf |
|---|---|---|---|---|
| Auth / CRUD | niedrig | niedrig | ms | gleichmäßig |
| Quiz / Feedback | niedrig | niedrig | ms | gleichmäßig |
| **RAG-Pipeline** | **hoch (Chunking)** | **hoch (bytea, Embeddings)** | **variabel 0.1s–10s** | **burstweise** |
| **Background Worker** | **sehr hoch (Bulk-Upload)** | **sehr hoch** | **Minuten** | **stark burstweise** |

Diese unterschiedlichen Profile in einen Prozess zu zwingen bedeutet: Stefan lädt 20 Dokumente hoch → der Background Worker hammert CPU und Memory → Laras Query-Antwortzeit steigt auf 15 Sekunden → Performance-NFA verletzt. Im Monolithen kannst du das nicht isolieren.

**Zweiter Fehler: Das Modul-Grenz-Versprechen ist in einem 360h KI-generierten Projekt nicht haltbar.** ADR-001 sagt selbst: *„Disziplin erforderlich."* Claude Code ist kein disziplinierter Entwickler — es nimmt den kürzesten Weg. Ohne technisch erzwungene Grenzen (separate Packages, Import-Linting) entsteht in 10 Wochen ein klassischer Big-Ball-of-Mud. Genau das, was ADR-001 ausschließen will.

**Dritter Fehler — teilweise revidiert:** ADR-001 verkauft „ein Deployment-Artefakt" und `docker-compose.yml` hat vier Container. Allerdings ist die Trennung `webapp` / `api` schlicht Standard-Web-Architektur (statischer React-Build auf Nginx vs. Python-Runtime) — kein Architektur-Argument. Und der `worker` muss kein eigener Container sein: pgqueuer unterstützt einen eingebetteten Modus als `asyncio`-Background-Coroutine direkt im FastAPI-Prozess. Mit drei Containern (`webapp`, `api+worker`, `db`) ist das Monolith-Versprechen tatsächlich einlösbar. Das schwächt diesen Punkt — die zwei stärkeren Argumente bleiben die Ressourcen-Isolation und das Streaming-Grounding-Paradox.

---

### 2. Was ihr in 6 Monaten bereuen werdet

**Das Streaming-Grounding-Paradox wird euch einholen.** Architecture Draft Anhang A.2/8 nennt es selbst: Fail-closed (ADR-008) verlangt die Antwort *vor* Auslieferung zu prüfen. Token-by-Token-Streaming (ADR-002) liefert *während* der Generierung aus. Im Monolithen ist das ein architektonischer Widerspruch im selben Prozess — ihr werdet entweder die Performance-NFA oder die Reliability-NFA opfern müssen. Das ist kein Implementierungsdetail, das ist ein fundamentaler Zielkonflikt.

**Das `bytea`-Problem wird zur RAM-Zeitbombe.** 100 MB PDF als `bytea` → jeder SELECT lädt das komplette Binary in den PostgreSQL-Arbeitsspeicher. Fünf gleichzeitige Downloads = 500 MB RAM-Spike auf dem DB-Server. Im Monolithen teilen sich API, Worker und DB denselben Stack — ein RAM-Peak des Workers macht den Query-Pfad träge. Mit isolierten Services wäre das ein Worker-Problem, nicht ein User-Problem.

**Das Debugging wird zur Expedition.** Wenn ADR-009 im CI schlägt — Halluzinationsrate über 0 % — müsst ihr in einem Log finden, wo in der 4-stufigen Pipeline (Retrieval-Gate → Konfidenz → Citation-Check → Self-Check) es gerissen hat. Ohne Korrelations-IDs und ohne Service-Isolation sind diese Logs ein Rauschen aus Auth-Events, Quiz-Anfragen und RAG-Traces.

**Der Embedding-Modell-Wechsel wird teurer als erwartet.** ADR-005 sagt: Modellwechsel = vollständige Re-Indexierung. Im Monolithen blockiert das Migrationsscript die gesamte Anwendung. Mit einem isolierten RAG-Service läuft die Re-Indexierung im Hintergrund, während die Applikation noch läuft.

---

### 3. Welches Pattern wäre ehrlich gesagt besser

Nicht Microservices — das wäre das falsche Gegenmittel. Die ehrliche Antwort:

**Backend-for-Frontend (BFF) + RAG-Service — zwei Services, nicht neun.**

```
┌─────────────────────────────────┐   ┌──────────────────────────────────┐
│  App-Service                    │   │  RAG-Service                     │
│  FastAPI                        │   │  FastAPI                         │
│                                 │   │                                  │
│  - Auth (JWT/RBAC)              │   │  - Hybrid-Retrieval (ADR-007)    │
│  - Dokument-Upload/-Management  │──►│  - Konfidenzpipeline (ADR-008)   │
│  - Quiz-Management              │   │  - LLM-Generierung (LiteLLM)     │
│  - Feedback                     │   │  - Embedding-Generierung         │
│  - Admin-UI                     │   │  - Background-Worker (pgqueuer)  │
│  - Stale-Validierung            │   │                                  │
└─────────────────────────────────┘   └──────────────────────────────────┘
         │                                         │
         └───────────────┬─────────────────────────┘
                         │
                  PostgreSQL 17
```

**Warum das besser ist:**
- RAG-Service kann unabhängig skaliert, deployed und getestet werden
- Streaming-Problem lösbar: RAG-Service buffert intern, streamt dann — ohne den App-Service zu berühren
- Eval (ADR-009) kann gegen den RAG-Service isoliert laufen — kein Full-Stack-Spin-up im CI
- Chunking-Parameter-Wechsel betrifft nur den RAG-Service
- Die 360h-Budget-Aussage hält trotzdem: zwei FastAPI-Services sind nicht zwei Microservice-Organisationen

Docker Compose bleibt — `docker-compose.yml` hätte fünf statt vier Container. Der Ops-Overhead gegenüber heute: eine zweite FastAPI-Instanz und eine interne HTTP-Route.

---

### 4. Was ihr tun müsst damit eure Wahl wirklich funktioniert

Wenn ihr beim Modularen Monolithen bleibt, braucht ihr vier harte Massnahmen — keine Empfehlungen, Bedingungen:

**1. Technisch erzwungene Modul-Grenzen, nicht Konventionen.**
Separate Python-Packages pro Modul (`app/rag/`, `app/auth/`, `app/quiz/` etc.) mit explizitem `__all__` und einem Ratchet-Linting-Test der direkte DB-Calls über Modul-Grenzen als Build-Fehler markiert. Sonst bricht Claude Code die Grenzen beim ersten Zeitdruck.

**2. Streaming-Grounding-Widerspruch vor Sprint 1 lösen** — nicht im Spike, *vor* dem Spike. Die Entscheidung ist: (a) erst generieren, dann prüfen, dann als Batch-SSE senden (höhere initiale Latenz, korrekte Grounding-Garantie) oder (b) optimistisches Streaming mit nachträglichem Abbruch-Signal. Beides ist implementierbar — aber die Wahl beeinflusst den gesamten API-Contract und das Frontend-Design. Wer das nicht entscheidet, baut zweimal.

**3. Korrelations-IDs von Tag 1.** Jede Anfrage erhält eine UUID die durch Auth → Retrieval → LLM → Citation-Check durchgereicht und in jeden Log-Eintrag geschrieben wird. Im Monolithen ist das die einzige Art, einen einzelnen RAG-Request in Produktions-Logs zu rekonstruieren. Nachträglich einbauen kostet dreimal so viel.

**4. `bytea`-Entscheidung vor dem Schema** — Large Object (`lo`) oder externes Storage-Konzept (auch wenn es ein lokaler Ordner ist) entscheiden, *bevor* Alembic die erste Migration schreibt. Ein nachträglicher `bytea` → `lo`-Umbau auf einer befüllten Datenbank ist eine aufwendige Migration mit Downtime.

---

**Zusammenfassung in einem Satz:** Der Modulare Monolith ist die richtige Entscheidung für eure Auth-, Quiz- und Feedback-Module — aber die falsche Entscheidung für eure RAG-Pipeline, die ihr gedanklich als „ein Modul wie die anderen" behandelt.

---

*Quelle: Architektur-Diskussion Claude Code · Basis: ADR-001 bis ADR-009, Architecture Draft · 2026-06-03*
