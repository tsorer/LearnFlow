# CLAUDE.md

Meta & Referenzen. Massgebliche Entscheide stehen in `Docs/` (Single Source of Truth),
Backlog in **GitHub Issues** (`T-01 … T-38`). Code in `src/`, Setup in `src/README.md`.

## Projekt-Struktur

```
Docs/             Entscheide: ADRs, C4-Diagramme, Anforderungen, Quality Attributes
src/              Anwendungscode + Docker-Compose, Makefile, README
  backend/        Python 3.13 / FastAPI, Alembic-Migrationen, pgqueuer-Worker, Tests
  backend/openapi.yaml
                  OpenAPI-Spec
  frontend/       React 18 / TypeScript / Vite
Ops/              Betrieb: CI-Runbook, Pilotstart-Checkliste
LearningCorpus/   Fachkorpus (SKOS-Richtlinien, EU AI Act) + Gold-Eval-Datasets (Grundlage ADR-009)
.github/          CI-Workflow (Actions) + Issue-Templates
.claudeignore     Verzeichnisse, die ignoriert werden sollen
Artefakten/       Historische Kursartefakte nach Modul/Tag — können veraltet sein
Niklaus/ Reto/    Individuelle Arbeits-/Spike-Verzeichnisse
Frank/ Christoph/
```

## Stack

- **Backend:** Python 3.13 / FastAPI (ASGI) — `src/backend`
- **Frontend:** React 18 / TypeScript 5 / Vite / Nginx — `src/frontend`
- **DB:** PostgreSQL 17 + pgvector (HNSW) + tsvector/GIN (Volltext, deutsch)
- **Worker:** pgqueuer (PostgreSQL-nativ, kein Redis)
- **LLM/Embeddings:** via LiteLLM — MVP: OpenAI Direct · Prod: Azure OpenAI EU
- **Deployment:** Docker Compose, 4 Container `webapp / api / worker / db`

## Architektur (mit ADR-Referenzen)

- **ADR-001** Modular Monolith, Docker Compose · 
- **ADR-002** Stack (Batch-Response, kein SSE)
- **ADR-003** Persistenz: PostgreSQL + pgvector, Dokumente als `bytea` ≤ 10 MB
- **ADR-004** LLM-Provider (LiteLLM) · 
- **ADR-005** Embedding `text-embedding-3-small`
- **ADR-006** Worker pgqueuer · 
- **ADR-007** Hybrid-Retrieval (Dense + Sparse, RRF)
- **ADR-008** Fail-closed Konfidenz-Pipeline · 
- **ADR-009** Eval (Gold-Dataset, RAGAS, CI-Gate)
- **ADR-010** API-First (OpenAPI 3.0)

Details: `Docs/04_ADR-00X_*.md`, `Docs/05_C4-*`, `Docs/06_Architecture-Draft.md`.

## Qualität & Konventionen (Tests, Branches, PRs)

- **Tests/Checks:** `make qa` (aus `src/`) deckt die CI-Jobs `backend` und `frontend`
  ab — Backend `ruff check .` + `mypy app worker` + `pytest`, Frontend `npm run lint` +
  `npm run check` (tsc) + `npm run test`. Der dritte CI-Job `e2e` läuft **nicht** in
  `make qa`, weil er den vollständigen Stack braucht: separat `make up && make seed &&
  make e2e`. Details: `Ops/09_CI-Runbook.md`.
- **Einzelne Tests:** Backend `docker exec src-api-1 pytest <pfad>::<test>` ·
  Frontend (in `frontend/`) `npm run test -- <datei>`
- **Migrationen (Alembic):** `docker exec src-api-1 alembic upgrade head`
- **Setup, Logins, Container-Start, psql:** `src/README.md`.
- **Definition of Done:** Vor „fertig" die Akzeptanzkriterien des Issues benennen,
  selbst dagegen prüfen, `make qa` grün. Bei Unsicherheit ein bestehendes Modul als
  Vorlage nehmen statt neu zu erfinden.
- **Stil:** gilt, was `ruff`/`eslint` erzwingen; sonst bestehenden Stil im Modul übernehmen.
- **Branches:** nie direkt auf `main` — Feature-Branch + PR.
- **PRs:** CI grün (Required Checks `backend` + `frontend` + `e2e`), Review durch zweite Person.
  `package-lock.json` committen — CI nutzt `npm ci`.
