# L3 · Architecture Draft zusammenführen
*LearnFlow · Modul 3 Tag 1 · Reto Stucki · 2026-05-31*

---

## Projektübersicht

LearnFlow ist eine interne RAG-Lernplattform für neue Mitarbeitende. Neue Mitarbeitende (Lara) stellen Fragen in natürlicher Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus. Bereichsverantwortliche (Stefan) laden Dokumente hoch und verwalten den Korpus. MVP: ein Pilot-Bereich, < 30 Nutzer, Single Instance, Business Hours, Deadline 30. September 2026.

---

## Top-3 Quality Attributes

| Rang | QA | Kernforderung |
|---|---|---|
| 1 | **Reliability** | Halluzinationsrate = 0 %; Out-of-Corpus-Erkennung ≥ 90 % „Weiss ich nicht"; Circuit Breaker für LLM; mehrschichtiger Unterdrückungsmechanismus |
| 2 | **Security** | DSGVO — Daten verlassen EU nicht; JWT + bcrypt; RBAC (User / Admin); Pseudonymisierung; SSO nachrüstbar |
| 3 | **Maintainability** | Schwellenwerte in DB ohne Code-Deployment änderbar; LLM-Provider-Wechsel per Konfiguration (LiteLLM); modulare RAG-Komponenten |

---

## C1: Externe Akteure und Systeme

| Akteur / System | Rolle |
|---|---|
| **Lara** (Lernende) | Fragen stellen, Antworten lesen, Feedback geben, Quiz absolvieren |
| **Stefan** (Bereichsverantwortlicher) | Dokumente hochladen, Korpus verwalten, Quiz-Fragen freigeben, Stale-Inhalte validieren |
| **Admin** | Konfidenz- und Stale-Schwellenwerte konfigurieren |
| **OpenAI API** | LLM-Generierung (gpt-4o-mini) + Embeddings (text-embedding-3-small) via LiteLLM; Fallback: Ollama (lokal) |
| **Unternehmens-IdP** | SSO-Authentifizierung + Rollen-Sync via Azure AD / SAML 2.0 — Post-MVP |

---

## C2: Container-Entscheidungen (finalisiert)

| Container | Technologie | Begründung | Grösstes Risiko |
|---|---|---|---|
| **Web App** | React 18 / TypeScript 5 · Nginx | SSE-native SPA für Token-by-Token Q&A, Quiz und Quellenhervorhebung | Quellenhervorhebung in PDFs (PDF.js) unterschätzt → MVP-Blocker |
| **API Server** | Python 3.12 / FastAPI (ASGI) | Async SSE-Streaming, Python-KI-Ökosystem, RBAC als Dependency Injection | Konfidenz-Scoring konzeptionell noch undefiniert — Framework hilft nicht |
| **Background Worker** | pgqueuer (PostgreSQL-nativer Job-Queue) | Asynchrones Dokument-Processing ohne Redis; Jobs transaktional, kein Datenverlust bei Crash | Kleine Community; Single-Threaded: parallele Uploads stauen Queue |
| **Datenbank** | PostgreSQL 16 + pgvector | Relationale Daten + Vektoren + Original-Dokumente in einem Service; HNSW-Index für Similarity Search | bytea für Dokumente = technische Schuld; Single Point of Failure ohne Replica |

**Kommunikation:**
- Web App → API Server: REST + SSE (HTTPS) — synchron/streaming
- API Server → Datenbank: SQL via asyncpg (TCP 5432) — synchron
- API Server → Background Worker: pg_notify (TCP 5432) — asynchron
- Background Worker → Datenbank: SQL (TCP 5432) — synchron
- API Server → OpenAI API: HTTPS via LiteLLM — synchron mit Circuit Breaker

---

## ADR-001 Zusammenfassung

