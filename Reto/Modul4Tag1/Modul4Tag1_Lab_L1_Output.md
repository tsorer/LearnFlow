# LearnFlow — Vollständiges Backlog (Lab L1)

*Modul 4 Tag 1 · Juni 2026*

---

> Definition of Done: siehe `Docs/07_Definition-of-Done.md`

---

## Backlog

### Legende

| Spalte           | Bedeutung                            |
| ---------------- | ------------------------------------ |
| **ID**           | Task-Identifier                      |
| **SP**           | Story Points (1 / 2 / 3 / 5 / 8)     |
| **Bereich**      | Backend / Frontend / DB / DevOps     |
| **Dauer**        | Geschätzte Arbeitszeit (max 4h)      |
| **Abhängig von** | Tasks, die zuerst fertig sein müssen |

---

### PHASE 0 — Fundament (Sprint 0)

*Muss vor allem anderen fertig sein. Kein Feature-Code ohne laufende Infrastruktur und API-Kontrakt.*

| ID   | Task                                                                                         | SP  | Bereich | Dauer | Abhängig von |
| ---- | -------------------------------------------------------------------------------------------- | --- | ------- | ----- | ------------ |
| T-01 | Docker Compose Setup: Services api, worker, db, frontend mit Health-Checks                   | 3   | DevOps  | 3h    | —            |
| T-02 | CI Pipeline (GitHub Actions): lint, type-check, pytest/vitest, build                         | 3   | DevOps  | 2h    | T-01         |
| T-03 | OpenAPI Spec Grundgerüst: alle Endpunkte aus US-01–05 als Stubs definieren                   | 3   | Backend | 3h    | —            |
| T-04 | DB-Schema Initial-Migration: Tabellen users, documents, chunks, embeddings, feedback, config | 3   | DB      | 3h    | T-01         |

**Phase-0-Summe: 12 SP**

---

### US-05 — Authentifizierung und Bereichszuordnung (MUST)

*Fundament für alle anderen Stories: kein Feature ohne Auth.*

| ID   | Task                                                                                                          | SP  | Bereich  | Dauer | Abhängig von |
| ---- | ------------------------------------------------------------------------------------------------------------- | --- | -------- | ----- | ------------ |
| T-05 | DB-Script: users-Tabelle befüllen (username, bcrypt-Hash, Rolle: Lernende / Bereichsverantwortlicher / Admin) | 1   | DB       | 1h    | T-04         |
| T-06 | FastAPI: POST /auth/login → JWT (8h), bcrypt-Passwort-Prüfung                                                 | 5   | Backend  | 4h    | T-03, T-04   |
| T-07 | FastAPI: RBAC-Middleware (Rollen-Prüfung auf allen geschützten Routen; 401/403)                               | 3   | Backend  | 3h    | T-06         |
| T-08 | React: Login-Seite + JWT-Storage im Memory + Protected Routes                                                 | 3   | Frontend | 3h    | T-06         |
| T-09 | Integration-Test: Login-Flow E2E, geschützte Route ohne Token → Redirect zur Login-Seite                      | 2   | Backend  | 2h    | T-07, T-08   |

**US-05-Summe: 14 SP**

---

### US-04 — Inhalte in den Lernkorpus aufnehmen (MUST)

*Voraussetzung für US-01 (Retrieval braucht Korpus). Stefan-Flow.*

| ID   | Task                                                                                                                       | SP  | Bereich  | Dauer | Abhängig von     |
| ---- | -------------------------------------------------------------------------------------------------------------------------- | --- | -------- | ----- | ---------------- |
| T-10 | FastAPI: POST /documents — Datei-Upload (PDF/DOCX/MD, 10 MB Limit serverseitig, Zeitstempel, bytea in DB)                  | 5   | Backend  | 4h    | T-03, T-04, T-07 |
| T-11 | pgqueuer: Job-Queue Setup — Job «process_document» einreihen nach Upload                                                   | 3   | Backend  | 3h    | T-01, T-10       |
| T-12 | Background Worker: Parsing (PyMuPDF für PDF, python-docx für DOCX, direkt für MD) + Chunking (512 Token, 50 Token Overlap) | 5   | Backend  | 4h    | T-11             |
| T-13 | Background Worker: Embedding via OpenAI text-embedding-3-small → pgvector HNSW-Index                                       | 5   | Backend  | 4h    | T-12             |
| T-14 | FastAPI: GET /documents — Dokumentenliste (nur eigener Bereich), DELETE /documents/{id}                                    | 3   | Backend  | 3h    | T-10             |
| T-15 | Versionierung: gleicher Dateiname ersetzt bestehendes Dokument (alte Chunks löschen, neu indexieren)                       | 3   | Backend  | 3h    | T-13, T-14       |
| T-16 | React: Upload-UI — Drag & Drop, Fortschrittsanzeige (Polling auf Job-Status), Fehlermeldung bei > 10 MB                    | 3   | Frontend | 3h    | T-10, T-14       |

