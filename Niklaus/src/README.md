# LearnFlow — src

Greenfield RAG platform. FastAPI + PostgreSQL/pgvector + React, orchestrated with Docker Compose.

## Prerequisites

- Docker Desktop (running)
- Git

## Quickstart

```bash
cp .env.example .env
# edit .env — fill in DB_PASSWORD, JWT_SECRET, OPENAI_API_KEY
docker compose up -d --build
```

After all four services are healthy:

```bash
docker exec src-api-1 python seed_users.py
```

Open **http://localhost** in your browser.

## Logins (after seed)

| Email                        | Password    | Role             |
|------------------------------|-------------|------------------|
| niklaus@learnflow.local      | changeme2   | admin            |
| frank@learnflow.local        | changeme1   | knowledge_owner  |
| reto@learnflow.local         | changeme3   | knowledge_owner  |
| christoph@learnflow.local    | changeme4   | knowledge_owner  |
| stefan@learnflow.local       | changeme5   | knowledge_owner  |
| lara@learnflow.local         | changeme6   | learner          |

## Access

| Service | URL / address         |
|---------|-----------------------|
| App     | http://localhost      |
| API     | http://localhost:8000 |
| DB      | localhost:5432        |

DB credentials: user `learnflow`, password from `DB_PASSWORD` in `.env`, database `learnflow`.

## Useful commands

```bash
# Status + health
docker compose ps

# Tail logs
docker compose logs -f
docker compose logs -f api

# Restart a single service
docker compose restart api

# Stop everything (keeps data)
docker compose down

# Stop + wipe DB volume
docker compose down -v

# Re-run migrations
docker exec src-api-1 alembic upgrade head

# Open psql
docker exec -it src-db-1 psql -U learnflow -d learnflow
```

## Makefile shortcuts

```bash
make up      # build + start
make down    # stop
make seed    # seed users
make logs    # tail all logs
make check   # verify all services are healthy
```
