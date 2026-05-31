# LearnFlow — C4 Container Diagram (Level 2)
*Modul 3 Tag 1 · Mai 2026*

---

## Diagramm (Mermaid)

```mermaid
C4Container
    title Container Diagram — LearnFlow

    Person(lara, "Lara", "Lernende / Junior Developer")
    Person(stefan, "Stefan", "Bereichsverantwortlicher / Knowledge Owner")
    Person(admin, "Admin", "Systemadministrator")

    System_Ext(openai, "Azure OpenAI EU", "LLM-Generierung (gpt-4o-mini) + Embeddings (text-embedding-3-small) via LiteLLM, EU-Datenresidenz. Dev: OpenAI Direct (keine Produktivdaten). OnPrem-Fallback: Ollama.")
    System_Ext(idp, "Unternehmens-IdP", "Azure AD / SAML 2.0. SSO-Auth + Rollen-Sync. (Post-MVP)")

    System_Boundary(learnflow, "LearnFlow") {
        Container(webapp, "Web App", "React 18 / TypeScript 5 · Nginx", "SPA: Q&A-Interface, Dokument-Upload, Quiz, Feedback, Admin-Seite. Konsumiert SSE-Stream für Token-by-Token-Anzeige.")
        Container(api, "API Server", "Python 3.13 / FastAPI (ASGI)", "REST-Endpunkte + SSE-Streaming. Auth-Middleware (JWT/RBAC). RAG-Pipeline-Orchestrierung (Hybrid-Retrieval, ADR-007). LiteLLM-Integration für LLM und Embeddings. Mehrstufige Konfidenz-Unterdrückungspipeline (ADR-008).")
        Container(worker, "Background Worker", "pgqueuer (PostgreSQL-nativer Job-Queue)", "Asynchrones Dokument-Processing: Parsing (PDF/DOCX/MD), Chunking, Embedding-Generierung via LiteLLM, pgvector-Indexierung. Erfüllt 5-Minuten-SLA für Dokumente ≤ 50 Seiten.")
        ContainerDb(db, "Datenbank", "PostgreSQL 17 + pgvector", "Relationale Tabellen: users, documents, feedback, config, quiz_questions. Vektor-Tabelle: embeddings (HNSW-Index) + Volltext-Index (tsvector/GIN, deutsch) für Hybrid-Retrieval. Original-Dokumente als bytea. config-Tabelle: alle Schwellenwerte ohne Neustart änderbar.")
    }

    Rel(lara, webapp, "Fragen stellen, Antworten + Quellen lesen, Feedback geben, Quiz absolvieren", "HTTPS")
    Rel(stefan, webapp, "Dokumente hochladen, Quiz-Fragen freigeben, Stale-Inhalte validieren", "HTTPS")
    Rel(admin, webapp, "Konfidenz- und Stale-Schwellenwerte konfigurieren", "HTTPS")

    Rel(webapp, api, "REST-Calls + SSE-Stream (Q&A-Antworten token-by-token)", "HTTPS")
    Rel(api, db, "Lesen/Schreiben: Users, Dokumente, Config, Feedback, Quiz, Embeddings (Similarity Search)", "SQL · TCP 5432")
    Rel(api, worker, "Dokument-Job enqueuen nach Upload", "pg_notify · TCP 5432")
    Rel(worker, db, "Chunks + Embeddings schreiben, HNSW-Index aufbauen", "SQL · TCP 5432")
    Rel(api, openai, "LLM-Prompts (Antwort-Generierung, Self-Check, Quiz-Generierung) + Embedding-Anfragen", "HTTPS/REST via LiteLLM (EU)")
    Rel(api, idp, "SSO-Auth + Rollen-Sync (Post-MVP)", "SAML 2.0")

    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

---

## Container-Übersicht

### 1. Container — Fragen und Begründungen

#### 1.1 Welche Container brauchen wir?

| Container | Technologie | Begründung (1 Satz) |
|---|---|---|
| **Web App** | React 18 / TypeScript 5, Vite, Nginx | Interaktive SPA mit SSE-Unterstützung für Token-by-Token-Streaming — HTMX wäre umständlicher für Quiz, Feedback-UI und Quellenhervorhebung. |
| **API Server** | Python 3.13 / FastAPI (ASGI) | Async-native SSE-Streaming, RBAC-Middleware und das gesamte Python-KI-Ökosystem (LiteLLM, LangChain, pypdf, python-docx) sind direkt verfügbar — kein Adapter-Layer. |
| **Background Worker** | pgqueuer (PostgreSQL-nativer Job-Queue) | Dokument-Processing (Parsing → Chunking → Embedding → Indexierung) muss asynchron laufen, damit der Upload sofort bestätigt wird und der 5-Minuten-SLA eingehalten wird. |
| **Datenbank** | PostgreSQL 17 + pgvector | Ein einziger Server für relationale Daten, Vektor-Embeddings (pgvector HNSW), Volltext-Index (tsvector/GIN) für Hybrid-Retrieval und Original-Dokumente (bytea) — ein Backup, eine Verbindungskonfiguration, kein zweiter Service. |

#### 1.2 Welche Technologien passen zu unseren QAs?

| QA | Container | Technologie-Entscheid |
|---|---|---|
| **Reliability** | API Server | Mehrschichtiger Unterdrückungsmechanismus (Quellenprüfung → Konfidenz → Self-Check) als Pipeline im API Server; Circuit Breaker für LiteLLM-Aufrufe. |
| **Reliability** | Datenbank | Konfidenz- und Stale-Schwellenwerte in `config`-Tabelle — empirisch kalibrierbar ohne Deployment. |
| **Security** | API Server | JWT (8 h) + bcrypt-Hashing; RBAC-Middleware; pseudonymisiertes Feedback-Schreiben; serverseitige URL-Abweisung ohne Admin-Rolle. |
| **Maintainability** | API Server | LiteLLM-Abstraktion: Provider-Wechsel (Azure OpenAI EU ↔ OpenAI Direct ↔ Ollama) ist ein Konfigurationseintrag in der `config`-Tabelle — kein Code-Change. |
| **Performance** | API Server + Web App | FastAPI `StreamingResponse` (SSE) + React `EventSource` — Token-by-Token-Anzeige; wahrgenommene Wartezeit sinkt deutlich unter 10 s p95. |
| **Performance** | Datenbank | pgvector HNSW-Index liefert Sub-100-ms-Latenz bei Similarity Search für < 10 000 Chunks. |
| **Performance** | Background Worker | Dokument-Processing asynchron — Upload wird sofort bestätigt, Verarbeitung läuft im Hintergrund. |
| **Testability** | Background Worker + API Server | Modulare RAG-Komponenten (Chunking, Embedding, Retrieval, Generierung) — jede einzeln isolierbar und testbar; Evaluationsdataset läuft im CI gegen jede Komponente. |

#### 1.3 Wie kommunizieren die Container miteinander?

| Von | Nach | Inhalt | Protokoll |
|---|---|---|---|
| Browser (Lara/Stefan/Admin) | Web App | HTML/JS/CSS ausliefern | HTTPS |
| Web App | API Server | REST-Calls (Login, Upload, Feedback, Quiz) + SSE-Stream (Q&A-Antworten token-by-token) | HTTPS |
| API Server | Datenbank | Lesen/Schreiben: Users, Dokumente, Config, Feedback, Quiz-Fragen; Similarity Search (Embeddings) | SQL · TCP 5432 |
| API Server | Background Worker | Dokument-Job nach Upload enqueuen (Dokument-ID, Bereich) | pg_notify · TCP 5432 |
| Background Worker | Datenbank | Chunks + Embeddings schreiben; HNSW-Index aufbauen | SQL · TCP 5432 |
| API Server | Azure OpenAI EU | LLM-Prompts (Antwort, Self-Check, Quiz-Generierung) + Embedding-Anfragen | HTTPS/REST via LiteLLM (EU) |
| API Server | Unternehmens-IdP | SSO-Authentifizierung + Rollen-Sync *(Post-MVP)* | SAML 2.0 |

---

## 2. RAG-Request-Flow (Happy Path)

```
Lara tippt Frage
       │
       ▼
  [Web App]
  Eingabe validieren (3–1000 Zeichen)
       │ POST /api/query  (HTTPS)
       ▼
  [API Server]
  1. Auth prüfen (JWT)
  2. Query-Embedding generieren  ──► [Azure OpenAI EU] text-embedding-3-small
  3. Hybrid-Retrieval (ADR-007)   ──► [Datenbank] pgvector HNSW + tsvector/GIN, RRF-Fusion
  4. Retrieval-Gate (ADR-007): Chunk über Similarity-Schwelle?
     └── nein → "Weiss ich nicht" (kein LLM-Aufruf)
  5. Retrieval-Konfidenz prüfen (ADR-008, Stufe 1)
     └── zu tief → "Weiss ich nicht"
  6. LLM-Prompt aufbauen + senden ──► [Azure OpenAI EU] gpt-4o-mini
  7. Grounding-/Citation-Check (ADR-008, Stufe 2)
     └── Coverage < 50 % → unterdrückt
  8. Self-Check für Grenzfälle (ADR-008, Stufe 3, optional)
  9. SSE-Stream öffnen
       │ text/event-stream
       ▼
  [Web App]
  Token-by-Token anzeigen + Quellenreferenzen einblenden
