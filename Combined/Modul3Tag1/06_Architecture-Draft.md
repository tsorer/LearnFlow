# LearnFlow — Architecture Draft

*Stand: 2026-05-31 · synthetisiert aus ADR-001 bis ADR-009 · BFH CAS ADAI 2026*
*Status: Draft (Sprint 0 / Tech-Spike) · Verfasser: LearnFlow-Team (Frank, Niklaus, Reto)*

> Dieses Dokument konsolidiert die neun Architecture Decision Records zu einem zusammenhängenden Architekturbild. Es ersetzt die ADRs nicht — sie bleiben die maßgebliche Quelle für Begründungen und Alternativen. Bei Abweichungen gilt der jeweilige ADR. Der Anhang sammelt offene und widersprüchliche Punkte.

---

## 1. Kontext & Ziele

**LearnFlow** ist eine interne RAG-Lernplattform, die neuen Entwickler:innen, Requirements-Engineers und Tester:innen fachliches Domänen- und Systemwissen über quellenbelegte KI-Antworten und überprüfte Quizfragen zugänglich macht — auf Basis eines kuratierten, vom Fachbereich freigegebenen Lern-Korpus.

### Randbedingungen

| Dimension | Wert |
|---|---|
| Budget | 4 Personen × 80 h = **360 h** |
| Zeitrahmen | 3 Monate MVP |
| Nutzer | < 30 (ein Pilot-Bereich), Business-Hours |
| Korpus | deutschsprachige Fachtexte, < 500 Dokumente / < 10 000 Chunks |
| Betrieb | intern, DSGVO/Compliance des Unternehmens |
| Implementierung | überwiegend KI-gestützt mit **Claude Code** (Team = Reviewer/Verifizierer) |

### Leitende Qualitätsattribute (NFA)

- **Reliability (Kern):** Halluzinationsrate = 0 %, Out-of-Corpus ≥ 90 % „Weiss ich nicht".
- **Performance:** wahrgenommene Wartezeit ≤ 10 s @ p95 (Token-Streaming).
- **Maintainability:** Provider-/Schwellenwechsel ohne Code-Deployment.
- **Security:** rollenbasierter Zugriff, EU-Datenresidenz.
- **Testability:** RAG-Komponenten isoliert evaluierbar, CI-Gate.

---

## 2. Architekturüberblick (ADR-001)

**Modularer Monolith** — alle Module (RAG-Pipeline, Auth, Dokument-Management, Feedback, Admin) in einem Deployment-Artefakt. Modul-Grenzen werden durch explizite Service-Interfaces durchgesetzt (kein DB-Zugriff über Modulgrenzen, kein shared State). Stateless-Design für späteren Ausbau.

*Begründung:* Microservices-Overhead (Service Discovery, Mesh, separate Pipelines: geschätzt +80–120 h) ist bei < 30 Nutzern und 360 h Budget nicht zu rechtfertigen.

---

## 3. Technologie-Stack (ADR-002, -003, -004, -005, -006)

| Schicht | Technologie | ADR |
|---|---|---|
| Frontend | **React 18 + TypeScript 5**, Vite, Nginx | ADR-002 |
| Backend | **Python 3.13 + FastAPI** (ASGI) | ADR-002 |
| Datenbank | **PostgreSQL 17 + pgvector** (HNSW) + Volltext (`tsvector`/GIN, deutsch) | ADR-003 |
| LLM-Integration | **LiteLLM** als Abstraktion | ADR-004 |
| LLM-Provider (Prod) | **Azure OpenAI EU** — `gpt-4o-mini` (Default), `gpt-4o` (Upgrade) | ADR-004 |
| Embedding (Prod) | **`text-embedding-3-small`** (1536 Dim) via Azure OpenAI EU | ADR-005 |
| Embedding (OnPrem/Dev) | **`bge-m3`** (1024 Dim) via Ollama | ADR-005 |
| Background-Worker | **pgqueuer** (PostgreSQL-nativ, `LISTEN`/`NOTIFY`) | ADR-006 |
| Deployment | **Docker Compose** — 4 Container (`webapp`, `api`, `worker`, `db`) | ADR-002/006 |

