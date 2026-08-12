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

### API-Typen nach einer Spec-Änderung neu generieren

```bash
make generate-api   # aus src/ — braucht kein lokales Node
```

`src/frontend/src/api/schema.d.ts` wird aus `backend/openapi.yaml` erzeugt und gehört in
denselben Commit wie die Spec-Änderung. Wer es vergisst, bekommt einen roten `frontend`-Job
mit genau diesem Befehl in der Fehlermeldung. Der Client (`src/api/client.ts`) ist gegen
diese Typen geschrieben — ein geändertes Schema bricht den Build, nicht erst die Laufzeit.

### API-Dokumentation (Swagger UI / ReDoc)

Standardmässig **aus**. FastAPI liefert `/docs`, `/redoc` und `/openapi.json` ohne
Authentifizierung aus und legt damit die vollständige API-Oberfläche offen — für
eine Plattform mit internen Dokumenten eine bewusste Entscheidung, kein Default.

Für die lokale Entwicklung in `.env` einschalten:

```
EXPOSE_API_DOCS=true
```

Danach `make up` (oder `docker compose restart api`); die drei URLs sind dann unter
`http://localhost/api/docs` usw. erreichbar. Verbindlich ist trotzdem
`backend/openapi.yaml` — das ausgelieferte Schema ist aus dem Code abgeleitet und
nur eine Entwicklungshilfe (ADR-010).

## Nützliche Befehle

```bash
make up         # build + starten
make down       # stoppen
make seed       # Testuser anlegen
make logs       # Logs aller Services
make check      # Health-Checks prüfen
make qa         # Lint + Types + Tests (Backend + Frontend) — CI-Jobs backend/frontend
make e2e        # Login-Flow gegen den laufenden Stack (nach up + seed) — CI-Job e2e
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
