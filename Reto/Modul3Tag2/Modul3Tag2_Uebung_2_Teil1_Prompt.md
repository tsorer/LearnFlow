Hier ist unser Projekt:

LearnFlow — interne RAG-Lernplattform; neue Mitarbeitende (Lara) stellen Fragen in natürlicher Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus. Bereichsverantwortliche (Stefan) laden Dokumente hoch und verwalten den Korpus. MVP: 1 Pilot-Bereich, < 30 Nutzer, Single Instance, Business Hours, Deadline 30. September 2026.

Stack: Python 3.13 / FastAPI (ASGI) + React 18 / TypeScript + PostgreSQL 17 + pgvector + pgqueuer (Background Worker) + Azure OpenAI EU via LiteLLM.

Hier sind unsere Must-have User Stories: Docs/01_UserStories.md

Welche 5 API-Endpoints sind für unseren MVP am wichtigsten?

Für jeden Endpoint:
- HTTP Methode (GET/POST/PUT/DELETE)
- Path (/api/v1/...)
- Was macht er?
- Wer ruft ihn auf?