**Versionsphilosophie:** bewusst stabil-abgehangen statt bleeding-edge. Python 3.13 (nicht 3.14) wegen ML-Wheel-Reife; React 18 und stabile APIs wegen höchster Trainingsdaten-Dichte → zuverlässigere KI-Generierung. PostgreSQL 17 aus Lebenszyklus-/Docker-Image-Gründen (pgvector ist versionsunabhängig).

**Frontend-Begründung (KI-bewusst):** React wegen höchster Trainingsdaten-Dichte (zuverlässige Claude-Code-Generierung), TypeScript als Compile-Zeit-Review-Netz, größtes Komponenten-Ökosystem. Vue/Svelte/HTMX wurden abgewogen (ADR-002).

---

## 4. Komponenten (C4-C2)

```
docker-compose.yml
├── webapp   React 18 / Nginx        — SPA: Q&A, Upload, Quiz, Feedback, Admin; SSE-Consumer
├── api      Python 3.13 / FastAPI   — REST + SSE; Auth (JWT/RBAC); RAG-Orchestrierung; Konfidenzpipeline
├── worker   pgqueuer                — async Dokument-Processing (Parsing→Chunking→Embedding→Index)
└── db       PostgreSQL 17 + pgvector — relational + Vektor (HNSW) + Volltext (GIN) + Dokumente (bytea)
```

Externe Systeme: **Azure OpenAI EU** (via LiteLLM, EU-Endpunkt; Dev: OpenAI Direct ohne Produktivdaten; OnPrem: Ollama), **Unternehmens-IdP** (Azure AD / SAML 2.0, *Post-MVP*).

---

## 5. Datenarchitektur (ADR-003)

- **Ein Persistenz-Service:** PostgreSQL 17 für relationale Daten (`users`, `documents`, `feedback`, `config`, `quiz_questions`), Vektor-Embeddings (`embeddings` mit HNSW), Volltext-Index (`tsvector`/GIN) und Original-Dokumente (`bytea`).
- **Migrationen:** Alembic, versioniert in Git.
- **Konfiguration:** `config`-Tabelle hält alle Schwellenwerte → ohne Deployment kalibrierbar (Maintainability-NFA).
- **Constraint:** pgvector indexiert HNSW nur bis **2000 Dimensionen** (1536/1024 unkritisch; `text-embedding-3-large`/3072 erfordert Matryoshka-Reduktion oder `halfvec`).

---

## 6. RAG-Pipeline — Kern der Reliability (ADR-007, -008)

### 6.1 Indexierung (Background-Worker)
Parsing (pypdf/python-docx) → **struktur-bewusstes Chunking** (Überschrift > Absatz > Satz; Startwerte ~512 Token / 64 Overlap) → Embedding via LiteLLM → Schreiben von Chunks + Embeddings + `tsvector` → HNSW-Index. Chunk-Metadaten (Dokument-ID, Bereich, Quell-Position) für Quellenanzeige.

### 6.2 Retrieval (ADR-007)
**Hybrid-Retrieval:** Dense (pgvector Cosine/HNSW) + Sparse (Postgres-Volltext `german`) → **Reciprocal Rank Fusion (RRF)**. Kandidaten `k=20` je Suche → Fusion → Gate → Top-`n=5` als Kontext.

### 6.3 Reliability-Pipeline (ADR-008, fail-closed)

| Stufe | Mechanismus | Wirkung |
|---|---|---|
| 0 | **Retrieval-Gate** (ADR-007): kein Chunk über Similarity-Schwelle | → „Weiss ich nicht", kein LLM-Aufruf |
| 1 | **Retrieval-Konfidenz** (deterministisch) | unter Schwelle → „Weiss ich nicht" |
| 2 | **Grounding-/Citation-Check** (deterministisch, Coverage ≥ 50 %) | ungedeckt → unterdrückt |
| 3 | **LLM-Self-Check** (nur Grenzfälle) | ungedeckte Aussagen → unterdrückt |

**Komposit-Konfidenz** (Stufe 1 + 2) → 3-Band-Anzeige (Hoch/Mittel/Niedrig) für US-02. Grounding-Prompt zwingt das LLM, nur aus Kontext zu antworten und zu zitieren. Alle Schwellen in `config`.

---

