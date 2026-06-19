# Plan: T-03 / Issue #10 — OpenAPI Spec Grundgerüst

## Context

ADR-010 legt **API-First** fest: Die `openapi.yaml` ist die verbindliche Schnittstellen-
Definition und wird geschrieben, *bevor* Backend/Frontend implementieren — Abweichungen im
Code gelten als Fehler, nicht die Spec. Aktuell existiert **keine** `openapi.yaml`; nur ein
teilweise implementierter Auth-Router (`/auth`) ist vorhanden. Frontend und Backend können
ohne formalen Vertrag nicht parallel arbeiten (genau das Problem, das ADR-010 löst).

Issue #10 (T-03) schließt diese Lücke: alle Endpunkte aus **US-01 … US-05** als Stubs in
einer handgepflegten OpenAPI-3.0-Spec definieren, mit vollständigen Request/Response-Schemas
für **Authentifizierung** und **Dokument-Upload**, validiert via `openapi-spec-validator`.

**Akzeptanzkriterien (aus dem Issue):**
- Alle Endpunkte aus US-01..US-05 als (leere) Stubs vorhanden.
- Request/Response-Schemas für Auth und Dokument-Upload definiert.
- Spec validiert erfolgreich mit `openapi-spec-validator`.

**Getroffene Entscheidungen (mit dem Nutzer geklärt):**
- Spec-Ort: `src/backend/openapi.yaml` (im Backend-Container testbar) — **ADR-010-Wortlaut
  „Projekt-Root" wird entsprechend auf `src/backend/openapi.yaml` präzisiert**.
- Pfad-Präfix: **`/api/...` durchgängig** (folgt C4-Docs).
- Login-Feld: **`username`** gemäß US-05.

> Hinweis: (2) und (3) weichen bewusst vom bereits implementierten Auth-Router ab
> (`/auth/login` mit `email`). Das ist korrekt für T-03 (Spec = Source of Truth, Design-First);
> die Angleichung des Codes an die Spec ist ein **separater Folge-Task**, nicht Teil dieses Issues.

## Endpunkte (Stubs) aus US-01..US-05

Alle unter Präfix `/api`. Sicherheits-Schema `bearerAuth` (HTTP Bearer / JWT) global, außer Login.

| US | Methode | Pfad | Auth | Schema-Tiefe |
|----|---------|------|------|--------------|
| US-05 | POST | `/api/auth/login` | keine | **voll** (Request+Response) |
| US-05 | GET | `/api/auth/me` | JWT | Stub (Response-Ref) |
| US-05 | POST | `/api/auth/logout` | JWT | Stub |
| US-01/02 | POST | `/api/query` | JWT | Stub (leichtes Request/Response-Gerüst) |
| US-03 | POST | `/api/feedback` | JWT | Stub |
| US-04 | POST | `/api/documents` | JWT (`knowledge_owner`) | **voll** (multipart Upload + Response) |
| US-04 | GET | `/api/documents` | JWT (`knowledge_owner`) | Stub (Liste) |
| US-04 | DELETE | `/api/documents/{document_id}` | JWT (`knowledge_owner`) | Stub |

Scope-Grenze: `/api/config` (US-11) und das Stefan-Dashboard (`GET /api/dashboard/feedback`)
gehören **nicht** zu US-01..US-05 → bewusst ausgelassen, um das Issue minimal zu halten.

„Stub" = Pfad + Methode + `summary`/`tags` + mind. eine `responses`-Antwort (2xx), damit die
Spec valide ist; nur Auth-Login und Dokument-Upload erhalten ausmodellierte Schemas.

## Umzusetzende Änderungen

### 1. `src/backend/openapi.yaml` (neu) — Kern des Issues
- `openapi: 3.0.3`, `info` (title `LearnFlow API`, version `0.1.0`), kurze `description`.
- `components.securitySchemes.bearerAuth`: `type: http`, `scheme: bearer`, `bearerFormat: JWT`.
- Global `security: [{ bearerAuth: [] }]`; auf `/api/auth/login` mit `security: []` überschreiben.
- `components.schemas` (voll ausmodelliert wo vom AC verlangt):
  - `LoginRequest` { `username`: string, `password`: string } — `required`.
  - `TokenResponse` { `access_token`: string, `token_type`: string=`bearer`, `role`: enum
    `[learner, knowledge_owner, admin]` }.
  - `DocumentUploadResponse` { `document_id`: string(uuid), `filename`, `upload_date`:
    date-time, `status`: enum `[processing, available, error]` }.
  - `Document` (Listeneintrag) + `DocumentList` (array).
  - `Error` { `detail`: string } — einheitliches Fehlerformat (kompatibel zu FastAPI-Default).
