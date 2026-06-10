Hier sind alle unsere Must-have User Stories (aus Docs/01_UserStories.md):

- US-01: Quellenbelegte Frage-Antwort (Lara stellt Fragen, erhält Antworten mit klickbaren Quellenverweisen, p95 ≤ 10s)
- US-02: Unsichere Antworten klar erkennen (Konfidenz-Score, mehrstufige Unterdrückungspipeline, «Weiss ich nicht»)
- US-03: Feedback zu Antworten geben (👍/👎 mit Kategorie + Freitext, pseudonymisiert)
- US-04: Inhalte in den Lernkorpus aufnehmen (Upload PDF/DOCX/MD, Background-Processing ≤ 5 Min für ≤ 50 Seiten)
- US-05: Authentifizierung und Bereichszuordnung (Username/Passwort, Accounts per DB-Script, Rollen User/Admin)

Tech-Stack (aus Docs/05_C4-C2_Container.md):

- Web App: React 18 / TypeScript 5, Nginx
- API Server: Python 3.13 / FastAPI (ASGI), LiteLLM, JWT/RBAC
- Background Worker: pgqueuer (Parsing → Chunking → Embedding → pgvector-Indexierung)
- Datenbank: PostgreSQL 17 + pgvector (HNSW + tsvector/GIN + bytea)
- Extern: OpenAI Direct (MVP), Azure OpenAI EU (Produktion)

Unsere Definition of Done: [AUS ÜBUNG 3 EINFÜGEN]

Erstelle ein vollständiges Backlog:

- Zerlege jede Story in Tasks (max 4h)
- Story Points pro Task (1,2,3,5,8)
- Bereich-Label (Backend/Frontend/DB/DevOps)
- Abhängigkeiten zwischen Tasks
- Sortiere nach: was muss zuerst gebaut werden?

Gib mir am Ende: Gesamt-Story-Points und grobe Reihenfolge.
