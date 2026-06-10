$repo    = "tsorer/LearnFlow"
$project = 2

# Milestone-Nummern via API
$milestones = gh api repos/$repo/milestones | ConvertFrom-Json
$ms0 = ($milestones | Where-Object { $_.title -like "*Sprint 0*" }).number
$ms1 = ($milestones | Where-Object { $_.title -like "*Sprint 1*" }).number
Write-Host "Milestone Sprint 0: $ms0 / Sprint 1: $ms1"

# Standard DoD gemaess L3-Template (Docs/07_Definition-of-Done.md)
$dod = @'
- [ ] Review durch eine zweite Person (nicht Autor/Prompter)
- [ ] CI gruen: Lint + Type-Check + Tests (make check)
- [ ] Unit-Test fuer neue Logik vorhanden; RAG-Komponente isoliert aufrufbar (nur bei Backend-Logik)
- [ ] Eval-Gate nicht verschlechtert: Halluzinationsrate = 0%, Out-of-Corpus-Refusal >= 90% (nur bei RAG-Pipeline-Aenderungen)
- [ ] Akzeptanzkriterien manuell durchgespielt im laufenden System
- [ ] Code-Qualitaet geprueft: kein Ballast, korrekte Modulzuordnung, keine unnoetige Abstraktion
- [ ] ADR/Docs aktualisiert (nur wenn ein Architekturentscheid beruehrt ist)
'@

function Write-Body {
    param($body)
    $tmp = [System.IO.Path]::GetTempFileName() + ".md"
    $body | Out-File -FilePath $tmp -Encoding utf8
    return $tmp
}

function Update-Issue {
    param($num, $body)
    $tmp = Write-Body $body
    gh issue edit $num --repo $repo --body-file $tmp
    Remove-Item $tmp
    Write-Host "Gepatch: #$num"
}

function New-Issue {
    param($title, $body, $labels, $milestone = 0)
    $tmp = Write-Body $body
    $url = gh issue create --repo $repo --title $title --body-file $tmp --label $labels
    Remove-Item $tmp
    if ($url) {
        $num = $url -replace ".*/issues/", ""
        if ($milestone -gt 0) {
            gh api repos/$repo/issues/$num --method PATCH --field milestone=$milestone | Out-Null
        }
        Write-Host "Erstellt: $url"
        gh project item-add $project --owner tsorer --url $url
    } else {
        Write-Host "FEHLER: $title konnte nicht erstellt werden."
    }
}

# ===========================================================================
# PATCH bestehende Issues #8-#12 mit korrektem Template
# ===========================================================================

Write-Host "`n--- Patche bestehende Issues ---"

Update-Issue 8 @"
## Beschreibung
Services api, worker, db, frontend mit Health-Checks aufsetzen.

## Akzeptanzkriterien
- [ ] docker compose up startet alle 4 Services ohne Fehler
- [ ] Health-Checks fuer alle Services gruen
- [ ] Lokale Entwicklungsumgebung dokumentiert (README)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | DevOps |
| **Abhaengig von** | - |
| **Zugehoerige Story** | Phase 0 |
"@

Update-Issue 9 @"
## Beschreibung
CI Pipeline mit lint, type-check, pytest/vitest, build aufsetzen.

## Akzeptanzkriterien
- [ ] PR triggert automatisch CI
- [ ] Backend: ruff + mypy + pytest laufen durch
- [ ] Frontend: eslint + tsc --noEmit + vitest laufen durch
- [ ] Fehlgeschlagener Check blockiert Merge (Branch Protection auf main)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | DevOps |
| **Abhaengig von** | T-01 |
| **Zugehoerige Story** | Phase 0 |
"@

Update-Issue 10 @"
## Beschreibung
Alle Endpunkte aus US-01 bis US-05 als Stubs in der OpenAPI Spec definieren.

## Akzeptanzkriterien
- [ ] Alle Endpunkte aus US-01 bis US-05 vorhanden (auch als leere Stubs)
- [ ] Request/Response-Schemas fuer Auth und Dokument-Upload definiert
- [ ] Spec valide (openapi-spec-validator gruen)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | - |
| **Zugehoerige Story** | Phase 0 |
"@

Update-Issue 11 @"
## Beschreibung
Alembic-Migration mit allen Basistabellen: users, documents, chunks, embeddings, feedback, config.

