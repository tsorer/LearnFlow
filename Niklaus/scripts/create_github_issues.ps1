# LearnFlow — GitHub Issues erstellen
# Ausfuehren in deiner PowerShell im Repo-Root: .\Niklaus\scripts\create_github_issues.ps1

$GH = "gh"
$MILESTONE_SPRINT1 = "Sprint 1"

Write-Host "=== LearnFlow GitHub Issues Setup ===" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------
Write-Host "`n--- Labels erstellen ---" -ForegroundColor Yellow
$labels = @(
    @{ name="backend";  color="0075ca"; desc="Backend (FastAPI/Python)" },
    @{ name="frontend"; color="7057ff"; desc="Frontend (React/TypeScript)" },
    @{ name="db";       color="e4e669"; desc="Database (PostgreSQL/pgvector)" },
    @{ name="devops";   color="d93f0b"; desc="DevOps (Docker/Infrastructure)" },
    @{ name="sp:1";     color="ededed"; desc="Story Points: 1" },
    @{ name="sp:2";     color="ededed"; desc="Story Points: 2" },
    @{ name="sp:3";     color="ededed"; desc="Story Points: 3" },
    @{ name="sp:5";     color="ededed"; desc="Story Points: 5" },
    @{ name="sp:8";     color="ededed"; desc="Story Points: 8" },
    @{ name="must";     color="b60205"; desc="MoSCoW: MUST" },
    @{ name="should";   color="fbca04"; desc="MoSCoW: SHOULD" },
    @{ name="could";    color="c5def5"; desc="MoSCoW: COULD" },
    @{ name="welle-1";  color="bfd4f2"; desc="Welle 1: Fundament" },
    @{ name="welle-2";  color="bfd4f2"; desc="Welle 2: Auth" },
    @{ name="welle-3";  color="bfd4f2"; desc="Welle 3: Dokument-Ingestion" },
    @{ name="welle-4";  color="bfd4f2"; desc="Welle 4: RAG-Pipeline" },
    @{ name="welle-5";  color="bfd4f2"; desc="Welle 5: Feedback + Admin" },
    @{ name="welle-6";  color="d4c5f9"; desc="Welle 6: SHOULD Features" },
    @{ name="welle-7";  color="d4c5f9"; desc="Welle 7: COULD Features" }
)
foreach ($l in $labels) {
    Write-Host "  Label: $($l.name)"
    & $GH label create $l.name --color $l.color --description $l.desc --force 2>&1 | Out-Null
}

# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------
Write-Host "`n--- Milestone erstellen ---" -ForegroundColor Yellow
Write-Host "  Milestone: $MILESTONE_SPRINT1"
& $GH api repos/{owner}/{repo}/milestones --method POST -f title="$MILESTONE_SPRINT1" -f description="Fundament + Auth (Welle 1-2)" 2>&1 | Out-Null

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
function New-Issue {
    param(
        [string]$Title,
        [string]$Body,
        [string]$Labels,
        [string]$Milestone = ""
    )
    Write-Host "  Issue: $Title"
    if ($Milestone) {
        & $GH issue create --title $Title --body $Body --label $Labels --milestone $Milestone 2>&1 | Out-Null
    } else {
        & $GH issue create --title $Title --body $Body --label $Labels 2>&1 | Out-Null
    }
}

# ---------------------------------------------------------------------------
# WELLE 1 + 2 — Sprint 1 (Fundament + Auth)
# ---------------------------------------------------------------------------
Write-Host "`n--- Welle 1: Infrastruktur [Sprint 1] ---" -ForegroundColor Green

New-Issue `
  -Title "[TASK-I-01] Docker Compose: 4 Container Setup" `
  -Body "**User Story:** Infrastruktur
**Story Points:** 3

### Beschreibung
Docker Compose mit 4 Containern (db, api, worker, webapp), Healthchecks und korrekter Startup-Reihenfolge.

### Akzeptanzkriterien
- [ ] db (pgvector/pgvector:pg17) startet mit Healthcheck
- [ ] api startet nach db (depends_on + condition: service_healthy)
- [ ] worker startet nach api
- [ ] webapp (Nginx) startet und ist auf Port 80 erreichbar
- [ ] docker compose up --build -d laeuft ohne Fehler

### Definition of Done
- [ ] Code implementiert und lokal getestet
- [ ] docker compose up startet alle 4 Container
- [ ] PR reviewed und approved

### Abhaengigkeiten
Keine" `
  -Labels "devops,sp:3,welle-1" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-I-02] Alembic Setup (async)" `
  -Body "**User Story:** Infrastruktur
**Story Points:** 1

### Beschreibung
Alembic fuer async Migrationen einrichten (env.py mit create_async_engine, alembic.ini ohne hardcodierte DB-URL).

### Akzeptanzkriterien
- [ ] alembic upgrade head laeuft ohne Fehler
- [ ] DB-URL kommt aus Settings (Pydantic), nicht aus alembic.ini
- [ ] Versions-Ordner vorhanden

### Definition of Done
- [ ] Code implementiert und lokal getestet
- [ ] Migration laeuft im api-Container durch
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-I-01" `
  -Labels "db,sp:1,welle-1" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-I-03] FastAPI Skeleton + Pydantic Settings + CORS" `
  -Body "**User Story:** Infrastruktur
**Story Points:** 2

### Beschreibung
FastAPI App-Instanz, Pydantic BaseSettings (aus .env), CORS fuer localhost und localhost:5173.

### Akzeptanzkriterien
- [ ] FastAPI app startet mit uvicorn
- [ ] Settings liest DB_PASSWORD, JWT_SECRET, OPENAI_API_KEY aus .env
- [ ] CORS erlaubt localhost:80 und localhost:5173
- [ ] Alle Router registriert