**US-04-Summe: 27 SP**

---

### US-01 — Quellenbelegte Frage-Antwort (MUST)

*Kernfeature. Braucht laufenden Korpus (US-04) und Auth (US-05).*

| ID   | Task                                                                                                                       | SP  | Bereich  | Dauer | Abhängig von |
| ---- | -------------------------------------------------------------------------------------------------------------------------- | --- | -------- | ----- | ------------ |
| T-17 | FastAPI: POST /query — Anfrage-Embedding + HNSW-Retrieval (Top-k Chunks aus pgvector)                                      | 5   | Backend  | 4h    | T-13, T-07   |
| T-18 | LiteLLM-Integration: Prompt-Template (System + Kontext-Chunks + Frage) + Antwort-Generierung                               | 5   | Backend  | 4h    | T-17         |
| T-19 | Quellenreferenz-Extraktion: Antwort ohne validierbare Quellenreferenz wird nicht zurückgegeben                             | 3   | Backend  | 3h    | T-18         |
| T-20 | React: Frage-UI — Eingabefeld (3–1000 Zeichen, clientseitig validiert), Ladeanzeige, Antwort mit klickbaren Quellverweisen | 5   | Frontend | 4h    | T-17         |
| T-21 | Quellenlink: Klick öffnet Originaldokument-Viewer mit hervorgehobenem Abschnitt                                            | 3   | Frontend | 3h    | T-20         |
| T-22 | Performance-Test: p95-Latenz ≤ 10s unter Normallast (k6 oder pytest-benchmark, dokumentiert)                               | 2   | Backend  | 2h    | T-19         |

**US-01-Summe: 23 SP**

---

### US-02 — Unsichere Antworten klar erkennen (MUST)

*Parallel zu US-01 entwickelbar; teilt den /query-Endpunkt.*

| ID   | Task                                                                                                                  | SP  | Bereich  | Dauer | Abhängig von |
| ---- | --------------------------------------------------------------------------------------------------------------------- | --- | -------- | ----- | ------------ |
| T-23 | Konfidenz-Score-Berechnung: semantische Ähnlichkeit zwischen Antwort und Top-k-Chunks                                 | 5   | Backend  | 4h    | T-18         |
| T-24 | DB config-Tabelle: Konfidenz-Schwellenwert speichern + ohne Neustart wirksam                                          | 2   | DB       | 2h    | T-04         |
| T-25 | Self-Check-Pipeline: LLM-Selbstevaluation des Quellen-Anteils (< 80 % → «Eingeschränkt belegt», < 50 % → unterdrückt) | 5   | Backend  | 4h    | T-23         |
| T-26 | Unterdrückungslogik einbinden: Reihenfolge Quellenprüfung → Konfidenz-Score → Self-Check                              | 3   | Backend  | 3h    | T-19, T-25   |
| T-27 | React: «Eingeschränkt belegt» Badge (Farbe + Icon + Hinweistext) + «Weiss ich nicht»-Meldung mit Reformulierungs-Tipp | 2   | Frontend | 2h    | T-26         |
| T-28 | Eval-Test-Set: 20 Out-of-Corpus-Fragen, automatisierter CI-Eval-Lauf (≥ 90 % «Weiss ich nicht» — DoD Kriterium 4)     | 3   | Backend  | 3h    | T-26         |

**US-02-Summe: 20 SP**

---

### US-03 — Feedback zu Antworten geben (MUST)

*Braucht US-01 (Antworten müssen vorhanden sein) und Auth (Pseudonymisierung).*

| ID   | Task                                                                                                      | SP  | Bereich  | Dauer | Abhängig von |
| ---- | --------------------------------------------------------------------------------------------------------- | --- | -------- | ----- | ------------ |
| T-29 | DB: feedback-Tabelle (query_id, Bewertung, Kategorie, Freitext, pseudonymisierter Hash)                   | 1   | DB       | 1h    | T-04         |
| T-30 | FastAPI: POST /feedback — Validierung Kategorie (ENUM), optionaler Freitext, pseudonymisierte Speicherung | 3   | Backend  | 3h    | T-29, T-07   |
| T-31 | React: Feedback-UI — 👍/👎, Kategorie-Auswahl, optionales Freitext-Feld, Bestätigungs-Meldung             | 3   | Frontend | 3h    | T-30         |
| T-32 | Stefan Dashboard: Feedback-Übersicht (Bewertung, Kategorie, Freitext — kein Personenbezug)                | 3   | Frontend | 3h    | T-30, T-07   |

**US-03-Summe: 10 SP**

---

### US-07 + US-08 — Quiz generieren, prüfen, absolvieren (SHOULD)

