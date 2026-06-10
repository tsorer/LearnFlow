# Architecture Draft — Finalisiert nach Peer Review
*LearnFlow · Modul 3 Tag 1 · Reto Stucki · 2026-05-31*
*Basis: L3_Output · Angereichert mit Peer-Review-Erkenntnissen aus L4*

---

## Projektübersicht

LearnFlow ist eine interne RAG-Lernplattform für neue Mitarbeitende. Neue Mitarbeitende (Lara) stellen Fragen in natürlicher Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus. Bereichsverantwortliche (Stefan) laden Dokumente hoch und verwalten den Korpus. MVP: ein Pilot-Bereich, < 30 Nutzer, Single Instance, Business Hours, Deadline 30. September 2026.

---

## Top-3 Quality Attributes

| Rang | QA | Kernforderung |
|---|---|---|
| 1 | **Reliability** | Halluzinationsrate = 0 %; Out-of-Corpus-Erkennung ≥ 90 % „Weiss ich nicht"; Circuit Breaker für LLM; mehrschichtiger Unterdrückungsmechanismus (Quellenprüfung → Konfidenz-Score → Self-Check) |
| 2 | **Security** | DSGVO — Daten verlassen EU nicht; JWT + bcrypt; RBAC (User / Admin); Pseudonymisierung von Feedback und Query-Logs; SSO nachrüstbar (Post-MVP) |
| 3 | **Maintainability** | Schwellenwerte in DB ohne Code-Deployment änderbar; LLM-Provider-Wechsel per Konfiguration (LiteLLM); modulare RAG-Komponenten; Budget-kritisch: 360–480 h total |

---

## C1: Externe Akteure und Systeme

| Akteur / System | Rolle |
|---|---|
| **Lara** (Lernende) | Fragen stellen, Antworten lesen, Feedback geben, Quiz absolvieren |
| **Stefan** (Bereichsverantwortlicher) | Dokumente hochladen, Korpus verwalten, Quiz-Fragen freigeben, Stale-Inhalte validieren |
| **Admin** | Konfidenz- und Stale-Schwellenwerte konfigurieren |
| **OpenAI API** | LLM-Generierung (gpt-4o-mini) + Embeddings (text-embedding-3-small) via LiteLLM; Fallback: Ollama (lokal, DSGVO-kritische Deployments) |
| **Unternehmens-IdP** | SSO-Authentifizierung + Rollen-Sync via Azure AD / SAML 2.0 — Post-MVP |

---

## C2: Container-Entscheidungen (finalisiert)

| Container | Technologie | Begründung | Grösstes Risiko |
|---|---|---|---|
| **Web App** | React 18 / TypeScript 5 · Nginx | SSE-native SPA für Token-by-Token Q&A, Quiz und Quellenhervorhebung | Quellenhervorhebung in PDFs (PDF.js) unterschätzt → **MVP-Scope noch zu klären** |
| **API Server** | Python 3.12 / FastAPI (ASGI) | Async SSE-Streaming, Python-KI-Ökosystem, RBAC als Dependency Injection | Konfidenz-Scoring konzeptionell noch undefiniert; **Prompt-Injection nicht adressiert** *(neu: Peer Review)* |
| **Background Worker** | pgqueuer (PostgreSQL-nativer Job-Queue) | Asynchrones Dokument-Processing ohne Redis; Jobs transaktional, kein Datenverlust bei Crash | Kleine Community; Single-Threaded: parallele Uploads stauen Queue |
| **Datenbank** | PostgreSQL 16 + pgvector | Relationale Daten + Vektoren + Original-Dokumente in einem Service; HNSW-Index für Similarity Search | **Single Point of Failure — kein Replica, kein Backup definiert** *(verschärft: Peer Review)* |

**Kommunikation:**
- Web App → API Server: REST + SSE (HTTPS) — synchron/streaming
- API Server → Datenbank: SQL via asyncpg (TCP 5432) — synchron
- API Server → Background Worker: pg_notify (TCP 5432) — asynchron
- Background Worker → Datenbank: SQL (TCP 5432) — synchron
- API Server → OpenAI API: HTTPS via LiteLLM — synchron mit Circuit Breaker

