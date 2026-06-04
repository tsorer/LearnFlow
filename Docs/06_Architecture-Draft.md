# Architecture Draft — Finalisiert nach Peer Review
*LearnFlow · Modul 3 Tag 1 · LearnFlow-Team (Frank, Niklaus, Reto, Christoph) · 2026-05-31*
*Basis: ADR-001 bis ADR-009 · Angereichert mit Peer-Review-Erkenntnissen*

---

## Projektübersicht

LearnFlow ist eine interne RAG-Lernplattform für neue Mitarbeitende. Neue Mitarbeitende (Lara) stellen Fragen in natürlicher Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus. Bereichsverantwortliche (Stefan) laden Dokumente hoch und verwalten den Korpus. MVP: ein Pilot-Bereich, < 30 Nutzer, Single Instance, Business Hours, Deadline 30. September 2026.

---

## Top-3 Quality Attributes

| Rang | QA | Kernforderung |
|---|---|---|
| 1 | **Reliability** | Halluzinationsrate = 0 %; Out-of-Corpus-Erkennung ≥ 90 % „Weiss ich nicht"; Retrieval-Gate + mehrschichtiger Unterdrückungsmechanismus (Quellenprüfung → Konfidenz-Score → Self-Check); CI-Regressionsgate |
| 2 | **Security** | DSGVO — bei echten internen Dokumenten bleibt die Verarbeitung in der EU (Azure OpenAI EU); im MVP keine echten internen Dokumente, daher OpenAI Direct zulässig. JWT + bcrypt; RBAC (User / Admin); Pseudonymisierung von Feedback und Query-Logs; SSO nachrüstbar (Post-MVP). **DSGVO-Löschantrag-Workflow und Aufbewahrungsfristen → Post-MVP** (Entscheid 2026-06-04; Pilot < 30 interne Nutzer, kein produktiver Betrieb). |
| 3 | **Maintainability** | Schwellenwerte in DB ohne Code-Deployment änderbar; LLM-Provider-Wechsel per Konfiguration (LiteLLM); modulare RAG-Komponenten; Budget-kritisch: 360 h total |

---

## C1: Externe Akteure und Systeme

| Akteur / System | Rolle |
|---|---|
| **Lara** (Lernende) | Fragen stellen, Antworten lesen, Feedback geben, Quiz absolvieren |
| **Stefan** (Bereichsverantwortlicher) | Dokumente hochladen, Korpus verwalten, Quiz-Fragen freigeben, Stale-Inhalte validieren |
| **Admin** | Konfidenz- und Stale-Schwellenwerte konfigurieren |
| **LLM-Provider (via LiteLLM)** | LLM-Generierung (`gpt-4o-mini` Default, `gpt-4o` Upgrade) + Embeddings (`text-embedding-3-small`). MVP: OpenAI Direct (keine echten internen Dokumente); Produktion: Azure OpenAI EU (EU-Datenresidenz); OnPrem-Fallback: Ollama (`bge-m3`, lokal) |
| **Unternehmens-IdP** | SSO-Authentifizierung + Rollen-Sync via Azure AD / SAML 2.0 — Post-MVP |

---

## C2: Container-Entscheidungen (finalisiert)

| Container | Technologie | Begründung | Grösstes Risiko |
|---|---|---|---|
| **Web App** | React 18 / TypeScript 5 · Vite · Nginx | SPA mit Batch-Response-Integration (JSON), Quiz und Quellenhervorhebung | **MVP: Link auf Dokument + Seitenangabe** statt inline PDF.js-Highlighting (2026-06-03) — PDF.js Post-MVP |
| **API Server** | Python 3.13 / FastAPI (ASGI) | Async Batch-Response (JSON), Python-KI-Ökosystem, RBAC als Dependency Injection | Konfidenz-Scoring definiert (ADR-008 Accepted); **Prompt-Injection → Post-MVP** *(Peer Review; Grounding-Prompt als erste Mitigation)* |
| **Background Worker** | pgqueuer (PostgreSQL-nativer Job-Queue) | Asynchrones Dokument-Processing ohne Redis; Jobs transaktional, kein Datenverlust bei Crash | Kleine Community; Single-Threaded: parallele Uploads stauen Queue |
| **Datenbank** | PostgreSQL 17 + pgvector | Relationale Daten + Vektoren (HNSW) + Volltext (`tsvector`/GIN, deutsch) + Original-Dokumente in einem Service | **Single Point of Failure — kein Replica, kein Backup definiert** *(verschärft: Peer Review)* |