### Definition of Done
- [ ] Code implementiert und lokal getestet
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-I-01" `
  -Labels "backend,sp:2,welle-1" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-I-04] GET /health Endpoint" `
  -Body "**User Story:** Infrastruktur
**Story Points:** 1

### Beschreibung
Health-Endpoint fuer Docker-Healthcheck und Monitoring.

### Akzeptanzkriterien
- [ ] GET /health gibt {status: ok, db: ok} zurueck
- [ ] DB-Verbindung wird geprueft (SELECT 1)
- [ ] HTTP 200 bei Erfolg, HTTP 503 bei DB-Fehler

### Definition of Done
- [ ] Code implementiert und lokal getestet
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-I-03" `
  -Labels "backend,sp:1,welle-1" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-I-05] pg_dump Backup-Cron (taeglich)" `
  -Body "**User Story:** Infrastruktur
**Story Points:** 3

### Beschreibung
Taeglich automatischer pg_dump via Cron-Container in Docker Compose. Peer-Review-Pflicht vor Pilot-Start.

### Akzeptanzkriterien
- [ ] Backup-Container laeuft taeglich um 02:00
- [ ] Dump landet in gemounteten Volume (./backups/)
- [ ] Letzte 7 Backups werden behalten, aeltere geloescht
- [ ] Backup-Erfolg wird in Docker-Log geschrieben

### Definition of Done
- [ ] Code implementiert und lokal getestet
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-I-01" `
  -Labels "devops,sp:3,welle-1"

Write-Host "`n--- Welle 2: Auth / US-05 [Sprint 1] ---" -ForegroundColor Green

New-Issue `
  -Title "[TASK-05-01] DB Migration: users-Tabelle" `
  -Body "**User Story:** US-05 Authentifizierung
**Story Points:** 2

### Beschreibung
Alembic-Migration fuer users-Tabelle mit Rollen-Enum.

### Akzeptanzkriterien
- [ ] Tabelle: id, username (unique), password_hash, role (enum: learner/knowledge_owner/admin), area, created_at
- [ ] Migration laeuft up und down fehlerfrei
- [ ] Index auf username

### Definition of Done
- [ ] Migration erstellt und getestet
- [ ] alembic upgrade head laeuft im Container
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-I-02" `
  -Labels "db,sp:2,must,welle-2" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-05-02] Backend: bcrypt + JWT (create/decode)" `
  -Body "**User Story:** US-05 Authentifizierung
**Story Points:** 2

### Beschreibung
Passwort-Hashing mit bcrypt (passlib) und JWT-Erstellung/-Validierung mit python-jose.

### Akzeptanzkriterien
- [ ] hash_password(plain) -> hashed
- [ ] verify_password(plain, hashed) -> bool
- [ ] create_access_token(data, expires_delta) -> JWT
- [ ] decode_token(token) -> payload oder HTTPException 401
- [ ] JWT enthaelt sub (username), role, exp

### Definition of Done
- [ ] Unit-Tests fuer hash/verify/create/decode
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-I-03" `
  -Labels "backend,sp:2,must,welle-2" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-05-03] Backend: POST /auth/login + GET /auth/me" `
  -Body "**User Story:** US-05 Authentifizierung
**Story Points:** 1

### Beschreibung
Login-Endpoint gibt JWT zurueck. /me gibt aktuellen User zurueck.

### Akzeptanzkriterien
- [ ] POST /auth/login: username+password -> {access_token, token_type}
- [ ] Falsches Passwort -> HTTP 401
- [ ] GET /auth/me: JWT validieren -> {username, role, area}
- [ ] Token-Expiry: 8 Stunden

### Definition of Done
- [ ] Endpoint implementiert und getestet
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-05-01
- TASK-05-02" `
  -Labels "backend,sp:1,must,welle-2" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-05-04] Backend: JWT Dependency (get_current_user, require_role)" `
  -Body "**User Story:** US-05 Authentifizierung
**Story Points:** 2

### Beschreibung
FastAPI Dependencies fuer Authentifizierung und Rollenprüfung (RBAC).

### Akzeptanzkriterien
- [ ] get_current_user: Bearer-Token aus Header lesen, validieren, User-Objekt zurueckgeben
- [ ] require_role(role): Factory die HTTPException 403 wirft wenn Rolle nicht passt
- [ ] require_knowledge_owner und require_admin als fertige Shortcuts
- [ ] Kein Token -> HTTP 401

### Definition of Done
- [ ] Code implementiert
- [ ] In mind. einem Router verwendet und getestet
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-05-02" `
  -Labels "backend,sp:2,must,welle-2" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-05-05] seed_users.py: 6 Fixuser anlegen" `
  -Body "**User Story:** US-05 Authentifizierung
**Story Points:** 1

### Beschreibung
Script legt 6 feste User mit bcrypt-Hashes an (INSERT OR UPDATE). Kein Registration-Flow, kein Password-Reset-UI.

### Akzeptanzkriterien
- [ ] 6 User: frank/niklaus/reto/christoph (knowledge_owner/admin), stefan/lara (learner)
- [ ] Passwort wird als bcrypt-Hash in DB geschrieben
- [ ] Script ist idempotent (wiederholbar ohne Fehler)
- [ ] Ausfuehren: docker compose exec api python ../scripts/seed_users.py

### Definition of Done
- [ ] Script erstellt und dokumentiert
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-05-01" `
  -Labels "backend,sp:1,must,welle-2" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-05-06] Frontend: Login-Formular" `
  -Body "**User Story:** US-05 Authentifizierung
**Story Points:** 2

### Beschreibung
Login-Seite mit Username/Passwort-Formular und Fehlerhandling.

### Akzeptanzkriterien
- [ ] Formular: username + password Felder
- [ ] POST /auth/login aufrufen
- [ ] Fehlermeldung bei falschen Credentials (401)
- [ ] Bei Erfolg: Token speichern, weiterleiten zu ChatView
- [ ] Enter-Taste submittet das Formular