---

## ADRs Übersicht (6 Entscheide)

| ADR | Entscheid | Status |
|---|---|---|
| **ADR-001** | Architekturstil: Modularer Monolith — kein Microservices-Overhead bei < 30 Nutzern und 360 h Budget | **Accepted** *(aktualisiert nach Peer Review)* |
| **ADR-002** | Backend/Frontend-Stack: Python 3.12 / FastAPI + React 18 / TypeScript 5 — async SSE-native, Python-KI-Ökosystem direkt verfügbar | Proposed |
| **ADR-003** | Datenpersistenz: PostgreSQL 16 + pgvector — relationale Daten + Vektoren + Dokumente in einem Service, ein Backup, kein zweiter Service | Proposed |
| **ADR-004** | LLM-Provider: OpenAI API + LiteLLM-Abstraktion — Provider-Wechsel (OpenAI ↔ Ollama) per Konfigurationseintrag, kein Code-Change | Proposed |
| **ADR-005** | Embedding-Modell: text-embedding-3-small (OpenAI) / nomic-embed-text (Ollama) — konfigurierbar via LiteLLM | Proposed |
| **ADR-006** | Background Worker: pgqueuer statt Celery + Redis — kein separater Broker, Jobs PostgreSQL-transaktional, ein Service weniger | Accepted |

> **Hinweis:** ADR-001 Status von «Proposed» auf «Accepted» aktualisiert — Peer Review hat keine offenen Gegargumente ergeben. Alle weiteren ADRs bleiben «Proposed» bis Tech Spike abgeschlossen.

---

## Neu aus Peer Review — Ergänzungen

| Befund | Massnahme | Priorität |
|---|---|---|
| **Backup-Strategie fehlt** | Täglicher `pg_dump` via Cron in Docker Compose — vor Pilot-Start implementieren | 🔴 Pflicht |
| **Prompt-Injection nicht adressiert** | Input-Sanitizing und Prompt-Boundaries im API Server definieren — Sprint 1 | 🟠 Security |
| **Onboarding-Prozess undefiniert** | Wer legt Stefans Account per DB-Script an? Pilot-Start-Checkliste erstellen | 🟠 Prozess |
| **Go/No-Go-Kriterien für Tech Spike fehlen** | Evaluationsdataset + Mindest-Scores definieren bevor Spike startet | 🔴 Blocker |
| **E-Mail-Service für US-06 ungeklärt** | SMTP-Provider-Entscheid vor US-06-Implementierung — Sprint 0 | 🟠 Abhängigkeit |

---

## Offene Fragen für Tag 2

1. **Konfidenz-Scoring-Mechanismus festlegen** — Self-Check: LLM-Selbstevaluation oder semantische Ähnlichkeit? Vorrang-Reihenfolge der drei Unterdrückungsmechanismen definieren. Blocker für US-02 und Tech Spike.

2. **Chunking-Strategie entscheiden** — Fixed-Size vs. Sentence-Based vs. Semantic Chunking. Beeinflusst Retrieval-Qualität direkt. Muss vor Sprint 1 durch Tech Spike beantwortet sein.

3. **Quellenhervorhebung scope-en** — PDF.js im Browser oder reduzierter MVP-Scope («Link öffnet Dokument, kein Highlighting»)? Entscheidung beeinflusst Frontend-Aufwand um 2–3 Wochen.

---

*Basis: [Modul3Tag1_Lab_L3_Output.md](Modul3Tag1_Lab_L3_Output.md) · Peer Review: [Modul3Tag1_Lab_L4_Output.md](Modul3Tag1_Lab_L4_Output.md)*
*Quellen: [Docs/05_C4-C2_Container.md](../../Docs/05_C4-C2_Container.md) · [Docs/03_QualityAttributes.md](../../Docs/03_QualityAttributes.md) · [Docs/04_ADR-001 bis 04_ADR-006](../../Docs/)*