**Kommunikation:**
- Web App → API Server: REST (HTTPS, Batch-Response JSON) — synchron
- API Server → Datenbank: SQL via asyncpg (TCP 5432) — synchron
- API Server → Background Worker: pg_notify (TCP 5432) — asynchron
- Background Worker → Datenbank: SQL (TCP 5432) — synchron
- API Server → LLM-Provider (via LiteLLM): HTTPS — synchron mit Circuit Breaker (MVP: OpenAI Direct, Prod: Azure OpenAI EU)

**Versionsphilosophie:** bewusst stabil-abgehangen statt bleeding-edge. Python 3.13 (nicht 3.14) wegen ML-Wheel-Reife; React 18 und stabile APIs wegen höchster Trainingsdaten-Dichte → zuverlässigere KI-Generierung. PostgreSQL 17 aus Lebenszyklus-/Docker-Image-Gründen (pgvector ist versionsunabhängig).

---

## ADRs Übersicht (10 Entscheide)

| ADR | Entscheid | Status |
|---|---|---|
| **ADR-001** | Architekturstil: Modularer Monolith — kein Microservices-Overhead bei < 30 Nutzern und 360 h Budget | **Accepted** *(aktualisiert nach Peer Review)* |
| **ADR-002** | Backend/Frontend-Stack: Python 3.13 / FastAPI + React 18 / TypeScript 5 — Batch-Response JSON, Python-KI-Ökosystem direkt verfügbar | **Accepted** *(aktualisiert 2026-06-03: kein SSE-Streaming)* |
| **ADR-003** | Datenpersistenz: PostgreSQL 17 + pgvector — relationale Daten + Vektoren + Dokumente in einem Service, ein Backup, kein zweiter Service | Proposed |
| **ADR-004** | LLM-Provider: LiteLLM-Abstraktion — MVP: OpenAI Direct (keine echten internen Dokumente), Produktion: Azure OpenAI EU, OnPrem: Ollama; Wechsel per Konfigurationseintrag, kein Code-Change | Proposed |
| **ADR-005** | Embedding-Modell: `text-embedding-3-small` (1536 Dim; MVP via OpenAI Direct, Prod via Azure EU) / `bge-m3` (Ollama, 1024 Dim) — konfigurierbar via LiteLLM | Proposed |
| **ADR-006** | Background Worker: pgqueuer statt Celery + Redis — kein separater Broker, Jobs PostgreSQL-transaktional, ein Service weniger | Accepted |
| **ADR-007** | Retrieval: Struktur-bewusstes Chunking + Hybrid-Retrieval (Dense + Sparse, RRF) + Retrieval-Gate | Proposed |
| **ADR-008** | Reliability: Mehrstufige Konfidenzpipeline (fail-closed) — Retrieval-Gate → Konfidenz → Grounding-/Citation-Check → LLM-Self-Check | **Accepted** *(aktualisiert 2026-06-03)* |
| **ADR-009** | Eval-Strategie: Gold-Dataset (In-/Out-of-Corpus/Adversarial) + RAGAS + CI-Regressionsgate (Build bricht bei Halluzination > 0 %) | Proposed |
| **ADR-010** | API-Design-Ansatz: API-First mit OpenAPI 3.0 — `openapi.yaml` als Single Source of Truth; FastAPI Auto-Spec bewusst deaktiviert | **Accepted** *(2026-06-03)* |

> **Hinweis:** ADR-001, ADR-002, ADR-006, ADR-008 und ADR-010 sind «Accepted». Alle weiteren ADRs bleiben «Proposed» bis Tech Spike abgeschlossen.

---

## Datenarchitektur (ADR-003)

- **Ein Persistenz-Service:** PostgreSQL 17 für relationale Daten (`users`, `documents`, `feedback`, `config`, `quiz_questions`), Vektor-Embeddings (`embeddings` mit HNSW), Volltext-Index (`tsvector`/GIN) und Original-Dokumente (`bytea`, max. 10 MB).
- **Migrationen:** Alembic, versioniert in Git.
- **Konfiguration:** `config`-Tabelle hält alle Schwellenwerte → ohne Deployment kalibrierbar (Maintainability-NFA).
- **Constraint:** pgvector indexiert HNSW nur bis **2000 Dimensionen** (1536/1024 unkritisch; `text-embedding-3-large`/3072 erfordert Matryoshka-Reduktion oder `halfvec`).