### Definition of Done
- [ ] Komponente implementiert
- [ ] Fehlerfall getestet
- [ ] PR reviewed und approved

### Abhaengigkeiten
Keine (kann parallel entwickelt werden)" `
  -Labels "frontend,sp:2,must,welle-2" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-05-07] Frontend: Token-Persistenz + Auth Context" `
  -Body "**User Story:** US-05 Authentifizierung
**Story Points:** 2

### Beschreibung
JWT in localStorage speichern, beim App-Start GET /auth/me aufrufen um Session wiederherzustellen.

### Akzeptanzkriterien
- [ ] Token wird in localStorage gespeichert
- [ ] Beim App-Start: GET /auth/me -> User-State setzen
- [ ] Bei 401 von /auth/me: Token loeschen, Login-Seite zeigen
- [ ] logout() loescht Token und redirectet zu Login

### Definition of Done
- [ ] Implementiert und getestet
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-05-03" `
  -Labels "frontend,sp:2,must,welle-2" `
  -Milestone $MILESTONE_SPRINT1

New-Issue `
  -Title "[TASK-05-08] Frontend: Protected Routes" `
  -Body "**User Story:** US-05 Authentifizierung
**Story Points:** 1

### Beschreibung
Nicht-eingeloggte User werden auf /login weitergeleitet.

### Akzeptanzkriterien
- [ ] Direkter URL-Aufruf ohne Token -> Redirect zu /login
- [ ] Nach Login: Redirect zurueck zur urspruenglichen URL
- [ ] Admin-Route /admin: zusaetzlich Rollenprüfung (nur admin)

### Definition of Done
- [ ] Implementiert und getestet
- [ ] PR reviewed und approved

### Abhaengigkeiten
- TASK-05-07" `
  -Labels "frontend,sp:1,must,welle-2" `
  -Milestone $MILESTONE_SPRINT1

# ---------------------------------------------------------------------------
# WELLE 3 — US-04 Dokument-Ingestion
# ---------------------------------------------------------------------------
Write-Host "`n--- Welle 3: US-04 Dokument-Ingestion ---" -ForegroundColor Green

New-Issue "[TASK-04-01] DB Migration: documents-Tabelle" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 2

### Beschreibung
Alembic-Migration fuer documents-Tabelle.

### Akzeptanzkriterien
- [ ] Felder: id, filename (unique per area), original_filename, content_type, raw_content (bytea), status (enum: pending/processing/available/failed), uploaded_by (FK users), uploaded_at, area
- [ ] Migration laeuft up/down fehlerfrei

### Abhaengigkeiten
- TASK-05-01" "db,sp:2,must,welle-3"

New-Issue "[TASK-04-02] DB Migration: chunks-Tabelle + HNSW + GIN Index" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 3

### Beschreibung
chunks-Tabelle mit pgvector HNSW-Index und PostgreSQL-Volltext GIN-Index.

### Akzeptanzkriterien
- [ ] Felder: id, document_id (FK cascade delete), content, tsvector (GIN-Index german), embedding Vector(1536), chunk_index, heading, page
- [ ] HNSW-Index: m=16, ef_construction=64, cosine distance
- [ ] GIN-Index auf tsvector

### Abhaengigkeiten
- TASK-04-01" "db,sp:3,must,welle-3"

New-Issue "[TASK-04-03] Backend: POST /documents (Upload)" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 3

### Beschreibung
Upload-Endpoint fuer PDF/DOCX/MD mit Validierung und Versions-Replace.

### Akzeptanzkriterien
- [ ] Multipart-Upload akzeptiert PDF, .docx, .md
- [ ] >100 MB -> HTTP 413 mit Fehlermeldung
- [ ] Falscher Typ -> HTTP 415
- [ ] Gleicher Dateiname im gleichen Bereich -> altes Dokument + Chunks ersetzen
- [ ] Job in pgqueuer einreihen, Status = pending
- [ ] Nur knowledge_owner/admin (RBAC)

### Abhaengigkeiten
- TASK-04-01
- TASK-05-04" "backend,sp:3,must,welle-3"

New-Issue "[TASK-04-04] Backend: GET /documents (Liste)" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 1

### Beschreibung
Dokumentenliste gefiltert nach Bereich des eingeloggten Users.

### Akzeptanzkriterien
- [ ] Response: id, filename, status, uploaded_at, uploaded_by
- [ ] Gefiltert nach area aus JWT-Claim
- [ ] Sortiert nach uploaded_at DESC

### Abhaengigkeiten
- TASK-04-01
- TASK-05-04" "backend,sp:1,must,welle-3"

New-Issue "[TASK-04-05] Backend: DELETE /documents/{id}" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 1

### Beschreibung
Dokument loeschen inkl. Kaskade auf Chunks.

### Akzeptanzkriterien
- [ ] Nur Dokumente des eigenen Bereichs loeschbar
- [ ] Chunks werden via FK cascade mitgeloescht
- [ ] Nur knowledge_owner/admin

### Abhaengigkeiten
- TASK-04-02
- TASK-05-04" "backend,sp:1,must,welle-3"

New-Issue "[TASK-04-06] Backend: Chunking-Service (PDF/DOCX/MD)" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 5

### Beschreibung
Struktur-bewusstes Chunking fuer alle 3 Formate. Groesster technischer Task in US-04.

### Akzeptanzkriterien
- [ ] PDF (pypdf): Text pro Seite, Heading-Erkennung
- [ ] DOCX (python-docx): Heading-Styles als Chunk-Grenzen
- [ ] MD: #-Header als Grenzen
- [ ] Splitting: Heading > Absatz > Satz, 512 Token / 64 Overlap (ADR-007)
- [ ] Metadaten pro Chunk: heading, page, chunk_index