## Akzeptanzkriterien
- [ ] Migration laeuft durch (alembic upgrade head) ohne Fehler
- [ ] Alle Tabellen mit korrekten Typen und Constraints angelegt
- [ ] pgvector Extension aktiviert
- [ ] Migration rueckwaerts anwendbar (alembic downgrade -1)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | DB |
| **Abhaengig von** | T-01 |
| **Zugehoerige Story** | US-05 |
"@

Update-Issue 12 @"
## Beschreibung
Login-Endpunkt mit JWT-Generierung (8h Gueltigkeit) und bcrypt-Passwort-Pruefung.

## Akzeptanzkriterien
- [ ] POST /auth/login mit gueltigem username/passwort liefert JWT
- [ ] Falsches Passwort -> 401
- [ ] Unbekannter User -> 401
- [ ] JWT enthaelt Rolle (Lernende / Bereichsverantwortlicher / Admin)
- [ ] Passwort ist bcrypt-gehasht in DB, Klartext nie gespeichert

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-03, T-04 |
| **Zugehoerige Story** | US-05 |
"@

# ===========================================================================
# NEUE Issues erstellen
# ===========================================================================

Write-Host "`n--- Erstelle neue Issues ---"

# --- US-05 ---

New-Issue "[T-05] DB-Script: users-Tabelle befuellen" @"
## Beschreibung
users-Tabelle mit username, bcrypt-Hash und Rolle befuellen (Lernende / Bereichsverantwortlicher / Admin).

## Akzeptanzkriterien
- [ ] Mindestens ein User pro Rolle vorhanden
- [ ] Passwoerter sind bcrypt-gehasht, kein Klartext
- [ ] Script idempotent (mehrfach ausfuehrbar ohne Fehler)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 1 |
| **Bereich** | DB |
| **Abhaengig von** | T-04 |
| **Zugehoerige Story** | US-05 |
"@ "db,SP-1"

New-Issue "[T-07] FastAPI: RBAC-Middleware" @"
## Beschreibung
Rollen-Pruefung auf allen geschuetzten Routen; nicht autorisierte Requests erhalten 401/403.

## Akzeptanzkriterien
- [ ] Request ohne Token -> 401
- [ ] Request mit ungueltigem Token -> 401
- [ ] Request mit korrektem Token, falscher Rolle -> 403
- [ ] Alle geschuetzten Routen pruefen die korrekte Rolle

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-06 |
| **Zugehoerige Story** | US-05 |
"@ "backend,SP-3"

New-Issue "[T-08] React: Login-Seite + JWT-Storage + Protected Routes" @"
## Beschreibung
Login-Formular, JWT-Storage im Memory (kein localStorage), Protected Routes mit Redirect.

## Akzeptanzkriterien
- [ ] Login-Formular sendet Credentials an POST /auth/login
- [ ] JWT wird nur im Memory gehalten (nicht localStorage/sessionStorage)
- [ ] Nicht-authentifizierter Zugriff auf geschuetzte Route -> Redirect zur Login-Seite
- [ ] Falsches Passwort zeigt Fehlermeldung

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-06 |
| **Zugehoerige Story** | US-05 |
"@ "frontend,SP-3"

New-Issue "[T-09] Integration-Test: Login-Flow E2E" @"
## Beschreibung
E2E-Test: Login-Flow vollstaendig testen; geschuetzte Route ohne Token -> Redirect zur Login-Seite.

## Akzeptanzkriterien
- [ ] Happy-Path: Login -> geschuetzte Route erreichbar
- [ ] Ohne Token: Redirect zur Login-Seite
- [ ] Test laeuft automatisch in CI

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 2 |
| **Bereich** | Backend |
| **Abhaengig von** | T-07, T-08 |
| **Zugehoerige Story** | US-05 |
"@ "backend,SP-2"

# --- US-04 ---

New-Issue "[T-10] FastAPI: POST /documents (Datei-Upload)" @"
## Beschreibung
Datei-Upload-Endpunkt: PDF/DOCX/MD, 10 MB Limit serverseitig, Zeitstempel, bytea in DB.

