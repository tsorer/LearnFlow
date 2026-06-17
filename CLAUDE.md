# CLAUDE.md

Meta & Referenzen. Massgebliche Entscheide stehen in `Docs/` (Single Source of Truth),
Backlog in **GitHub Issues** (`T-01 … T-38`). Code in `src/`, Setup in `src/README.md`.

## Projekt-Struktur

```
Docs/             Massgebliche Entscheide: ADRs, C4-Diagramme, Anforderungen, Quality Attributes (Single Source of Truth)
src/              Anwendungscode + Docker-Compose, Makefile, README
  backend/        Python 3.13 / FastAPI, Alembic-Migrationen, pgqueuer-Worker, Tests
  frontend/       React 18 / TypeScript / Vite
Ops/              Betrieb: CI-Runbook, Pilotstart-Checkliste
LearningCorpus/   Fachkorpus (SKOS-Richtlinien, EU AI Act) + Gold-Eval-Datasets (Grundlage ADR-009)
.github/          CI-Workflow (Actions) + Issue-Templates
Artefakten/       Historische Kursartefakte nach Modul/Tag — können veraltet sein, Docs/ hat Vorrang
Niklaus/ Reto/    Individuelle Arbeits-/Spike-Verzeichnisse — nicht massgeblich
Frank/ Christoph/
```

## Stack

- **Backend:** Python 3.13 / FastAPI (ASGI) — `src/backend`
- **Frontend:** React 18 / TypeScript 5 / Vite / Nginx — `src/frontend`
- **DB:** PostgreSQL 17 + pgvector (HNSW) + tsvector/GIN (Volltext, deutsch)
- **Worker:** pgqueuer (PostgreSQL-nativ, kein Redis)
- **LLM/Embeddings:** via LiteLLM — MVP: OpenAI Direct · Prod: Azure OpenAI EU
- **Deployment:** Docker Compose, 4 Container `webapp / api / worker / db`
  (Shortcuts: `make up`, `make seed`, `make qa`)

## Architektur (mit ADR-Referenzen)

- **ADR-001** Modular Monolith, Docker Compose · **ADR-002** Stack (Batch-Response, kein SSE)
- **ADR-003** Persistenz: PostgreSQL + pgvector, Dokumente als `bytea` ≤ 10 MB
- **ADR-004** LLM-Provider (LiteLLM) · **ADR-005** Embedding `text-embedding-3-small`
- **ADR-006** Worker pgqueuer · **ADR-007** Hybrid-Retrieval (Dense + Sparse, RRF)
- **ADR-008** Fail-closed Konfidenz-Pipeline · **ADR-009** Eval (Gold-Dataset, RAGAS, CI-Gate)
- **ADR-010** API-First (OpenAPI 3.0)

Details: `Docs/04_ADR-00X_*.md`, `Docs/05_C4-*`, `Docs/06_Architecture-Draft.md`.

## Arbeitsweise (vor dem Coden)

- **Erst denken:** Annahmen explizit nennen; bei Mehrdeutigkeit Optionen aufzeigen
  statt still zu wählen; bei Unklarheit nachfragen.
- **Minimal:** kleinster Code, der das Problem löst — nichts Spekulatives, keine
  Über-Abstraktion, keine ungefragten Features.
- **Chirurgisch:** nur ändern, was die Aufgabe erfordert; bestehenden Stil übernehmen;
  angrenzenden Code nicht „mitverbessern".
- **Zielgetrieben:** Aufgabe in testbare Kriterien + kurzen Plan überführen, dann gegen
  diese Kriterien verifizieren (→ Definition of Done).

## Konventionen (Tests, Branches, PRs)

- **Definition of Done:** Vor „fertig" die Akzeptanzkriterien des Issues benennen,
  dagegen selbst prüfen, und `make qa` muss grün sein. Bei Unsicherheit ein bestehendes
  Modul als Vorlage nehmen statt neu zu erfinden.
- **Tests/Checks:** `make qa` läuft lokal exakt wie die CI — Backend `ruff` + `mypy` +
  `pytest`, Frontend `eslint` + `tsc --noEmit` + `vitest`. Details: `Ops/09_CI-Runbook.md`.
- **Branches:** nie direkt auf `main` — Feature-Branch + PR.
- **PRs:** CI grün (Required Checks `backend` + `frontend`), Review durch zweite Person
  (DoD). `package-lock.json` committen — CI nutzt `npm ci`.
- **Sprache:** Docs/Ordner Deutsch; Code-Identifier und Commits Englisch.

## Was Claude NICHT tun soll

- **Nicht auf `main` committen/pushen** — immer Branch + PR.
- **Keine Secrets / `.env` committen.**
- **`package.json` nicht von Hand editieren** — `npm install` nutzen, Lockfile committen.
- **Keine inhaltlichen Entscheide in dieser Datei** — die gehören in `Docs/`.
- **Fail-closed-Schwellen (ADR-008) nicht aufweichen** (z. B. `>=` → `>`); Eval-Gates
  (ADR-009) nicht umgehen.
- **Im MVP keine echten internen Dokumente** über OpenAI Direct — Wechsel auf
  Azure OpenAI EU ist Vorbedingung (ADR-004, Pilotstart-Checkliste).
- **Spike-Verzeichnisse** (`Niklaus/`, `Reto/`, `Frank/`, `Christoph/`) und `Artefakten/`
  nicht als Quelle der Wahrheit behandeln — massgeblich sind `Docs/` + `src/`.