## 7. LLM- & Embedding-Integration (ADR-004, -005)

- **LiteLLM** normalisiert Provider → Wechsel Azure EU ↔ OpenAI Direct ↔ Ollama ist ein `config`-Eintrag, kein Code-Change.
- **EU-Datenresidenz als Default** (Azure OpenAI EU), da interne Dokumente verarbeitet werden — beim Indexieren geht der *gesamte* Korpus an den Provider (datenintensivste Exposition).
- **Modellwechsel** erzwingt vollständige Re-Indexierung (Dimensionsänderung = Schema-Migration).
- **Provider-Portabilität** ist auch in der Eval (LLM-as-Judge) und Konfidenz (keine Logprob-Abhängigkeit) durchgehalten.

---

## 8. Background-Processing (ADR-006)

**pgqueuer** statt Celery + Redis: Jobs als persistierte PostgreSQL-Zeilen, Benachrichtigung via `pg_notify`. Kein Redis, kein zusätzlicher Service → Monolith-Ziel (ADR-001) erfüllt, ein Backup deckt alles. Erfüllt den 5-Minuten-SLA (US-04) für Dokumente ≤ 50 Seiten. Alternativen (procrastinate, `SKIP LOCKED`, ARQ/Dramatiq/SAQ) abgewogen.

---

## 9. Querschnitt & Verifikation

- **Auth (ADR-002, C4):** JWT (8 h) + bcrypt, RBAC-Middleware; SSO (SAML 2.0 / Azure AD) als *Post-MVP* vorbereitet. *(Detail-Rollenmodell offen — siehe Anhang.)*
- **Konfiguration:** alle Schwellen-/Provider-Parameter in der `config`-Tabelle.
- **Eval & Reliability-Verifikation (ADR-009):** Gold-Dataset (In-/Out-of-Corpus/Adversarial) + RAGAS + Custom-Gates; **CI-Regressionsgate** (Build bricht bei Halluzination > 0 %); Produktions-Monitoring via Feedback (US-03). LLM-as-Judge über Azure OpenAI EU.
- **Deployment:** Docker Compose, Single-Instance (kein HA) — bewusst für Business-Hours-Pilot.

---

## 10. ADR-Index

| ADR | Entscheidung | Status |
|---|---|---|
| ADR-001 | Modularer Monolith | Proposed |
| ADR-002 | Python 3.13/FastAPI + React 18/TS | Proposed |
| ADR-003 | PostgreSQL 17 + pgvector | Proposed |
| ADR-004 | Azure OpenAI EU + LiteLLM | Proposed |
| ADR-005 | Embedding konfigurierbar (Azure EU / Ollama) | Proposed |
| ADR-006 | pgqueuer (Background-Worker) | Accepted |
| ADR-007 | Struktur-Chunking + Hybrid-Retrieval + Gate | Proposed |
| ADR-008 | Mehrstufige Konfidenzpipeline (fail-closed) | Proposed |
| ADR-009 | Eval-Strategie (Gold-Dataset + CI-Gate) | Proposed |

---

# Anhang A — Was ist noch unklar oder widersprüchlich?

### A.1 Unklar / unentschieden

1. **`bytea` vs. PostgreSQL Large Object (`lo`)** (ADR-003): Als Entscheidung deklariert, aber `lo`-Evaluierung als Mitigation offen gelassen. `bytea` lädt das ganze Binary in den RAM (100 MB PDF → 100 MB pro SELECT). Muss **vor Schema-Erstellung** geklärt werden.
2. **Datenmodell & OpenAPI-Kontrakt fehlen** vollständig — obwohl ADR-002 die „OpenAPI-Spec als saubere Grenze" als zentrale Begründung nutzt. Kein Tabellen-Schema, keine Endpunkt-Definitionen.
3. **Produktions-Embedding-Modell** (ADR-005): `text-embedding-3-small` ist gesetzt, aber als Spike-Eval markiert — für deutschen Fachkorpus evtl. nicht optimal. Noch nicht final.
4. **RAG-Parameter** (ADR-007/008): Chunk-Größe, Overlap, Similarity-Schwelle, Citation-Coverage, Top-`k`/`n`, RRF-`k` sind **Hypothesen**, erst nach Spike-Kalibrierung verlässlich.
5. **Auth-Detail** (ADR-002): Rollenmodell, Account-Provisionierung und Endpunkt-Autorisierungsmatrix sind nicht spezifiziert.
6. **Quiz-Generierung** (US-07/08): im Scope, aber durch kein ADR abgedeckt.
7. **Secret-Management & Observability/Logging:** in ADR-001/C1 als Folgeentscheide markiert, nicht entschieden.