## Akzeptanzkriterien
- [ ] Unterstuetzte Formate: PDF, DOCX, MD
- [ ] Dateien ueber 10 MB -> 413
- [ ] Datei wird als bytea mit Zeitstempel in DB gespeichert
- [ ] Nur Bereichsverantwortlicher kann hochladen (RBAC)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-03, T-04, T-07 |
| **Zugehoerige Story** | US-04 |
"@ "backend,SP-5"

New-Issue "[T-11] pgqueuer: Job-Queue Setup" @"
## Beschreibung
Job-Queue mit pgqueuer aufsetzen; Job 'process_document' nach Upload einreihen.

## Akzeptanzkriterien
- [ ] Nach erfolgreichem Upload wird Job 'process_document' eingereiht
- [ ] Job-Status abrufbar (pending / processing / done / failed)
- [ ] Worker-Prozess startet mit Docker Compose

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-01, T-10 |
| **Zugehoerige Story** | US-04 |
"@ "backend,SP-3"

New-Issue "[T-12] Background Worker: Parsing + Chunking" @"
## Beschreibung
Dokument parsen (PyMuPDF fuer PDF, python-docx fuer DOCX, direkt fuer MD) und chunken (512 Token, 50 Token Overlap).

## Akzeptanzkriterien
- [ ] PDF, DOCX und MD werden korrekt geparst
- [ ] Chunks: 512 Token, 50 Token Overlap
- [ ] Chunks werden in der DB gespeichert

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-11 |
| **Zugehoerige Story** | US-04 |
"@ "backend,SP-5"

New-Issue "[T-13] Background Worker: Embedding + pgvector HNSW-Index" @"
## Beschreibung
Chunks via OpenAI text-embedding-3-small einbetten und in pgvector HNSW-Index speichern.

## Akzeptanzkriterien
- [ ] Embeddings werden fuer alle Chunks generiert
- [ ] Vektoren im pgvector HNSW-Index gespeichert
- [ ] Embedding-Fehler fuehren zu Job-Status 'failed' (kein stiller Fehler)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-12 |
| **Zugehoerige Story** | US-04 |
"@ "backend,SP-5"

New-Issue "[T-14] FastAPI: GET /documents + DELETE /documents/{id}" @"
## Beschreibung
Dokumentenliste (nur eigener Bereich) und Loeschen eines Dokuments.

## Akzeptanzkriterien
- [ ] GET /documents liefert nur Dokumente des eigenen Bereichs
- [ ] DELETE /documents/{id} entfernt Dokument und zugehoerige Chunks
- [ ] Nicht-autorisierter Zugriff -> 403

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-10 |
| **Zugehoerige Story** | US-04 |
"@ "backend,SP-3"

New-Issue "[T-15] Versionierung: gleicher Dateiname ersetzt Dokument" @"
## Beschreibung
Upload mit gleichem Dateinamen ersetzt bestehendes Dokument: alte Chunks loeschen, neu indexieren.

## Akzeptanzkriterien
- [ ] Upload mit bestehendem Dateinamen ersetzt das alte Dokument
- [ ] Alte Chunks und Embeddings werden geloescht
- [ ] Neues Dokument wird vollstaendig neu indexiert

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-13, T-14 |
| **Zugehoerige Story** | US-04 |
"@ "backend,SP-3"

New-Issue "[T-16] React: Upload-UI" @"
## Beschreibung
Drag & Drop Upload-UI mit Fortschrittsanzeige (Polling auf Job-Status) und Fehlermeldung bei > 10 MB.

## Akzeptanzkriterien
- [ ] Drag & Drop und Klick-Upload funktionieren
- [ ] Fortschrittsanzeige per Polling auf Job-Status
- [ ] Fehlermeldung bei Dateien ueber 10 MB
- [ ] Unterstuetzte Formate sichtbar kommuniziert

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-10, T-14 |
| **Zugehoerige Story** | US-04 |
"@ "frontend,SP-3"

# --- US-01 ---

New-Issue "[T-17] FastAPI: POST /query (Retrieval)" @"
## Beschreibung
Anfrage-Embedding + HNSW-Retrieval (Top-k Chunks aus pgvector).

## Akzeptanzkriterien
- [ ] POST /query nimmt Frage entgegen und gibt Top-k Chunks zurueck
- [ ] Anfrage-Embedding via OpenAI text-embedding-3-small
- [ ] HNSW-Suche in pgvector

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-13, T-07 |
| **Zugehoerige Story** | US-01 |
"@ "backend,SP-5"

