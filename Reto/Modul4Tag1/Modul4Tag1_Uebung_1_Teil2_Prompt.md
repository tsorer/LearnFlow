Du bist ein erfahrener Scrum Master.

User Story: US-01 — Quellenbelegte Frage-Antwort
Als Junior-Entwicklerin möchte ich eine Frage in natürlicher Sprache stellen und eine quellenbelegte Antwort erhalten, damit ich Fachprozesse verstehen kann, ohne erfahrene Kolleg:innen zu unterbrechen.

Acceptance Criteria (aus Docs/01_UserStories.md — US-01):
- Jede Antwort enthält mindestens einen klickbaren Quellenverweis (Dokumenttitel + Abschnitt + Validierungsdatum)
- Ein Klick auf eine Quellenangabe öffnet das Originaldokument und hebt den belegenden Abschnitt visuell hervor
- Antworten ohne identifizierbare Quelle werden nicht angezeigt
- Eingaben unter 3 Zeichen oder über 1.000 Zeichen werden clientseitig abgewiesen mit einem verständlichen Hinweis
- LLM- oder Retrieval-Service nicht erreichbar → klare Fehlermeldung, keine erfundene Antwort
- Antwortzeit: p95 ≤ 10 Sekunden

Tech-Stack (aus Docs/05_C4-C2_Container.md):
- Web App: React 18 / TypeScript 5, Nginx (Batch-Response JSON, keine SSE)
- API Server: Python 3.13 / FastAPI (ASGI), LiteLLM, Hybrid-Retrieval (pgvector HNSW + tsvector/GIN, RRF-Fusion), mehrstufige Konfidenz-Pipeline (ADR-008)
- Background Worker: pgqueuer (PostgreSQL-nativer Job-Queue)
- Datenbank: PostgreSQL 17 + pgvector (HNSW-Index + tsvector/GIN + bytea für Originaldokumente)
- Extern: OpenAI Direct (MVP) → Azure OpenAI EU (Produktion), via LiteLLM

Zerlege diese Story in konkrete Tasks:
- Jeder Task max. 4 Stunden
- Markiere: Backend / Frontend / DB / DevOps
- Nummeriere: TASK-001, TASK-002, ...
- Zeige Abhängigkeiten (welcher Task braucht welchen?)