### Abhaengigkeiten
Keine (kann parallel entwickelt werden)" "backend,sp:5,must,welle-3"

New-Issue "[TASK-04-07] Backend: Embedding-Service (LiteLLM)" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 2

### Beschreibung
Batch-Embedding via LiteLLM mit Retry bei Rate-Limit.

### Akzeptanzkriterien
- [ ] embed(texts) und embed_one(text) via litellm.aembedding
- [ ] BATCH_SIZE=32
- [ ] Exponential Backoff bei Rate-Limit-Fehler
- [ ] Modell aus Settings (text-embedding-3-small)

### Abhaengigkeiten
Keine (kann parallel entwickelt werden)" "backend,sp:2,must,welle-3"

New-Issue "[TASK-04-08] Backend: Worker Task process_document" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 3

### Beschreibung
Vollstaendiger Worker-Task: Dokument laden, chunken, embedden, in DB schreiben.

### Akzeptanzkriterien
- [ ] Status: pending -> processing -> available (oder failed bei Exception)
- [ ] Chunks mit CAST(:embedding AS vector) und to_tsvector('german') einfuegen
- [ ] 5-Minuten-SLA fuer Dokumente <= 50 Seiten / 10 MB
- [ ] Bei Exception: status=failed, Fehler geloggt

### Abhaengigkeiten
- TASK-04-02
- TASK-04-06
- TASK-04-07" "backend,sp:3,must,welle-3"

New-Issue "[TASK-04-09] Backend: pgqueuer Integration" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 2

### Beschreibung
Job-Queue via pgqueuer: enqueue im API, LISTEN im Worker.

### Akzeptanzkriterien
- [ ] enqueue_document(doc_id): raw SQL INSERT in pgqueuer-Tabelle + pg_notify
- [ ] worker/main.py: AsyncpgDriver + QueueManager + @qm.entrypoint
- [ ] Worker reconnectet bei DB-Verbindungsunterbruch

### Abhaengigkeiten
- TASK-04-01" "backend,sp:2,must,welle-3"

New-Issue "[TASK-04-10] Frontend: Dokumentliste-Komponente" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 2

### Beschreibung
Tabelle mit Dokumenten, Status-Badges und Aktionen.

### Akzeptanzkriterien
- [ ] Spalten: Dateiname, Status-Badge, Zeitstempel
- [ ] Status-Farben: pending=grau, processing=blau+Spinner, available=gruen, failed=rot
- [ ] Upload- und Delete-Buttons nur fuer knowledge_owner/admin sichtbar

### Abhaengigkeiten
Keine (Mock-Daten zuerst)" "frontend,sp:2,must,welle-3"

New-Issue "[TASK-04-11] Frontend: Upload-Komponente" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 3

### Beschreibung
Datei-Upload mit Drag&Drop und client-seitiger Validierung.

### Akzeptanzkriterien
- [ ] Datei-Picker + Drag&Drop-Zone
- [ ] Client-seitiger Typ-Check (.pdf/.docx/.md), Hinweistext bei Fehler
- [ ] POST /documents, Loading-State waehrend Upload
- [ ] Fehlerhandling: 413 (zu gross), 415 (falscher Typ), Netzwerkfehler

### Abhaengigkeiten
- TASK-04-03
- TASK-04-10" "frontend,sp:3,must,welle-3"

New-Issue "[TASK-04-12] Frontend: Status-Polling" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 2

### Beschreibung
Automatische Aktualisierung des Dokumentstatus waehrend Verarbeitung.

### Akzeptanzkriterien
- [ ] GET /documents alle 5 Sekunden solange pending/processing-Dokumente vorhanden
- [ ] Spinner + Text 'wird verarbeitet...' pro Zeile
- [ ] Polling stoppt wenn alle available/failed

### Abhaengigkeiten
- TASK-04-04
- TASK-04-10" "frontend,sp:2,must,welle-3"

New-Issue "[TASK-04-13] Frontend: Delete-Flow" "**User Story:** US-04 Inhalte aufnehmen
**Story Points:** 1

### Beschreibung
Loeschen mit Bestaetigungsdialog.

### Akzeptanzkriterien
- [ ] Bestaetigungsdialog nennt Dateinamen
- [ ] DELETE /documents/{id} aufrufen
- [ ] Liste wird sofort aktualisiert
- [ ] Fehlertoast bei Misserfolg

### Abhaengigkeiten
- TASK-04-05
- TASK-04-10" "frontend,sp:1,must,welle-3"

# ---------------------------------------------------------------------------
# WELLE 4 — US-01 + US-02 RAG-Pipeline
# ---------------------------------------------------------------------------
Write-Host "`n--- Welle 4: US-01 + US-02 RAG-Pipeline ---" -ForegroundColor Green

New-Issue "[TASK-01-01] DB Migration: query_sessions + answers" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 2

### Akzeptanzkriterien
- [ ] query_sessions: id, user_id FK, created_at
- [ ] answers: id, session_id FK, question, answer_text, citations JSONB, confidence_score, confidence_band (enum), created_at

### Abhaengigkeiten
- TASK-05-01" "db,sp:2,must,welle-4"

New-Issue "[TASK-02-01] DB Migration: config-Tabelle + Default-Werte" "**User Story:** US-02 Unsichere Antworten erkennen
**Story Points:** 1

### Akzeptanzkriterien
- [ ] config: key (PK), value, updated_at, updated_by
- [ ] Default-Zeilen: retrieval_threshold=0.35, citation_coverage_min=0.5, confidence_low=0.4, stale_days=90
- [ ] Schwellenwerte ohne Deployment aenderbar (US-02 AC)

### Abhaengigkeiten
- TASK-05-01" "db,sp:1,must,welle-4"

New-Issue "[TASK-01-02] Backend: Dense Retrieval (pgvector HNSW)" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 3

