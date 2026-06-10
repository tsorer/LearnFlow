# LearnFlow — Lokale Entwicklungsumgebung

Voraussetzungen: **Docker Desktop** (laufend), **Git**.

---

## 1. Erste Einrichtung

```bash
cd src

# .env anlegen (einmalig)
cp .env.example .env   # falls vorhanden, sonst manuell (siehe unten)
```

Minimale `.env`-Datei:

```env
DB_PASSWORD=localdev
OPENAI_API_KEY=sk-...
SECRET_KEY=changeme-local-only
```

> `DB_PASSWORD` kann frei gewählt werden — gilt nur lokal.  
> `OPENAI_API_KEY` wird für Embeddings und LLM-Calls benötigt (MVP: OpenAI Direct, keine echten internen Dokumente).

---

## 2. Stack starten

```bash
docker compose up --build
```

Beim ersten Start läuft automatisch `alembic upgrade head` im `api`-Container — alle Datenbankmigrationen werden eingespielt.

| Dienst   | Erreichbar unter           |
|----------|---------------------------|
| Web App  | http://localhost           |
| API      | http://localhost:8000      |
| API Docs | http://localhost:8000/docs |
| DB       | localhost:5432 (intern)    |

---

## 3. Datenbank einrichten

### Schema anlegen (automatisch beim Start)

Migrationen laufen beim Hochfahren des `api`-Containers automatisch. Manuell:

```bash
docker compose exec api alembic upgrade head
```

### Testbenutzer anlegen (Seed)

```bash
docker compose exec api python seed_users.py
```

Angelegte Testkonten:

| E-Mail                       | Passwort    | Rolle             |
|------------------------------|-------------|-------------------|
| lara@learnflow.local         | changeme6   | learner           |
| stefan@learnflow.local       | changeme5   | knowledge_owner   |
| frank@learnflow.local        | changeme1   | knowledge_owner   |
| niklaus@learnflow.local      | changeme2   | admin             |
| reto@learnflow.local         | changeme3   | knowledge_owner   |
| christoph@learnflow.local    | changeme4   | knowledge_owner   |

> Das Seed-Skript ist idempotent — mehrfaches Ausführen aktualisiert bestehende Einträge.

---

## 4. Direkt auf die Datenbank zugreifen

```bash
docker compose exec db psql -U learnflow -d learnflow
```

Nützliche psql-Befehle:

```sql
\dt                       -- alle Tabellen
\d embeddings             -- Spalten der Embeddings-Tabelle
SELECT COUNT(*) FROM documents;
```

---

## 5. Neue Migration erstellen

```bash
docker compose exec api alembic revision --autogenerate -m "kurze Beschreibung"
```

Die generierte Datei liegt unter `src/backend/alembic/versions/` und muss in Git eingecheckt werden, damit alle dasselbe Schema ziehen können.

---

## 6. Debug-Modus (Remote Debugger)

```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build
```

Dann in VS Code / PyCharm auf `localhost:5678` verbinden (debugpy).

---

## 7. Stack stoppen / zurücksetzen

```bash
# Stoppen (Daten bleiben erhalten)
docker compose down

# Stoppen + alle Daten löschen (Volume pgdata)
docker compose down -v
```

Nach `down -v` muss beim nächsten `up` das Seed-Skript erneut ausgeführt werden.

---

## 8. Häufige Fehler

| Symptom | Ursache | Lösung |
|---|---|---|
| `api` startet nicht — DB-Verbindungsfehler | `db`-Container noch nicht ready | Warten; Healthcheck wiederholt bis zu 10×; `docker compose logs db` prüfen |
| `alembic upgrade head` schlägt fehl | Inkompatible Migration | `docker compose down -v && docker compose up --build` |
| `OPENAI_API_KEY` fehlt | `.env` nicht angelegt | `.env` nach Abschnitt 1 anlegen |
| Port 80 belegt | Anderer lokaler Webserver läuft | `docker compose down` des anderen Projekts oder Port in `docker-compose.yml` anpassen |

---

## Verzeichnisstruktur

```
src/
├── backend/              # Python 3.13 / FastAPI
│   ├── alembic/          # Datenbankmigrationen
│   │   └── versions/
│   ├── app/              # Anwendungscode
│   ├── worker/           # pgqueuer Background Worker
│   ├── seed_users.py     # Testbenutzer anlegen
│   └── Dockerfile
├── frontend/             # React 18 / TypeScript 5
│   └── Dockerfile
├── docker-compose.yml
└── docker-compose.debug.yml
```

---

## Architektur-Hintergrund

Der Stack besteht aus vier Docker-Compose-Services (ADR-001):

```
webapp   React 18 / Nginx          → Port 80
api      Python 3.13 / FastAPI     → Port 8000 (intern)
worker   pgqueuer                  → kein externer Port
db       PostgreSQL 17 + pgvector  → Port 5432 (intern)
```

Vollständige Architekturentscheide: [`Docs/`](../Docs/).
