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

Die Werte in `.env.example` sind bewusst so gewählt, dass der Stack damit **nicht**
startet: `app/config.py` weist jedes `JWT_SECRET` ab, das kürzer als 32 Zeichen ist
oder `changeme` enthält. Ein brauchbares Secret erzeugen:

```bash
openssl rand -hex 32
```

Ist Port 80 belegt, in `.env` `WEBAPP_PORT` setzen (z. B. `WEBAPP_PORT=8080`) — es ist
der einzige Port, den der Stack nach aussen veröffentlicht.

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

| Service | Zugang                                            |
|---------|---------------------------------------------------|
| App     | http://localhost (bzw. `WEBAPP_PORT`)             |
| API     | http://localhost/api/ — via nginx                 |
| DB      | nur containerintern, kein veröffentlichter Port   |

`webapp` ist der einzige Container mit einem `ports:`-Eintrag. `api` und `db` hängen an
internen Netzen (`docker-compose.yml`); nginx proxyt `/api/*` auf `api:8000` und entfernt
dabei das Prefix. Ein direkter Zugriff auf `localhost:8000` oder `localhost:5432`
funktioniert deshalb nicht — die DB erreicht man über `docker exec` (siehe unten).

Für das Frontend-Dev-Setup (`npm run dev` in `frontend/`) gilt derselbe Weg: der
Vite-Proxy leitet `/api` an nginx weiter, der Stack muss also laufen.

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
make qa-be      # nur Backend: ruff + mypy + pytest — läuft im api-Container, braucht `make up`
make qa-fe      # nur Frontend: eslint + tsc + vitest — ephemerer node:22-alpine, ohne laufenden Stack
make e2e        # E2E-Tests gegen den laufenden Stack (nach up + seed) — CI-Job e2e
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

## Zurücksetzen & Stolpersteine

```bash
# Datenbank komplett neu aufsetzen
docker compose down
docker volume rm learnflow_pgdata
make up && make seed
```

Das Volume heisst bewusst global `learnflow_pgdata` statt projekt-scoped — ein
`docker compose down -v` löscht es damit **nicht**, ein Verzeichnis-Rename behält die
Daten. Wegräumen geht nur über `docker volume rm`.

Nach einem Versionssprung von `openapi-typescript` generiert `make generate-api` weiter
mit der alten Version aus dem gecachten Volume; die committeten Typen fallen dann in der
CI durch. Einmalig:

```bash
docker volume rm learnflow-fe-node-modules
```

## VS Code Debugger (debugpy)

```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d api
```

Die passende Konfiguration liegt nicht im Repo (`.vscode/` ist nicht eingecheckt) — einmalig
selbst in `.vscode/launch.json` anlegen, mit dem Repo-Root als geöffnetem Ordner:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to FastAPI",
      "type": "debugpy",
      "request": "attach",
      "connect": { "host": "localhost", "port": 5678 },
      "pathMappings": [
        { "localRoot": "${workspaceFolder}/src/backend", "remoteRoot": "/app" }
      ]
    }
  ]
}
```

Dann in VS Code: **Run & Debug → Attach to FastAPI**. Breakpoints in `backend/app/` funktionieren sofort.

## Weiterführend

- **Entscheide (ADRs, C4, Anforderungen, DoD):** `Docs/` — Übersicht in `../CLAUDE.md`
- **CI-Pipeline und ihre drei Jobs:** `Ops/09_CI-Runbook.md`
- **Vor dem Pilotstart:** `Ops/07_Pilotstart-Checkliste.md`
- **API-Vertrag:** `backend/openapi.yaml` (ADR-010)