### Akzeptanzkriterien
- [ ] Cosine-Similarity-Suche via HNSW-Index
- [ ] Top-20 Kandidaten zurueckgeben mit similarity score
- [ ] Gefiltert nach Bereich

### Abhaengigkeiten
- TASK-04-02" "backend,sp:3,must,welle-4"

New-Issue "[TASK-01-03] Backend: Sparse Retrieval (tsvector german)" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 2

### Akzeptanzkriterien
- [ ] to_tsquery('german', ...) gegen tsvector-Spalte
- [ ] GIN-Index wird genutzt
- [ ] Top-20 Kandidaten mit ts_rank

### Abhaengigkeiten
- TASK-04-02" "backend,sp:2,must,welle-4"

New-Issue "[TASK-01-04] Backend: RRF Fusion + Retrieval Gate" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 2

### Beschreibung
Reciprocal Rank Fusion (k=60) kombiniert Dense+Sparse. Gate blockt LLM-Aufruf wenn kein Chunk Schwellenwert erreicht.

### Akzeptanzkriterien
- [ ] RRF: score = sum(1/(k+rank)), k=60
- [ ] Gate: mind. 1 Chunk mit cosine >= retrieval_threshold aus config
- [ ] Gate nicht erreicht -> direkt 'Weiss ich nicht', kein LLM-Aufruf
- [ ] Top-n=5 nach Fusion und Gate

### Abhaengigkeiten
- TASK-01-02
- TASK-01-03
- TASK-02-01" "backend,sp:2,must,welle-4"

New-Issue "[TASK-02-02] Backend: Retrieval-Konfidenz (Stage 1)" "**User Story:** US-02 Unsichere Antworten erkennen
**Story Points:** 3

### Beschreibung
Deterministisches Konfidenz-Scoring aus Retrieval-Ergebnissen (ADR-008).

### Akzeptanzkriterien
- [ ] Score = top_score*0.5 + mean_score*0.3 + density*0.2
- [ ] Unter Schwellenwert -> 'Weiss ich nicht'
- [ ] Schwellenwert aus config-Tabelle

### Abhaengigkeiten
- TASK-01-04" "backend,sp:3,must,welle-4"

New-Issue "[TASK-01-05] Backend: Grounding-Prompt + LLM-Aufruf (LiteLLM)" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 3

### Beschreibung
LLM bekommt nur gefilterte Chunks als Kontext. Grounding-Prompt zwingt zu Quellenangaben.

### Akzeptanzkriterien
- [ ] Prompt: 'Antworte nur aus dem bereitgestellten Kontext, zitiere jede Aussage mit [N]'
- [ ] Batch-Response (kein Streaming, ADR-002)
- [ ] Model aus Settings (gpt-4o-mini default)
- [ ] Bei LLM-Fehler: HTTP 503 mit Fehlermeldung

### Abhaengigkeiten
- TASK-01-04" "backend,sp:3,must,welle-4"

New-Issue "[TASK-02-03] Backend: Citation-Coverage-Check (Stage 2)" "**User Story:** US-02 Unsichere Antworten erkennen
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Regex findet [N]-Referenzen in Saetzen
- [ ] Coverage = belegte Saetze / alle Saetze
- [ ] < 50% -> Antwort unterdrückt
- [ ] < 80% -> 'Eingeschraenkt belegt' markiert

### Abhaengigkeiten
- TASK-01-05" "backend,sp:2,must,welle-4"

New-Issue "[TASK-02-04] Backend: Composite Confidence + Bands" "**User Story:** US-02 Unsichere Antworten erkennen
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Composite = retrieval*0.6 + citation*0.4
- [ ] 3 Baender: high/medium/low
- [ ] is_borderline() fuer Stage-3-Entscheid
- [ ] Band in Answer-Objekt gespeichert

### Abhaengigkeiten
- TASK-02-02
- TASK-02-03" "backend,sp:2,must,welle-4"

New-Issue "[TASK-02-05] Backend: LLM Self-Check (Stage 3, nur Grenzfaelle)" "**User Story:** US-02 Unsichere Antworten erkennen
**Story Points:** 3

### Akzeptanzkriterien
- [ ] Wird nur aufgerufen wenn is_borderline() == True
- [ ] Separater LLM-Aufruf mit Self-Check-Prompt
- [ ] Ergebnis fliesst in finale Entscheidung ein

### Abhaengigkeiten
- TASK-02-04" "backend,sp:3,must,welle-4"

New-Issue "[TASK-02-06] Backend: Weiss-ich-nicht Antwort + Hinweis" "**User Story:** US-02 Unsichere Antworten erkennen
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Meldung: 'Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden.'
- [ ] Kontextueller Hinweis zur Fragenanpraezisierung
- [ ] Out-of-Corpus-Testfragen: >= 90% 'Weiss ich nicht' (ADR-008)

### Abhaengigkeiten
- TASK-02-04" "backend,sp:1,must,welle-4"

New-Issue "[TASK-01-06] Backend: POST /query (volle Pipeline)" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 3

### Akzeptanzkriterien
- [ ] Eingabe: {question, session_id?}
- [ ] Validierung: 3-1000 Zeichen
- [ ] Volle Pipeline (Stages 0-3)
- [ ] Response: {answer, citations, confidence_score, confidence_band, session_id}
- [ ] Antwortzeit p95 <= 10 Sekunden

### Abhaengigkeiten
- TASK-01-01
- TASK-01-05
- TASK-02-04" "backend,sp:3,must,welle-4"

New-Issue "[TASK-01-07] Frontend: Chat-Input-Komponente" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Textarea mit Zeichenzaehler
- [ ] < 3 oder > 1000 Zeichen -> client-seitige Fehlermeldung, kein Submit
- [ ] Enter submittet, Shift+Enter = Zeilenumbruch
- [ ] Loading-State waehrend Anfrage