---

## RAG-Pipeline — Kern der Reliability (ADR-007, -008)

### Indexierung (Background-Worker)
Parsing (pypdf/python-docx) → **struktur-bewusstes Chunking** (Überschrift > Absatz > Satz; Startwerte ~512 Token / 64 Overlap) → Embedding via LiteLLM → Schreiben von Chunks + Embeddings + `tsvector` → HNSW-Index. Chunk-Metadaten (Dokument-ID, Bereich, Quell-Position) für Quellenanzeige.

### Retrieval (ADR-007)
**Hybrid-Retrieval:** Dense (pgvector Cosine/HNSW) + Sparse (Postgres-Volltext `german`) → **Reciprocal Rank Fusion (RRF)**. Kandidaten `k=20` je Suche → Fusion → Gate → Top-`n=5` als Kontext.

### Reliability-Pipeline (ADR-008, fail-closed)

| Stufe | Mechanismus | Wirkung |
|---|---|---|
| 0 | **Retrieval-Gate** (ADR-007): kein Chunk über Similarity-Schwelle | → „Weiss ich nicht", kein LLM-Aufruf |
| 1 | **Retrieval-Konfidenz** (deterministisch) | unter Schwelle → „Weiss ich nicht" |
| 2 | **Grounding-/Citation-Check** (deterministisch, Coverage ≥ 50 %) | ungedeckt → unterdrückt |
| 3 | **LLM-Self-Check** (nur Grenzfälle) | ungedeckte Aussagen → unterdrückt |

**Komposit-Konfidenz** (Stufe 1 + 2) → 3-Band-Anzeige (Hoch/Mittel/Niedrig) für US-02. Grounding-Prompt zwingt das LLM, nur aus Kontext zu antworten und zu zitieren. Alle Schwellen in `config`.

---

## LLM- & Embedding-Integration (ADR-004, -005)

- **LiteLLM** normalisiert Provider → Wechsel OpenAI Direct ↔ Azure EU ↔ Ollama ist ein `config`-Eintrag, kein Code-Change.
- **MVP-Default: OpenAI Direct** — einfachste Anbindung (nur API-Key), zulässig, weil im MVP keine echten internen Dokumente verarbeitet werden.
- **Produktion: Azure OpenAI EU** — sobald echte interne Dokumente indexiert werden, gilt EU-Datenresidenz (beim Indexieren geht der *gesamte* Korpus an den Provider — datenintensivste Exposition). Umstellung = eine `config`-Zeile, harte Go-Live-Vorbedingung.
- **Modellwechsel** erzwingt vollständige Re-Indexierung (Dimensionsänderung = Schema-Migration).
- **Provider-Portabilität** ist auch in der Eval (LLM-as-Judge) und Konfidenz (keine Logprob-Abhängigkeit) durchgehalten.

---

## Background-Processing (ADR-006)

**pgqueuer** statt Celery + Redis: Jobs als persistierte PostgreSQL-Zeilen, Benachrichtigung via `pg_notify`. Kein Redis, kein zusätzlicher Service → Monolith-Ziel (ADR-001) erfüllt, ein Backup deckt alles. Erfüllt den 5-Minuten-SLA (US-04) für Dokumente ≤ 50 Seiten. Alternativen (procrastinate, `SKIP LOCKED`, ARQ/Dramatiq/SAQ) abgewogen.

---

## Neu aus Peer Review — Ergänzungen