New-Issue "[T-18] LiteLLM-Integration: Prompt-Template + Antwort-Generierung" @"
## Beschreibung
Prompt-Template (System + Kontext-Chunks + Frage) und Antwort-Generierung via LiteLLM.

## Akzeptanzkriterien
- [ ] Prompt-Template enthaelt System-Anweisung, Kontext-Chunks und Nutzerfrage
- [ ] Antwort wird via LiteLLM generiert
- [ ] LLM-Provider austauschbar (LiteLLM-Abstraktion)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-17 |
| **Zugehoerige Story** | US-01 |
"@ "backend,SP-5"

New-Issue "[T-19] Quellenreferenz-Validierung" @"
## Beschreibung
Antwort ohne validierbare Quellenreferenz wird nicht zurueckgegeben.

## Akzeptanzkriterien
- [ ] Jede Antwort enthaelt mindestens eine Quellenreferenz
- [ ] Nicht validierbare Quellenreferenz -> Antwort wird unterdrueckt
- [ ] Unterdrueckte Antwort fuehrt zu definiertem Fallback-Text

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-18 |
| **Zugehoerige Story** | US-01 |
"@ "backend,SP-3"

New-Issue "[T-20] React: Frage-UI" @"
## Beschreibung
Eingabefeld (3-1000 Zeichen, clientseitig validiert), Ladeanzeige, Antwort mit klickbaren Quellenverweisen.

## Akzeptanzkriterien
- [ ] Eingabefeld validiert 3-1000 Zeichen clientseitig
- [ ] Ladeanzeige waehrend Antwort-Generierung
- [ ] Antwort wird mit klickbaren Quellenverweisen angezeigt

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-17 |
| **Zugehoerige Story** | US-01 |
"@ "frontend,SP-5"

New-Issue "[T-21] Quellenlink: Originaldokument-Viewer" @"
## Beschreibung
Klick auf Quellverweis oeffnet Originaldokument-Viewer mit hervorgehobenem Abschnitt.

## Akzeptanzkriterien
- [ ] Klick auf Quellverweis oeffnet Viewer
- [ ] Relevanter Abschnitt ist hervorgehoben
- [ ] Viewer zeigt das korrekte Originaldokument

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-20 |
| **Zugehoerige Story** | US-01 |
"@ "frontend,SP-3"

New-Issue "[T-22] Performance-Test: p95-Latenz <= 10s" @"
## Beschreibung
p95-Latenz unter Normallast mit k6 oder pytest-benchmark messen und dokumentieren.

## Akzeptanzkriterien
- [ ] p95-Latenz <= 10s unter Normallast
- [ ] Test-Setup und Ergebnisse dokumentiert
- [ ] Test laeuft in CI

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 2 |
| **Bereich** | Backend |
| **Abhaengig von** | T-19 |
| **Zugehoerige Story** | US-01 |
"@ "backend,SP-2"

# --- US-02 ---

New-Issue "[T-23] Konfidenz-Score-Berechnung" @"
## Beschreibung
Semantische Aehnlichkeit zwischen Antwort und Top-k-Chunks als Konfidenz-Score berechnen.

## Akzeptanzkriterien
- [ ] Konfidenz-Score wird fuer jede Antwort berechnet
- [ ] Score basiert auf semantischer Aehnlichkeit Antwort <-> Top-k-Chunks
- [ ] Score wird mit der Antwort zurueckgegeben

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-18 |
| **Zugehoerige Story** | US-02 |
"@ "backend,SP-5"

New-Issue "[T-24] DB config-Tabelle: Konfidenz-Schwellenwert" @"
## Beschreibung
Konfidenz-Schwellenwert in config-Tabelle speichern und ohne Neustart wirksam machen.

## Akzeptanzkriterien
- [ ] Konfidenz-Schwellenwert in DB config-Tabelle gespeichert
- [ ] Aenderung wirkt sofort ohne Service-Neustart
- [ ] Default-Wert vorhanden

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 2 |
| **Bereich** | DB |
| **Abhaengig von** | T-04 |
| **Zugehoerige Story** | US-02 |
"@ "db,SP-2"

New-Issue "[T-25] Self-Check-Pipeline: LLM-Selbstevaluation" @"
## Beschreibung
LLM evaluiert selbst den Quellen-Anteil: < 80% -> 'Eingeschraenkt belegt', < 50% -> unterdrueckt.