### Abhaengigkeiten
Keine" "frontend,sp:2,must,welle-4"

New-Issue "[TASK-01-08] Frontend: MessageBubble-Komponente" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 2

### Akzeptanzkriterien
- [ ] User-Bubble (rechts) und Assistant-Bubble (links)
- [ ] Citations-Liste aufklappbar
- [ ] Antworttext mit Quellenmarkierungen [N]

### Abhaengigkeiten
Keine" "frontend,sp:2,must,welle-4"

New-Issue "[TASK-01-09] Frontend: Citation-Link (Dokument + Seite)" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 2

### Beschreibung
MVP: Link auf Dokument + Seitenangabe. PDF.js-Highlighting ist Post-MVP (ADR-002).

### Akzeptanzkriterien
- [ ] Jede Citation zeigt: Dokumenttitel + Abschnitt + Upload-Datum
- [ ] Klick oeffnet Dokument (Download-Link)
- [ ] Seitenangabe sichtbar

### Abhaengigkeiten
- TASK-01-06
- TASK-01-08" "frontend,sp:2,must,welle-4"

New-Issue "[TASK-01-10] Frontend: Error States" "**User Story:** US-01 Quellenbelegte Frage-Antwort
**Story Points:** 1

### Akzeptanzkriterien
- [ ] LLM nicht erreichbar -> Fehlermeldung (kein erfundener Text)
- [ ] Leerer Korpus -> Hinweis
- [ ] Timeout -> Hinweis

### Abhaengigkeiten
- TASK-01-07" "frontend,sp:1,must,welle-4"

New-Issue "[TASK-02-07] Frontend: Confidence-Band-Anzeige" "**User Story:** US-02 Unsichere Antworten erkennen
**Story Points:** 2

### Akzeptanzkriterien
- [ ] high -> gruen, medium -> gelb, low -> rot
- [ ] Icon + Farbe + Tooltip mit Score
- [ ] In MessageBubble integriert

### Abhaengigkeiten
- TASK-01-08" "frontend,sp:2,must,welle-4"

New-Issue "[TASK-02-08] Frontend: Eingeschraenkt-belegt Warning" "**User Story:** US-02 Unsichere Antworten erkennen
**Story Points:** 2

### Akzeptanzkriterien
- [ ] < 80% Coverage: gelbes Banner 'Eingeschraenkt belegt' (Farbe + Icon + Text)
- [ ] Unterdrückte Antwort: Meldung statt Antworttext
- [ ] 'Weiss ich nicht': eigene visuelle Darstellung

### Abhaengigkeiten
- TASK-02-07" "frontend,sp:2,must,welle-4"

# ---------------------------------------------------------------------------
# WELLE 5 — US-03 Feedback + US-11 Admin
# ---------------------------------------------------------------------------
Write-Host "`n--- Welle 5: US-03 Feedback + US-11 Admin ---" -ForegroundColor Green

New-Issue "[TASK-03-01] DB Migration: feedback-Tabelle" "**User Story:** US-03 Feedback
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Felder: id, answer_id FK, rating (enum: positive/negative), category, freetext, user_hash (sha256), created_at
- [ ] Kein Bezug auf user_id (Pseudonymisierung)

### Abhaengigkeiten
- TASK-01-01" "db,sp:1,must,welle-5"

New-Issue "[TASK-03-02] Backend: POST /answers/{id}/feedback" "**User Story:** US-03 Feedback
**Story Points:** 2

### Akzeptanzkriterien
- [ ] sha256(user_id + salt) als user_hash
- [ ] Kategorie-Validierung (4 positive / 5 negative Kategorien)
- [ ] Freitext optional, max. 500 Zeichen

### Abhaengigkeiten
- TASK-03-01
- TASK-05-04" "backend,sp:2,must,welle-5"

New-Issue "[TASK-03-03] Frontend: Daumen-hoch/runter Buttons" "**User Story:** US-03 Feedback
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Thumbs-up / Thumbs-down nach jeder Antwort
- [ ] Nur einmal pro Antwort bewertbar
- [ ] Visuelles Feedback nach Auswahl

### Abhaengigkeiten
- TASK-01-08" "frontend,sp:1,must,welle-5"

New-Issue "[TASK-03-04] Frontend: Kategorie-Selektor" "**User Story:** US-03 Feedback
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Positiv: verstaendlich / vollstaendig / hilfreich fuer Code / Quelle passt
- [ ] Negativ: faktisch falsch / unvollstaendig / veraltet / unverstaendlich / Quelle stimmt nicht
- [ ] Gegenseitig exklusiv

### Abhaengigkeiten
- TASK-03-03" "frontend,sp:2,must,welle-5"

New-Issue "[TASK-03-05] Frontend: Freitext + Submit + Bestaetigung" "**User Story:** US-03 Feedback
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Optionales Freitext-Feld (max. 500 Zeichen)
- [ ] Submit ruft POST /feedback auf
- [ ] Bestaetigungsmeldung nach Speichern

### Abhaengigkeiten
- TASK-03-02
- TASK-03-04" "frontend,sp:1,must,welle-5"

New-Issue "[TASK-11-01] Backend: GET /admin/config" "**User Story:** US-11 Systemkonfiguration
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Gibt alle config-Zeilen zurueck
- [ ] Nur admin-Rolle

### Abhaengigkeiten
- TASK-02-01
- TASK-05-04" "backend,sp:1,should,welle-5"

New-Issue "[TASK-11-02] Backend: PUT /admin/config" "**User Story:** US-11 Systemkonfiguration
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Update einzelner Werte mit Zeitstempel und updated_by
- [ ] Aenderung wirkt sofort (naechster Query liest neuen Wert)
- [ ] Nur admin-Rolle

### Abhaengigkeiten
- TASK-11-01" "backend,sp:2,should,welle-5"