```

---

## 3. Dokument-Upload-Flow (Hintergrund-Processing)

```
Stefan lädt PDF hoch
       │
       ▼
  [Web App]
  POST /api/documents  (multipart/form-data)
       │
       ▼
  [API Server]
  1. Auth + Rolle prüfen (Bereichsverantwortlicher)
  2. Datei in DB speichern (bytea), Zeitstempel setzen
  3. Job in Queue schreiben (Dokument-ID)
  4. Sofortige Bestätigung an Stefan → "Upload erfolgreich, Verarbeitung läuft"
       │
       ▼
  [Background Worker]
  1. Dokument aus DB laden
  2. Text extrahieren (pypdf / python-docx)
  3. Text chunken (struktur-bewusst, ~512 Token / 64 Overlap — ADR-007)
  4. Chunks embedden  ──► [Azure OpenAI EU] text-embedding-3-small
  5. Embeddings + Chunks + tsvector in DB schreiben, HNSW-Index aktualisieren
  6. Dokument-Status: "verfügbar"
  → Innerhalb 5 Minuten für Dokumente ≤ 50 Seiten / 10 MB
```

---

## 4. Entscheid — Background Worker

**pgqueuer** — entschieden 2026-05-27 (ADR-006).

Jobs werden in einer PostgreSQL-Tabelle persistiert. Der Worker nutzt `pg_notify` für sofortige Benachrichtigung — kein Redis, kein separater Broker. Details und Begründung: `04_ADR-006_Background-Worker.md`.

---

## 5. Deployment-Übersicht (Docker Compose — MVP)

```
docker-compose.yml
├── webapp        (Nginx + React Build)        Port 80/443
├── api           (FastAPI / Uvicorn)           Port 8000 (intern)
├── worker        (pgqueuer)                    kein externer Port
└── db            (PostgreSQL 17 + pgvector)    Port 5432 (intern)
```

Single Instance — kein HA-Setup. Bewusst akzeptiert für Business-Hours-Pilot mit < 30 Nutzern.

---

*Quellen: 03_QualityAttributes.md · 05_C4-C1_System-Context.md · 04_ADR-001 bis 04_ADR-009*
*Stand: v3 — 2026-05-31 · Stack-Versionen (Py 3.13, PG 17) + Azure OpenAI EU + ADR-007/008/009 (Retrieval, Konfidenz, Eval) eingearbeitet*
