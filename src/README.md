# LearnFlow — src

RAG-basierte Lernplattform. FastAPI + PostgreSQL/pgvector + React, orchestriert mit Docker Compose.

## Prerequisites

- Docker Desktop (running)
- Git

## Quickstart

```bash
cp .env.example .env
# .env editieren — DB_PASSWORD, JWT_SECRET, OPENAI_API_KEY eintragen
docker compose up -d --build
```

Nach dem Start aller Services:

```bash
docker exec src-api-1 python seed_users.py
```

Browser: **http://localhost**

## Logins (nach seed)

| Email                        | Passwort    | Rolle            |
|------------------------------|-------------|------------------|
| niklaus@learnflow.local      | changeme2   | admin            |
| frank@learnflow.local        | changeme1   | knowledge_owner  |
| reto@learnflow.local         | changeme3   | knowledge_owner  |
| christoph@learnflow.local    | changeme4   | knowledge_owner  |
| stefan@learnflow.local       | changeme5   | knowledge_owner  |
| lara@learnflow.local         | changeme6   | learner          |

## Zugang

| Service | URL / Adresse         |
|---------|-----------------------|
| App     | http://localhost      |
| API     | http://localhost:8000 |
| DB      | localhost:5432        |

DB: user `learnflow`, Passwort aus `DB_PASSWORD`, Database `learnflow`.

## Nützliche Befehle

```bash
make up         # build + starten
make down       # stoppen
make seed       # Testuser anlegen
make logs       # Logs aller Services
make check      # Health-Checks prüfen
make qa         # Lint + Types + Tests (Backend + Frontend)
```

```bash
# Einzelne Services
docker compose logs -f api
docker compose restart api

# Migrations
docker exec src-api-1 alembic upgrade head

# psql
docker exec -it src-db-1 psql -U learnflow -d learnflow
```

## VS Code Debugger (debugpy)

```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d api
```

Dann in VS Code: **Run & Debug → Attach to FastAPI**. Breakpoints in `backend/app/` funktionieren sofort.
