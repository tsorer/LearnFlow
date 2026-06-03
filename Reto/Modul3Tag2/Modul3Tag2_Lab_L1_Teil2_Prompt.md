Hier ist unser Architecture Draft: Docs/06_Architecture-Draft.md

Analysiere unsere Architektur auf zwei Dimensionen:

Dimension 1 — Skalierung:
- Was bricht als erstes bei 10x mehr Usern (von < 30 auf ~300)?
- Wo ist unser Bottleneck (Hinweis: PostgreSQL als Single Instance, pgvector HNSW-Index, SSE-Streaming, Background Worker pgqueuer)?
- Was müssten wir ändern für 100x?

Dimension 2 — Security:
- Wo sind die grössten Angriffsflächen (Hinweis: RAG-Pipeline, Dokument-Upload, SSE-Stream, JWT-Auth)?
- Welche OWASP Top-10 Risiken betreffen uns konkret?
- Was fehlt in unserer Architektur für DSGVO-Compliance (Daten in EU via Azure OpenAI EU, Query-Logs, Feedback-Pseudonymisierung)?