### A.2 Widersprüche / Spannungen

8. **Streaming vs. Grounding-Check (ADR-008 ↔ Performance-NFA):** Fail-closed verlangt, die Antwort *vor* Auslieferung zu prüfen (Stufe 2). Token-by-Token-Streaming (ADR-002, Performance-NFA) liefert aber *während* der Generierung aus. Beides zugleich ist nicht trivial — entweder erst generieren+prüfen, dann „streamen" (höhere wahrgenommene Latenz) oder Korrektur-/Abbruch-Mechanik im Stream. **Architektonisch noch nicht aufgelöst.**
9. **„0 % Halluzination" vs. statistische Realität** (ADR-009): Auf endlichem Dataset nur demonstrierbar, nicht beweisbar. Die NFA-Formulierung sollte als „0 % auf Eval-Set + Produktions-Monitoring" präzisiert werden.
10. **Bestes Deutsch-Modell nur lokal** (ADR-005): `bge-m3` (stark multilingual) läuft lokal, das englisch-optimierte `text-embedding-3-small` in Produktion — Sprach-Fit „verkehrt herum".
11. **Dev/Prod-Inkompatibilität** (ADR-005): 1536 (Prod) vs. 1024 (Dev) → Retrieval-Probleme aus Produktion lokal nicht reproduzierbar (eingeschränkte Debuggability).

---

# Anhang B — Wichtigste offene Fragen

> Priorisiert nach Auswirkung auf den Tech-Spike (Woche 1) und das MVP.

### B.1 Blockierend vor dem ersten Code

1. **Wer erstellt wann das Gold-Eval-Dataset?** Ohne fachlich abgenommenes Dataset (Stefan) ist die Reliability-NFA weder kalibrierbar noch verifizierbar (ADR-009). → Terminzusage Fachbereich nötig.
2. **Wie sieht das Datenmodell + der API-Kontrakt aus?** Tabellen-Schema und OpenAPI-Spec sind Voraussetzung für parallele Arbeit und für die Schema-Migrationen.
3. **`bytea` oder `lo` für Dokumente?** Entscheidung vor Schema-Erstellung (RAM-/WAL-Verhalten).

### B.2 Im Spike zu beantworten (Woche 1)

4. **Welche RAG-Parameter erfüllen die NFA?** Chunking (256/512/1024, Overlap), Similarity-Schwelle, Coverage, Top-`k`/`n` empirisch kalibrieren.
5. **Welches Produktions-Embedding-Modell?** `-small` vs. `-large` vs. dediziert multilingual — auf echten Fachtexten messen (inkl. HNSW-2000-Dim-Constraint).
6. **Wie lösen wir Streaming + Grounding-Check?** (Widerspruch A.2/8) — generieren-dann-streamen vs. In-Stream-Korrektur.
7. **Welches maschinenlesbare Citation-Format?** Voraussetzung für die deterministischen Checks (ADR-008 Stufe 2).

### B.3 Vor dem MVP-Release

8. **Auth-Rollenmodell & Provisionierung** konkretisieren.
9. **Bulk-Upload-Rate-Limiting** gegen Azure-TPM-Limits (Batching/Backoff)?
10. **Quiz-Generierung & Freigabe-Workflow** (US-07/08) entscheiden.
11. **Secret-Management & Observability/Logging** festlegen.
12. **LLM-Framework:** LangChain vs. schlanke Eigenimplementierung — bislang vorausgesetzt, nie entschieden.
13. **Kosten-/Quota-Planung** für Azure OpenAI EU vor Go-Live.

---

*Quellen: 04_ADR-001 bis 04_ADR-009 · 05_C4-C1/C2 · 02_Requirements.md · 03_QualityAttributes.md · 04_ADR-Review_Kritik.md*