New-Issue "[TASK-11-03] Frontend: Admin-Page (Route /admin)" "**User Story:** US-11 Systemkonfiguration
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Route /admin nur fuer admin-Rolle
- [ ] Direkter URL-Aufruf ohne Rechte -> Redirect

### Abhaengigkeiten
- TASK-05-08" "frontend,sp:1,should,welle-5"

New-Issue "[TASK-11-04] Frontend: Config-Formular" "**User Story:** US-11 Systemkonfiguration
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Felder: Konfidenz-Schwellenwert + Stale-Tage
- [ ] Speichern-Button ruft PUT /admin/config auf
- [ ] Erfolgsbestaetigung + Fehlermeldung bei Misserfolg

### Abhaengigkeiten
- TASK-11-01
- TASK-11-03" "frontend,sp:2,should,welle-5"

# ---------------------------------------------------------------------------
# WELLE 6 — US-07, US-08, US-06 (SHOULD)
# ---------------------------------------------------------------------------
Write-Host "`n--- Welle 6: SHOULD Features (US-07, US-08, US-06) ---" -ForegroundColor Magenta

New-Issue "[TASK-07-01] DB Migration: quiz_questions-Tabelle" "**User Story:** US-07 Quiz-Fragen pruefen
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Felder: id, document_id FK, question, options JSONB, correct_index, explanation, source_chunk_id FK, status (enum: pending/approved/rejected), created_at, reviewed_at

### Abhaengigkeiten
- TASK-04-02" "db,sp:2,should,welle-6"

New-Issue "[TASK-07-02] Backend: POST /quiz/generate (LLM MCQ-Generierung)" "**User Story:** US-07 Quiz-Fragen pruefen
**Story Points:** 5

### Akzeptanzkriterien
- [ ] Manuell ausloesbarer Endpunkt (knowledge_owner/admin)
- [ ] LLM generiert N Multiple-Choice-Fragen aus Top-Chunks des Bereichs
- [ ] Grounding-Prompt: Fragen nur aus Kontext
- [ ] Gespeichert mit status=pending

### Abhaengigkeiten
- TASK-07-01
- TASK-01-05" "backend,sp:5,should,welle-6"

New-Issue "[TASK-07-03] Backend: GET /quiz/questions (Review-Liste)" "**User Story:** US-07 Quiz-Fragen pruefen
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Pending-Fragen mit Quellen-Passage
- [ ] Nur knowledge_owner/admin

### Abhaengigkeiten
- TASK-07-01
- TASK-05-04" "backend,sp:1,should,welle-6"

New-Issue "[TASK-07-04] Backend: PATCH /quiz/questions/{id} (approve/reject/edit)" "**User Story:** US-07 Quiz-Fragen pruefen
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Status: pending -> approved oder rejected
- [ ] Edit: Frage/Optionen aendern
- [ ] reviewed_at Timestamp setzen

### Abhaengigkeiten
- TASK-07-01
- TASK-05-04" "backend,sp:2,should,welle-6"

New-Issue "[TASK-07-05] Frontend: Quiz-Review-Dashboard" "**User Story:** US-07 Quiz-Fragen pruefen
**Story Points:** 3

### Akzeptanzkriterien
- [ ] Liste pending Fragen mit Quellen-Passage sichtbar
- [ ] Nur fuer knowledge_owner/admin

### Abhaengigkeiten
- TASK-07-03" "frontend,sp:3,should,welle-6"

New-Issue "[TASK-07-06] Frontend: Approve/Reject/Edit-Aktionen" "**User Story:** US-07 Quiz-Fragen pruefen
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Approve/Reject-Buttons pro Frage
- [ ] Inline-Edit-Formular fuer Frage und Optionen

### Abhaengigkeiten
- TASK-07-04
- TASK-07-05" "frontend,sp:2,should,welle-6"

New-Issue "[TASK-08-01] Backend: GET /quiz (5 zufaellige approved Fragen)" "**User Story:** US-08 Quiz absolvieren
**Story Points:** 2

### Akzeptanzkriterien
- [ ] 5 zufaellige approved Fragen fuer Bereich
- [ ] Leer wenn keine freigegebenen Fragen

### Abhaengigkeiten
- TASK-07-01" "backend,sp:2,should,welle-6"

New-Issue "[TASK-08-02] Backend: POST /quiz/submit" "**User Story:** US-08 Quiz absolvieren
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Antworten pruefen, Ergebnis berechnen
- [ ] Response: pro Frage richtig/falsch + korrekte Antwort + Erklaerung
- [ ] Kein personenbezogenes Speichern

### Abhaengigkeiten
- TASK-08-01" "backend,sp:2,should,welle-6"

New-Issue "[TASK-08-03] Frontend: Quiz-Start-Button" "**User Story:** US-08 Quiz absolvieren
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Button sichtbar, disabled wenn keine approved Fragen
- [ ] Hinweistext: 'Noch keine Quizfragen freigegeben'

### Abhaengigkeiten
- TASK-08-01" "frontend,sp:1,should,welle-6"

New-Issue "[TASK-08-04] Frontend: Quiz-UI (5 MCQ)" "**User Story:** US-08 Quiz absolvieren
**Story Points:** 3

### Akzeptanzkriterien
- [ ] 5 Multiple-Choice-Fragen nacheinander
- [ ] Fortschrittsanzeige (Frage X von 5)
- [ ] Submit am Ende

### Abhaengigkeiten
- TASK-08-02
- TASK-08-03" "frontend,sp:3,should,welle-6"

New-Issue "[TASK-08-05] Frontend: Quiz-Ergebnis-View" "**User Story:** US-08 Quiz absolvieren
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Pro Frage: richtig/falsch, korrekte Antwort, Erklaerung
- [ ] Direktlink zur belegenden Quelle