## Akzeptanzkriterien
- [ ] LLM bewertet Quellen-Anteil der eigenen Antwort
- [ ] Unter 80%: Antwort als 'Eingeschraenkt belegt' markiert
- [ ] Unter 50%: Antwort wird unterdrueckt

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-23 |
| **Zugehoerige Story** | US-02 |
"@ "backend,SP-5"

New-Issue "[T-26] Unterdrueckungslogik einbinden" @"
## Beschreibung
Reihenfolge: Quellenreferenz-Pruefung -> Konfidenz-Score -> Self-Check-Pipeline einbinden.

## Akzeptanzkriterien
- [ ] Pipeline-Reihenfolge: Quellenreferenz -> Konfidenz -> Self-Check
- [ ] Jede Stufe kann Antwort unterdruecken oder markieren
- [ ] Unterdrueckte Antwort gibt definierten Fallback-Text zurueck

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-19, T-25 |
| **Zugehoerige Story** | US-02 |
"@ "backend,SP-3"

New-Issue "[T-27] React: Konfidenz-UI-Badges" @"
## Beschreibung
'Eingeschraenkt belegt' Badge (Farbe + Icon + Hinweistext) und 'Weiss ich nicht'-Meldung mit Reformulierungs-Tipp.

## Akzeptanzkriterien
- [ ] Badge 'Eingeschraenkt belegt' mit Farbe und Icon sichtbar
- [ ] 'Weiss ich nicht'-Meldung mit Reformulierungs-Tipp angezeigt
- [ ] Nutzer versteht den Unterschied zwischen den Zustaenden

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 2 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-26 |
| **Zugehoerige Story** | US-02 |
"@ "frontend,SP-2"

New-Issue "[T-28] Eval-Test-Set: 20 Out-of-Corpus-Fragen" @"
## Beschreibung
20 Out-of-Corpus-Fragen als Eval-Test-Set; automatisierter CI-Eval-Lauf (>= 90% 'Weiss ich nicht').

## Akzeptanzkriterien
- [ ] 20 Out-of-Corpus-Fragen definiert und dokumentiert
- [ ] CI-Eval-Lauf laeuft automatisch
- [ ] >= 90% der Out-of-Corpus-Fragen erhalten 'Weiss ich nicht' (DoD Kriterium 4)

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-26 |
| **Zugehoerige Story** | US-02 |
"@ "backend,SP-3"

# --- US-03 ---

New-Issue "[T-29] DB: feedback-Tabelle" @"
## Beschreibung
feedback-Tabelle anlegen: query_id, Bewertung, Kategorie, Freitext, pseudonymisierter Hash.

## Akzeptanzkriterien
- [ ] Tabelle mit allen Feldern angelegt
- [ ] Pseudonymisierter Hash statt Nutzer-ID gespeichert
- [ ] Migration laeuft durch

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 1 |
| **Bereich** | DB |
| **Abhaengig von** | T-04 |
| **Zugehoerige Story** | US-03 |
"@ "db,SP-1"

New-Issue "[T-30] FastAPI: POST /feedback" @"
## Beschreibung
Feedback-Endpunkt: Kategorie (ENUM) validieren, optionaler Freitext, pseudonymisierte Speicherung.

## Akzeptanzkriterien
- [ ] Kategorie als ENUM validiert
- [ ] Freitext optional (max 500 Zeichen)
- [ ] Nutzer-ID wird pseudonymisiert gespeichert

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-29, T-07 |
| **Zugehoerige Story** | US-03 |
"@ "backend,SP-3"

New-Issue "[T-31] React: Feedback-UI" @"
## Beschreibung
Feedback-UI: Daumen hoch/runter, Kategorie-Auswahl, optionales Freitext-Feld, Bestaetigung.

## Akzeptanzkriterien
- [ ] Daumen hoch/runter sichtbar und klickbar
- [ ] Kategorie-Auswahl nach Klick
- [ ] Optionales Freitext-Feld
- [ ] Bestaetigung nach Absenden

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-30 |
| **Zugehoerige Story** | US-03 |
"@ "frontend,SP-3"