*Braucht US-04 (Chunks als Quelle). US-08 braucht US-07.*

| ID   | Task                                                                                                  | SP  | Bereich  | Dauer | Abhängig von |
| ---- | ----------------------------------------------------------------------------------------------------- | --- | -------- | ----- | ------------ |
| T-33 | FastAPI: POST /quiz/generate — LLM generiert 5 Multiple-Choice-Fragen aus Chunks des Bereichs         | 5   | Backend  | 4h    | T-18, T-07   |
| T-34 | DB: quiz_questions-Tabelle (Frage, Optionen, korrekte Antwort, Quellen-Chunk-ID, Status, Zeitstempel) | 2   | DB       | 2h    | T-04         |
| T-35 | Stefan Quiz-Review Dashboard: Fragen mit Quellen-Passage anzeigen, freigeben / ablehnen / editieren   | 5   | Frontend | 4h    | T-33, T-34   |
| T-36 | React: Lara Quiz-UI — 5 Fragen, Ergebnis mit richtig/falsch + Erklärung + Quellen-Link                | 3   | Frontend | 3h    | T-35         |

**US-07+08-Summe: 15 SP**

---

### US-11 — Systemkonfiguration Admin-Seite (SHOULD)

*DB-Script ist der Fallback; Admin-UI ist Komfort. Kann nach US-05 gebaut werden.*

| ID   | Task                                                                                                     | SP  | Bereich  | Dauer | Abhängig von |
| ---- | -------------------------------------------------------------------------------------------------------- | --- | -------- | ----- | ------------ |
| T-37 | FastAPI: PATCH /admin/config — Konfidenz- und Stale-Schwellenwert setzen (wirkt sofort, nur Admin-Rolle) | 3   | Backend  | 3h    | T-07, T-24   |
| T-38 | React: Admin-Seite — Formular für beide Schwellenwerte, Audit-Log-Anzeige (wer hat wann geändert)        | 3   | Frontend | 3h    | T-37         |

**US-11-Summe: 6 SP**

---

## Gesamt-Story-Points

| Scope                     | Story Points |
| ------------------------- | ------------ |
| Phase 0 (Fundament)       | 12           |
| US-05 Authentifizierung   | 14           |
| US-04 Korpus-Verwaltung   | 27           |
| US-01 Frage-Antwort       | 23           |
| US-02 Konfidenz-Pipeline  | 20           |
| US-03 Feedback            | 10           |
| **MUST-Total**            | **106**      |
| US-07+08 Quiz             | 15           |
| US-11 Admin-Konfiguration | 6            |
| **SHOULD-Total**          | **21**       |
| **Gesamt**                | **127**      |

---

## Grobe Reihenfolge — Phasen

```
Phase 0: Fundament
  T-01 Docker Compose
  T-02 CI Pipeline
  T-03 OpenAPI Spec Grundgerüst
  T-04 DB-Schema Initial-Migration
        │
        ▼
Phase 1: Auth (US-05)
  T-05 DB-Script users
  T-06 Login-Endpunkt + JWT
  T-07 RBAC-Middleware
  T-08 React Login + Protected Routes
  T-09 Integration-Test
        │
        ├──────────────────────────┐
        ▼                          ▼
Phase 2a: Korpus (US-04)      Phase 2b: Konfidenz-Config
  T-10 Upload-API                T-24 config-Tabelle
  T-11 Job-Queue
  T-12 Parsing + Chunking
  T-13 Embedding + pgvector
  T-14 Dok-Liste + Delete
  T-15 Versionierung
  T-16 Upload-UI
        │
        ▼
Phase 3: RAG-Kern (US-01 + US-02)
  T-17 Retrieval-Endpunkt
  T-18 LiteLLM-Integration
  T-19 Quellenreferenz-Validierung
  T-23 Konfidenz-Score
  T-25 Self-Check-Pipeline
  T-26 Unterdrückungslogik
  T-28 Eval-Test-Set (CI-Gate DoD-4)
  T-20 Frage-UI
  T-21 Quellenlink-Viewer
  T-22 Performance-Test (p95 ≤ 10s)
  T-27 Konfidenz-UI-Badges
        │
        ▼
Phase 4: Feedback (US-03)
  T-29–T-32
        │
        ▼
Phase 5: SHOULD
  T-33–T-36 Quiz (US-07+08)
  T-37–T-38 Admin-Konfiguration (US-11)
```

---

## Kritische Kette

```
T-01 → T-04 → T-06 → T-07 → T-10 → T-11 → T-12 → T-13 → T-17 → T-18 → T-19 → T-26 → T-28
                                                                          T-23 → T-25 ↗
T-04 → T-24 ↗
```

---

*Quellen: Docs/01_UserStories.md · Docs/05_C4-C2_Container.md · Docs/07_Definition-of-Done.md*
*Stand: 2026-06-10*