- **Sprache:** Docs/Ordner Deutsch; Code-Identifier und Commits Englisch.

## Arbeitsweise (vor dem Coden)

- **Erst denken:** Annahmen explizit nennen; bei Mehrdeutigkeit Optionen aufzeigen
  statt still zu wählen; bei Unklarheit nachfragen.
- **Minimal & chirurgisch:** kleinster Code, der das Problem löst; nur ändern, was die
  Aufgabe erfordert; angrenzenden Code nicht „mitverbessern", keine ungefragten Features.
- **Zielgetrieben:** Aufgabe in testbare Kriterien + kurzen Plan überführen, dann gegen
  diese Kriterien verifizieren (→ Definition of Done).

## Entwicklungsprozess (verbindlich für jeden Issue)

- aktuellen Stand in GIT prüfen
- Wenn es noch kein Issue gibt, fragen ob ein neues Issue erstellt werden soll
- **Issue lesen** — GitHub Issue vollständig lesen; Akzeptanzkriterien und Scope erfassen.
- **Spec prüfen** — relevante Dokumente in `Docs/` konsultieren und mit dem Issue abgleichen.
   Bei Inkonsistenzen oder Unklarheiten: **zuerst rückfragen**, Docs anpassen, erst dann weiter.
- **Spec zuerst** — berührt eine Änderung die Schnittstelle (neuer Endpoint, geändertes
   Request-/Response-Feld, neuer Statuscode), zuerst `src/backend/openapi.yaml` anpassen und den
   Spec-Diff kurz zeigen. Erst danach implementieren. Nichts implementieren, was nicht in der Spec
   steht (ADR-010).
- **Spec und Code gehen zusammen** — `openapi.yaml` ist für beide Seiten verbindlich, in beide
   Richtungen. Ein neuer Endpoint braucht **im selben PR** drei Dinge, sonst ist die CI rot:
   1. den Eintrag in `openapi.yaml`,
   2. eine Route im Backend — bei noch offener Umsetzung ein Platzhalter mit `501` und einem
      `TODO (T-XX)`, Vorlage: `app/routers/query.py`. Kein erfundener Beispielinhalt, ADR-008 ist
      fail-closed,
   3. die neu generierten Frontend-Typen: `make generate-api`, `src/frontend/src/api/schema.d.ts`
      mitcommitten.
   Wer die Spec ändert, macht Punkt 3 — nicht das Frontend-Team später. Die drei Checks dazu:
   `tests/test_rbac.py` (beide Richtungen Code ↔ Spec) und `npm run check` (generierte Typen).
- **Erst coden wenn alles klar** — kein Code ohne vollständig verstandene, konsistente Anforderung.
- **Tests schreiben** — neue Geschäftslogik wird mit Unit- und Integrationstests getestet;
   jede RAG-Komponente muss isoliert testbar sein (→ DoD Kriterium 3).
- **Branch + PR** — immer auf Feature-Branch (`feat/T-XX-beschreibung`); PR wenn `make qa`
   grün;
- Pull-Request Name mit Branchname prefixen

## Tripwires — was Claude NICHT tun soll

- **Fail-closed-Schwellen (ADR-008) nicht aufweichen** (z. B. `>=` → `>`);
  Eval-Gates (ADR-009) nicht umgehen.
- **Im MVP keine echten internen Dokumente** über OpenAI Direct verarbeiten — Wechsel auf
  Azure OpenAI EU ist Vorbedingung (ADR-004, Pilotstart-Checkliste).
- **Keine Secrets / `.env` committen**; nicht auf `main` committen/pushen.
- **`package.json` nicht von Hand editieren** — `npm install` nutzen, Lockfile committen.
- **`src/frontend/src/api/schema.d.ts` nicht von Hand editieren** — generiert aus `openapi.yaml`
  (`make generate-api`). Von Hand geänderte Typen überleben die nächste Generierung nicht.
- **Keine inhaltlichen Entscheide in dieser Datei** — die gehören in `Docs/`.
- **Spike-Verzeichnisse** (`Niklaus/`, `Reto/`, `Frank/`, `Christoph/`) und `Artefakten/`
  nicht als Quelle der Wahrheit behandeln.