### Abhaengigkeiten
- TASK-08-04" "frontend,sp:2,should,welle-6"

New-Issue "[TASK-06-01] DB Migration: validated_at + stale_documents View" "**User Story:** US-06 Veraltete Inhalte (Post-MVP)
**Story Points:** 2

### Akzeptanzkriterien
- [ ] validated_at Spalte auf documents
- [ ] DB-View stale_documents: Dokumente > X Tage nicht validiert (X aus config)

### Abhaengigkeiten
- TASK-04-01" "db,sp:2,should,welle-6"

New-Issue "[TASK-06-02] Backend: GET /documents/stale" "**User Story:** US-06 Veraltete Inhalte (Post-MVP)
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Sortiert nach Alter und letztem Validierungsdatum
- [ ] Schwellenwert aus config-Tabelle

### Abhaengigkeiten
- TASK-06-01
- TASK-02-01" "backend,sp:1,should,welle-6"

New-Issue "[TASK-06-03] Backend: POST /documents/{id}/validate" "**User Story:** US-06 Veraltete Inhalte (Post-MVP)
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Setzt validated_at = now
- [ ] Nur knowledge_owner/admin

### Abhaengigkeiten
- TASK-06-01
- TASK-05-04" "backend,sp:1,should,welle-6"

New-Issue "[TASK-06-04] Frontend: Stale-Dashboard" "**User Story:** US-06 Veraltete Inhalte (Post-MVP)
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Liste sortierbar nach Alter / Validierungsdatum

### Abhaengigkeiten
- TASK-06-02" "frontend,sp:2,should,welle-6"

New-Issue "[TASK-06-05] Frontend: Re-Validierungs-Aktionen" "**User Story:** US-06 Veraltete Inhalte (Post-MVP)
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Aktionen: 'aktuell' / 'ersetzt durch ...' / 'entfernen'
- [ ] Bestaetigung vor Loeschen

### Abhaengigkeiten
- TASK-06-03
- TASK-06-04" "frontend,sp:2,should,welle-6"

# ---------------------------------------------------------------------------
# WELLE 7 — US-09, US-10 (COULD)
# ---------------------------------------------------------------------------
Write-Host "`n--- Welle 7: COULD Features (US-09, US-10) ---" -ForegroundColor DarkGray

New-Issue "[TASK-09-01] Backend: Session-Kontext (letzte 3 QA-Paare)" "**User Story:** US-09 Folgefragen
**Story Points:** 3

### Akzeptanzkriterien
- [ ] Letzte 3 QA-Paare der Session in Prompt einbinden
- [ ] POST /query: session_id nutzen fuer Kontext-Laden

### Abhaengigkeiten
- TASK-01-06" "backend,sp:3,could,welle-7"

New-Issue "[TASK-09-02] Backend: DELETE /query/sessions/{id}" "**User Story:** US-09 Folgefragen
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Session und Answers loeschen (nur eigene)

### Abhaengigkeiten
- TASK-01-01" "backend,sp:1,could,welle-7"

New-Issue "[TASK-09-03] Frontend: Gespraechshistorie (scrollbar)" "**User Story:** US-09 Folgefragen
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Alle Nachrichten der Session scrollbar sichtbar

### Abhaengigkeiten
- TASK-01-08" "frontend,sp:1,could,welle-7"

New-Issue "[TASK-09-04] Frontend: Neue-Konversation Button" "**User Story:** US-09 Folgefragen
**Story Points:** 1

### Akzeptanzkriterien
- [ ] Context Reset: DELETE /sessions/{id}, leere neue Session
- [ ] Bestaetigung wenn noch Nachrichten vorhanden

### Abhaengigkeiten
- TASK-09-02
- TASK-09-03" "frontend,sp:1,could,welle-7"

New-Issue "[TASK-10-01] DB: Clustering-Job (Embedding-Aehnlichkeit)" "**User Story:** US-10 Wissensluecken
**Story Points:** 3

### Akzeptanzkriterien
- [ ] Cluster-Zuweisung fuer answers speichern
- [ ] Hintergrund-Job (Worker)

### Abhaengigkeiten
- TASK-01-01" "db,sp:3,could,welle-7"

New-Issue "[TASK-10-02] Backend: GET /analytics/clusters" "**User Story:** US-10 Wissensluecken
**Story Points:** 5

### Akzeptanzkriterien
- [ ] Top-10 Cluster, nur wenn >= 5 Fragen (Datenschutz)
- [ ] Haeufigkeit + aggregierte Feedback-Quote
- [ ] Schwellenwert konfigurierbar (30 Tage / 20 Fragen)

### Abhaengigkeiten
- TASK-10-01" "backend,sp:5,could,welle-7"

New-Issue "[TASK-10-03] Frontend: Wissensluecken-Dashboard" "**User Story:** US-10 Wissensluecken
**Story Points:** 3

### Akzeptanzkriterien
- [ ] Top-10 Cluster mit Haeufigkeit und Feedback-Quote
- [ ] Schwellenwert konfigurierbar

### Abhaengigkeiten
- TASK-10-02" "frontend,sp:3,could,welle-7"

New-Issue "[TASK-10-04] Frontend: Cluster-Detail" "**User Story:** US-10 Wissensluecken
**Story Points:** 2

### Akzeptanzkriterien
- [ ] Beispielfragen und verwendete Quellen
- [ ] Direktlink zu Upload/Re-Validierung

### Abhaengigkeiten
- TASK-10-03" "frontend,sp:2,could,welle-7"

Write-Host "`n=== Fertig! ===" -ForegroundColor Cyan
Write-Host "Issues erstellt. Oeffne GitHub -> Projects -> Board und ziehe Sprint-1-Issues in 'To Do'."
Write-Host "Sprint-1-Issues: TASK-I-01 bis I-05 und TASK-05-01 bis 05-08"