- `/api/auth/login`: `requestBody` → `LoginRequest` (application/json), `200` → `TokenResponse`,
  `401` → `Error`.
- `/api/documents` POST: `requestBody` `multipart/form-data` mit `file` (binary) + `area_id`,
  `201` → `DocumentUploadResponse`, `413` (zu groß, 10 MB-Limit), `415` (Format) → `Error`.
- Übrige Endpunkte: minimaler valider Stub (z. B. `200`/`204` + ggf. `$ref` `Error`),
  `tags` je US-Bereich (`auth`, `query`, `feedback`, `documents`).
- Orientierung an bestehender Namenskonvention (`LoginRequest`/`TokenResponse` aus
  `src/backend/app/routers/auth.py`).

### 2. `src/backend/requirements-dev.txt` — Validator-Dependency
- Zeile ergänzen: `openapi-spec-validator==0.7.1` (Version pinnen wie die übrigen Tools).
- Kein separates `pyyaml` nötig: `openapi_spec_validator.readers.read_from_filename` liest YAML
  (PyYAML kommt transitiv über die Dependencies des Validators).

### 3. `src/backend/tests/test_openapi_spec.py` (neu) — CI-Gate
- Analog zum bestehenden `tests/test_health.py` (Pattern dort übernehmen).
- Spec relativ zum Test laden: `Path(__file__).parent.parent / "openapi.yaml"`.
- Validieren:
  ```python
  from openapi_spec_validator import validate
  from openapi_spec_validator.readers import read_from_filename

  def test_openapi_spec_is_valid():
      spec, _ = read_from_filename(str(SPEC_PATH))
      validate(spec)  # wirft bei ungültiger Spec
  ```
- Zusatz-Assertions (leichtgewichtig, erfüllen „Stubs vorhanden"-AC explizit):
  prüfen, dass alle 8 erwarteten `path`+`method`-Kombinationen vorhanden sind und dass
  `LoginRequest`/`DocumentUploadResponse` unter `components.schemas` existieren.
- `tests/` wird laut Makefile **nicht** von `mypy` erfasst (`mypy app worker`) → keine
  strict-typing-Hürde für den Validator-Import.

### 4. `Docs/04_ADR-010_API-First.md` — Spec-Ort präzisieren
- Wortlaut „wird als `openapi.yaml` im Projekt-Root versioniert" → konkret auf
  `src/backend/openapi.yaml` ändern (Begründung: im Backend-Container/CI testbar). Minimaler
  Edit an Zeile 21; restliche ADR unverändert.

### 5. (Optional) `Src/Makefile` — Convenience-Target
- `validate-spec: docker exec src-api-1 python -m openapi_spec_validator openapi.yaml` als
  `.PHONY` ergänzen. **Nicht zwingend** — die Validierung läuft bereits über `make test-be`
  (pytest) und damit im CI-Gate. Nur aufnehmen, wenn ein dediziertes Kommando gewünscht ist.

## Bewusst NICHT in diesem Issue
- Keine Implementierung der Stub-Endpunkte (Query/Feedback/Documents-Router) — reine Spec.
- Kein Umzug des bestehenden `/auth`-Routers nach `/api/auth`, keine Umstellung von `email`→
  `username` im Code → **Folge-Task** (Code-an-Spec-Angleichung).
- Kein Abschalten der FastAPI-Auto-Spec (`openapi_url=None`) — separat, nicht vom AC verlangt.

## Verifikation (Definition of Done)
1. `cd src && make up` (Container starten; Image baut `requirements-dev.txt` mit dem neuen
   Validator neu — ggf. `docker compose build api` erzwingen).
2. `make test-be` → der neue `test_openapi_spec.py` muss grün sein (validiert Spec + prüft Stubs).
3. `make qa-be` (ruff + mypy + pytest) komplett grün; danach `make qa` für Full-Stack-Gate.
4. Manuelle AC-Prüfung: Spec einmal direkt validieren —
   `docker exec src-api-1 python -m openapi_spec_validator openapi.yaml` → „OK/valid".
   Optional Spec in Swagger-Editor öffnen und alle 8 Endpunkte + Auth-/Upload-Schemas sichten.
5. Branch + PR (nie direkt `main`); CI-Required-Checks `backend` + `frontend` grün; Review durch
   zweite Person. Push/PR übernimmt der Nutzer selbst.

**Relevante DoD-Punkte des Issues:** Code-Review (2. Person), CI grün (`make qa`),
Unit-Test für neue Logik (Spec-Validierung), AC manuell im laufenden System verifiziert,
ADR-Doku aktualisiert (ADR-010). Generische Template-Punkte (RAG isoliert aufrufbar,
Halluzinationsrate 0 %) sind für eine reine Spec-Aufgabe nicht anwendbar.
