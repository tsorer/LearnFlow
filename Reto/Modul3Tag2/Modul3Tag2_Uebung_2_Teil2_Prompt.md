Schreibe eine OpenAPI 3.0 Spec für diesen Endpoint:

Endpoint: POST /api/v1/questions — Nutzer stellt eine Frage; Backend führt RAG-Pipeline aus und streamt die Antwort mit Quellenbelegen via Server-Sent Events zurück.

Projekt: LearnFlow — interne RAG-Lernplattform; neue Mitarbeitende stellen Fragen in natürlicher Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus.

Stack: Python 3.13 / FastAPI · SSE via StreamingResponse · PostgreSQL + pgvector · Azure OpenAI EU via LiteLLM.

Inkludiere:
- Path, Method, Summary, Description
- Request Body mit Beispiel (JSON Schema)
- Response 200 mit Beispiel (SSE-Stream mit Antwort + Quellen)
- Response 400, 401, 404, 422 mit Fehlerbeschreibungen
- Security: Bearer Token (JWT)

Format: YAML
