# Architecture Draft — Finalisiert nach Peer Review
*LearnFlow · Modul 3 Tag 1 · LearnFlow-Team (Frank, Niklaus, Reto) · 2026-05-31*
*Basis: ADR-001 bis ADR-009 · Angereichert mit Peer-Review-Erkenntnissen*

---

## Projektübersicht

LearnFlow ist eine interne RAG-Lernplattform für neue Mitarbeitende. Neue Mitarbeitende (Lara) stellen Fragen in natürlicher Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus. Bereichsverantwortliche (Stefan) laden Dokumente hoch und verwalten den Korpus. MVP: ein Pilot-Bereich, < 30 Nutzer, Single Instance, Business Hours, Deadline 30. September 2026.

---

## Top-3 Quality Attributes

| Rang | QA | Kernforderung |
|---|---|---|
| 1 | **Reliability** | Halluzinationsrate = 0 %; Out-of-Corpus-Erkennung ≥ 90 % „Weiss ich nicht"; Retrieval-Gate + mehrschichtiger Unterdrückungsmechanismus (Quellenprüfung → Konfidenz-Score → Self-Check); CI-Regressionsgate |
| 2 | **Security** | DSGVO — Daten verlassen EU nicht (Azure OpenAI EU); JWT + bcrypt; RBAC (User / Admin); Pseudonymisierung von Feedback und Query-Logs; SSO nachrüstbar (Post-MVP) |
| 3 | **Maintainability** | Schwellenwerte in DB ohne Code-Deployment änderbar; LLM-Provider-Wechsel per Konfiguration (LiteLLM); modulare RAG-Komponenten; Budget-kritisch: 360 h total |

---

## C1: Externe Akteure und Systeme

| Akteur / System | Rolle |
|---|---|
| **Lara** (Lernende) | Fragen stellen, Antworten lesen, Feedback geben, Quiz absolvieren |
| **Stefan** (Bereichsverantwortlicher) | Dokumente hochladen, Korpus verwalten, Quiz-Fragen freigeben, Stale-Inhalte validieren |
| **Admin** | Konfidenz- und Stale-Schwellenwerte konfigurieren |
| **Azure OpenAI EU** | LLM-Generierung (`gpt-4o-mini` Default, `gpt-4o` Upgrade) + Embeddings (`text-embedding-3-small`) via LiteLLM; Fallback: Ollama (`bge-m3`, lokal/OnPrem, DSGVO-kritische Deployments) |
| **Unternehmens-IdP** | SSO-Authentifizierung + Rollen-Sync via Azure AD / SAML 2.0 — Post-MVP |

---

## C2: Container-Entscheidungen (finalisiert)

| Container | Technologie | Begründung | Grösstes Risiko |
|---|---|---|---|
| **Web App** | React 18 / TypeScript 5 · Vite · Nginx | SSE-native SPA für Token-by-Token Q&A, Quiz und Quellenhervorhebung | Quellenhervorhebung in PDFs (PDF.js) unterschätzt → **MVP-Scope noch zu klären** |
| **API Server** | Python 3.13 / FastAPI (ASGI) | Async SSE-Streaming, Python-KI-Ökosystem, RBAC als Dependency Injection | Konfidenz-Scoring konzeptionell noch undefiniert; **Prompt-Injection nicht adressiert** *(Peer Review)* |
| **Background Worker** | pgqueuer (PostgreSQL-nativer Job-Queue) | Asynchrones Dokument-Processing ohne Redis; Jobs transaktional, kein Datenverlust bei Crash | Kleine Community; Single-Threaded: parallele Uploads stauen Queue |
| **Datenbank** | PostgreSQL 17 + pgvector | Relationale Daten + Vektoren (HNSW) + Volltext (`tsvector`/GIN, deutsch) + Original-Dokumente in einem Service | **Single Point of Failure — kein Replica, kein Backup definiert** *(verschärft: Peer Review)* |

**Kommunikation:**
- Web App → API Server: REST + SSE (HTTPS) — synchron/streaming
- API Server → Datenbank: SQL via asyncpg (TCP 5432) — synchron
- API Server → Background Worker: pg_notify (TCP 5432) — asynchron
- Background Worker → Datenbank: SQL (TCP 5432) — synchron
- API Server → Azure OpenAI EU: HTTPS via LiteLLM — synchron mit Circuit Breaker

**Versionsphilosophie:** bewusst stabil-abgehangen statt bleeding-edge. Python 3.13 (nicht 3.14) wegen ML-Wheel-Reife; React 18 und stabile APIs wegen höchster Trainingsdaten-Dichte → zuverlässigere KI-Generierung. PostgreSQL 17 aus Lebenszyklus-/Docker-Image-Gründen (pgvector ist versionsunabhängig).

---

## ADRs Übersicht (9 Entscheide)