| Befund | Massnahme | Priorität |
|---|---|---|
| **Backup-Strategie fehlt** | Täglicher `pg_dump` via Cron in Docker Compose — vor Pilot-Start implementieren | 🔴 Pflicht |
| **Prompt-Injection** | Bewusst als Post-MVP eingestuft (2026-06-03). Grounding-Prompt (ADR-007) und Fail-Closed-Pipeline (ADR-008) sind erste Mitigation. Vollständiges Input-Sanitizing und Prompt-Boundaries im API Server → Post-MVP. | ⏸ Post-MVP |
| ~~**Onboarding-Prozess undefiniert**~~ | ✅ **Gelöst (2026-06-04):** Pilotstart-Checkliste erstellt (`Ops/07_Pilotstart-Checkliste.md`) — DB-Script-Template, Account-Anlage, Provider-Umstellung, Backup-Verifikation und Smoke-Tests dokumentiert. | ✅ Erledigt |
| **Observability** | ✅ **Entscheid (2026-06-04):** Kein externer Service im MVP. Strukturiertes JSON-Logging (stdout → Docker-Log) + `GET /health`-Endpoint am API Server. Metriken über Eval-Runs (ADR-009). Post-MVP: Prometheus/Grafana oder Sentry. | ✅ Erledigt |
| **Go/No-Go-Kriterien für Tech Spike** | **Prozess (Entscheid 2026-06-04):** Team definiert Eval-Dataset und Mindest-Scores gemeinsam **vor** dem ersten Spike-Tag. Pflicht-Agenda-Punkt im Spike-Kick-off: (1) 20–30 Testfragen aus Pilot-Dokumenten manuell erstellen, (2) Mindest-Scores für Similarity-Threshold, Out-of-Corpus-Quote und Citation-Coverage gemeinsam festlegen, (3) Go/No-Go-Entscheid nach Spike dokumentieren. | 🟠 Prozess |
| ~~**E-Mail-Service für US-06 ungeklärt**~~ | ✅ **Gelöst (2026-06-04):** US-06 (Stale-Content-Erkennung + E-Mail-Report) als Post-MVP eingestuft. SMTP-Provider-Entscheid entfällt als MVP-Blocker. | ✅ Erledigt |
| ~~**`bytea` vs. Large Object (`lo`)**~~ | ✅ **Gelöst (2026-06-03):** `bytea` für MVP mit hartem 10 MB Limit (serverseitig, US-04 konform). `lo`-Evaluation entfällt. MinIO/S3 als Post-MVP-Option offen (ADR-003). | ✅ Erledigt |
| ~~**Streaming ↔ Grounding-Check**~~ | ✅ **Gelöst (2026-06-03):** Batch-Response — kein SSE-Streaming. Gesamte Konfidenzpipeline (ADR-008) läuft durch bevor Antwort ausgeliefert wird. ADR-002 aktualisiert. | ✅ Erledigt |
| **Provider-Umstellung vor echten Daten** | MVP nutzt OpenAI Direct (US); vor dem ersten echten internen Dokument auf Azure OpenAI EU umstellen (LiteLLM-`config`). Go-Live-Checklist + optionaler Guard gegen Nicht-EU-Provider bei „intern/produktiv" markiertem Korpus (ADR-004/005) | 🔴 Compliance |

---

## Offene Fragen für Tag 2

1. ~~**Konfidenz-Scoring-Mechanismus festlegen**~~ — ✅ **Gelöst (2026-06-03):** ADR-008 Accepted. Mehrstufige Defense-in-Depth: Retrieval-Gate → Retrieval-Konfidenz (deterministisch) → Grounding-/Citation-Check (deterministisch) → LLM-Self-Check (nur Grenzfälle). Schwellenwerte in `config`-Tabelle. Kalibrierung via Tech Spike.

2. **Chunking- und Retrieval-Parameter entscheiden** — Chunk-Grösse (256/512/1024), Overlap, Similarity-Schwelle, Citation-Coverage, Top-`k`/`n`, RRF-`k` sind Hypothesen (ADR-007/008) und müssen vor Sprint 1 durch Tech Spike kalibriert werden.

3. **Quellenhervorhebung scope-en** — PDF.js im Browser oder reduzierter MVP-Scope («Link öffnet Dokument, kein Highlighting»)? Entscheidung beeinflusst Frontend-Aufwand um 2–3 Wochen.

4. **Produktions-Embedding-Modell bestätigen** — `text-embedding-3-small` vs. `-large` vs. dediziert multilingual auf echten deutschen Fachtexten messen (inkl. HNSW-2000-Dim-Constraint, ADR-005).

5. **„0 % Halluzination" vs. statistische Realität** (ADR-009) — auf endlichem Dataset nur demonstrierbar, nicht beweisbar. Die NFA-Formulierung sollte als „0 % auf Eval-Set + Produktions-Monitoring" präzisiert werden.

---

*Basis: 04_ADR-001 bis 04_ADR-009 · Peer Review: 04_ADR-Review_Kritik.md*
*Quellen: [05_C4-C1_System-Context.md](05_C4-C1_System-Context.md) · [05_C4-C2_Container.md](05_C4-C2_Container.md) · [03_QualityAttributes.md](03_QualityAttributes.md) · 04_ADR-001 bis 04_ADR-009*