New-Issue "[T-32] Stefan Dashboard: Feedback-Uebersicht" @"
## Beschreibung
Feedback-Uebersicht fuer Stefan (Bereichsverantwortlicher): Bewertung, Kategorie, Freitext — kein Personenbezug.

## Akzeptanzkriterien
- [ ] Alle Feedbacks des Bereichs sichtbar (ohne Personenbezug)
- [ ] Filterbar nach Bewertung und Kategorie
- [ ] Freitext lesbar

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-30, T-07 |
| **Zugehoerige Story** | US-03 |
"@ "frontend,SP-3"

# --- US-07+08 (SHOULD) ---

New-Issue "[T-33] FastAPI: POST /quiz/generate" @"
## Beschreibung
LLM generiert 5 Multiple-Choice-Fragen aus Chunks des Bereichs.

## Akzeptanzkriterien
- [ ] 5 Multiple-Choice-Fragen werden generiert
- [ ] Fragen basieren auf Chunks des eigenen Bereichs
- [ ] Jede Frage enthaelt 4 Optionen und die korrekte Antwort

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Backend |
| **Abhaengig von** | T-18, T-07 |
| **Zugehoerige Story** | US-07 |
"@ "backend,SP-5"

New-Issue "[T-34] DB: quiz_questions-Tabelle" @"
## Beschreibung
quiz_questions-Tabelle: Frage, Optionen, korrekte Antwort, Quellen-Chunk-ID, Status, Zeitstempel.

## Akzeptanzkriterien
- [ ] Alle Felder vorhanden
- [ ] Status-Feld: pending / approved / rejected
- [ ] Migration laeuft durch

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 2 |
| **Bereich** | DB |
| **Abhaengig von** | T-04 |
| **Zugehoerige Story** | US-08 |
"@ "db,SP-2"

New-Issue "[T-35] Stefan Quiz-Review Dashboard" @"
## Beschreibung
Fragen mit Quellen-Passage anzeigen, freigeben / ablehnen / editieren.

## Akzeptanzkriterien
- [ ] Alle generierten Fragen mit Quellen-Passage sichtbar
- [ ] Stefan kann Fragen freigeben, ablehnen oder editieren
- [ ] Status-Aenderungen werden gespeichert

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 5 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-33, T-34 |
| **Zugehoerige Story** | US-08 |
"@ "frontend,SP-5"

New-Issue "[T-36] React: Lara Quiz-UI" @"
## Beschreibung
Quiz-UI fuer Lara: 5 Fragen, Ergebnis mit richtig/falsch + Erklaerung + Quellen-Link.

## Akzeptanzkriterien
- [ ] 5 Fragen werden sequenziell angezeigt
- [ ] Ergebnis-Seite: richtig/falsch pro Frage
- [ ] Erklaerung und Quellen-Link bei jeder Frage

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-35 |
| **Zugehoerige Story** | US-07 |
"@ "frontend,SP-3"

# --- US-11 (SHOULD) ---

New-Issue "[T-37] FastAPI: PATCH /admin/config" @"
## Beschreibung
Konfidenz- und Stale-Schwellenwert setzen (wirkt sofort, nur Admin-Rolle).

## Akzeptanzkriterien
- [ ] Nur Admin-Rolle kann Werte aendern (sonst 403)
- [ ] Aenderung wirkt sofort ohne Neustart
- [ ] Audit-Log-Eintrag bei jeder Aenderung

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Backend |
| **Abhaengig von** | T-07, T-24 |
| **Zugehoerige Story** | US-11 |
"@ "backend,SP-3"

New-Issue "[T-38] React: Admin-Seite" @"
## Beschreibung
Formular fuer Konfidenz- und Stale-Schwellenwert, Audit-Log-Anzeige (wer hat wann geaendert).

## Akzeptanzkriterien
- [ ] Formular fuer beide Schwellenwerte vorhanden
- [ ] Aktueller Wert vorausgefuellt
- [ ] Audit-Log mit Zeitstempel und Nutzer (pseudonymisiert) sichtbar

## Definition of Done
$dod
## Metadaten
| Feld | Wert |
|---|---|
| **Story Points** | 3 |
| **Bereich** | Frontend |
| **Abhaengig von** | T-37 |
| **Zugehoerige Story** | US-11 |
"@ "frontend,SP-3"

Write-Host ""
Write-Host "Fertig: bestehende Issues gepatch + alle neuen Issues erstellt."