| ADR | Entscheid | Status |
|---|---|---|
| **ADR-001** | Architekturstil: Modularer Monolith — kein Microservices-Overhead bei < 30 Nutzern und 360 h Budget | **Accepted** *(aktualisiert nach Peer Review)* |
| **ADR-002** | Backend/Frontend-Stack: Python 3.13 / FastAPI + React 18 / TypeScript 5 — async SSE-native, Python-KI-Ökosystem direkt verfügbar | Proposed |
| **ADR-003** | Datenpersistenz: PostgreSQL 17 + pgvector — relationale Daten + Vektoren + Dokumente in einem Service, ein Backup, kein zweiter Service | Proposed |
| **ADR-004** | LLM-Provider: Azure OpenAI EU + LiteLLM-Abstraktion — Provider-Wechsel (Azure EU ↔ OpenAI Direct ↔ Ollama) per Konfigurationseintrag, kein Code-Change | Proposed |
| **ADR-005** | Embedding-Modell: `text-embedding-3-small` (Azure EU, 1536 Dim) / `bge-m3` (Ollama, 1024 Dim) — konfigurierbar via LiteLLM | Proposed |
| **ADR-006** | Background Worker: pgqueuer statt Celery + Redis — kein separater Broker, Jobs PostgreSQL-transaktional, ein Service weniger | Accepted |
| **ADR-007** | Retrieval: Struktur-bewusstes Chunking + Hybrid-Retrieval (Dense + Sparse, RRF) + Retrieval-Gate | Proposed |
| **ADR-008** | Reliability: Mehrstufige Konfidenzpipeline (fail-closed) — Retrieval-Gate → Konfidenz → Grounding-/Citation-Check → LLM-Self-Check | Proposed |
| **ADR-009** | Eval-Strategie: Gold-Dataset (In-/Out-of-Corpus/Adversarial) + RAGAS + CI-Regressionsgate (Build bricht bei Halluzination > 0 %) | Proposed |

> **Hinweis:** ADR-001 Status von «Proposed» auf «Accepted» aktualisiert — Peer Review hat keine offenen Gegenargumente ergeben. ADR-006 ist «Accepted». Alle weiteren ADRs bleiben «Proposed» bis Tech Spike abgeschlossen.

---

## Datenarchitektur (ADR-003)

- **Ein Persistenz-Service:** PostgreSQL 17 für relationale Daten (`users`, `documents`, `feedback`, `config`, `quiz_questions`), Vektor-Embeddings (`embeddings` mit HNSW), Volltext-Index (`tsvector`/GIN) und Original-Dokumente (`bytea`).
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

- **LiteLLM** normalisiert Provider → Wechsel Azure EU ↔ OpenAI Direct ↔ Ollama ist ein `config`-Eintrag, kein Code-Change.
- **EU-Datenresidenz als Default** (Azure OpenAI EU), da interne Dokumente verarbeitet werden — beim Indexieren geht der *gesamte* Korpus an den Provider (datenintensivste Exposition).
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
| **Prompt-Injection nicht adressiert** | Input-Sanitizing und Prompt-Boundaries im API Server definieren — Sprint 1 | 🟠 Security |
| **Onboarding-Prozess undefiniert** | Wer legt Stefans Account per DB-Script an? Pilot-Start-Checkliste erstellen | 🟠 Prozess |
| **Go/No-Go-Kriterien für Tech Spike fehlen** | Evaluationsdataset + Mindest-Scores definieren bevor Spike startet | 🔴 Blocker |
| **E-Mail-Service für US-06 ungeklärt** | SMTP-Provider-Entscheid vor US-06-Implementierung — Sprint 0 | 🟠 Abhängigkeit |
| **`bytea` vs. Large Object (`lo`)** | RAM-/WAL-Verhalten für grosse PDFs prüfen — vor Schema-Erstellung entscheiden (ADR-003) | 🔴 Blocker |
| **Streaming ↔ Grounding-Check** | Fail-closed (ADR-008) vs. Token-Streaming (Performance-Anforderung, ≤ 10 s @ p95) auflösen: generieren-dann-streamen vs. In-Stream-Korrektur | 🟠 Architektur |

---

## Offene Fragen für Tag 2

1. **Konfidenz-Scoring-Mechanismus festlegen** — Self-Check: LLM-Selbstevaluation oder semantische Ähnlichkeit? Vorrang-Reihenfolge der Unterdrückungsmechanismen (ADR-008) definieren. Blocker für US-02 und Tech Spike.

2. **Chunking- und Retrieval-Parameter entscheiden** — Chunk-Grösse (256/512/1024), Overlap, Similarity-Schwelle, Citation-Coverage, Top-`k`/`n`, RRF-`k` sind Hypothesen (ADR-007/008) und müssen vor Sprint 1 durch Tech Spike kalibriert werden.

3. **Quellenhervorhebung scope-en** — PDF.js im Browser oder reduzierter MVP-Scope («Link öffnet Dokument, kein Highlighting»)? Entscheidung beeinflusst Frontend-Aufwand um 2–3 Wochen.

4. **Produktions-Embedding-Modell bestätigen** — `text-embedding-3-small` vs. `-large` vs. dediziert multilingual auf echten deutschen Fachtexten messen (inkl. HNSW-2000-Dim-Constraint, ADR-005).

5. **„0 % Halluzination" vs. statistische Realität** (ADR-009) — auf endlichem Dataset nur demonstrierbar, nicht beweisbar. Die NFA-Formulierung sollte als „0 % auf Eval-Set + Produktions-Monitoring" präzisiert werden.

---

*Basis: 04_ADR-001 bis 04_ADR-009 · Peer Review: 04_ADR-Review_Kritik.md*
*Quellen: [05_C4-C1_System-Context.md](05_C4-C1_System-Context.md) · [05_C4-C2_Container.md](05_C4-C2_Container.md) · [03_QualityAttributes.md](03_QualityAttributes.md) · 04_ADR-001 bis 04_ADR-009*