**Modularer Monolith** — alle Module (RAG-Pipeline, Auth, Dokumentverwaltung, Feedback, Admin) in einem Deployment-Artefakt. Modul-Grenzen durch explizite Service-Interfaces, kein shared State, stateless Design. Microservices verworfen wegen +80–120 h reinem Infrastruktur-Overhead bei < 30 Nutzern. Status: Proposed (2026-05-27).

---

## ADR-002 Pattern-Entscheidung Zusammenfassung

**Modularer Monolith** — API Server intern modular strukturiert (`rag/`, `documents/`, `quiz/`, `auth/`, `admin/`). Background Worker als bewusste Ausnahme: separater Prozess weil asynchrones Processing den 5-Minuten-SLA erfordert. Microservices verworfen: bei undefinierten Kern-Algorithmen (Konfidenz-Scoring, Chunking) ist verteilter Service-Overhead ein Budget-Killer. Status: Entschieden (2026-05-31).

---

## Was ist noch unklar oder widersprüchlich?

| Offenheit | Beschreibung | Kritikalität |
|---|---|---|
| **Konfidenz-Scoring undefiniert** | Zwei Unterdrückungsmechanismen (Konfidenz-Score vs. Self-Check-Anteil) — wie genau wird der Self-Check implementiert? LLM-Selbstevaluation oder semantische Ähnlichkeit? | 🔴 Blocker für US-02 |
| **Chunking-Strategie offen** | Im C2 explizit als «offen» markiert. Fixed-Size, Sentence-Based oder Semantic Chunking — die Wahl beeinflusst direkt Retrieval-Qualität und damit Reliability | 🔴 Blocker für Tech Spike |
| **Quellenhervorhebung im Browser** | US-01 verlangt «Klick auf Quelle hebt Abschnitt hervor» — PDF-Rendering + Highlighting im Browser ist nicht spezifiziert (PDF.js? iFrame? Backend-seitig?) | 🟠 Risiko für MVP-Scope |
| **bytea vs. Object Storage** | Original-Dokumente in PostgreSQL als bytea — funktioniert für MVP, aber kein Architekturentscheid dokumentiert wann der Wechsel zu S3/MinIO nötig wird | 🟡 Technische Schuld |
| **ADR-001 Status «Proposed»** | ADR-001 wurde noch nicht auf «Accepted» gesetzt — unklar ob die Entscheidung als final gilt oder noch offen ist | 🟡 Prozess |

---

## Offene Fragen für Tag 2

1. **Konfidenz-Scoring-Mechanismus festlegen** — welcher der drei Unterdrückungsmechanismen (Quellenprüfung, Konfidenz-Score, Self-Check) hat Vorrang, und wie wird Self-Check konkret implementiert? Das ist die Implementierung des Kernfeatures, keine Detail-Entscheidung.

2. **Chunking-Strategie entscheiden** — Fixed-Size vs. Semantic Chunking: der Tech Spike muss diese Frage beantworten bevor Sprint 1 startet. Ohne definierte Strategie ist die RAG-Qualität nicht evaluierbar.

3. **Quellenhervorhebung im MVP scope-en** — ist PDF.js im Browser realistisch für 3 Devs in 3 Monaten, oder wird US-01 auf «Link öffnet Dokument ohne Highlighting» reduziert für MVP? Diese Entscheidung beeinflusst den Frontend-Aufwand um 2–3 Wochen.

---

*Quellen: [Docs/05_C4-C1_System-Context.md](../../Docs/05_C4-C1_System-Context.md) · [Docs/05_C4-C2_Container.md](../../Docs/05_C4-C2_Container.md) · [Docs/03_QualityAttributes.md](../../Docs/03_QualityAttributes.md) · [Artefakten/Modul3Tag1/ADR-001_Architekturstil.md](../../Artefakten/Modul3Tag1/ADR-001_Architekturstil.md) · [Modul3Tag1_Lab_L2_Teil2_Output.md](Modul3Tag1_Lab_L2_Teil2_Output.md)*
