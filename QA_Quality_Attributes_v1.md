# LearnFlow — Quality Attributes v1

*Basis: LearnFlow_Requirements_v1.md · Stand: 2026-05-27*

Diese Quality Attributes (QAs) definieren die nicht-funktionalen Anforderungen an LearnFlow. Sie dienen als Entscheidungsgrundlage für Architecture Decision Records (ADRs) und als Akzeptanzkriterien für den Pilotbetrieb.

---

## QA-01 · Performance

### Hintergrund
US-01 schreibt eine maximale Antwortzeit vor. Die RAG-Pipeline (Retrieval + LLM-Generierung) ist der kritische Pfad — beide Schritte können variieren und müssen gemeinsam das Ziel einhalten.

### Messbare Kriterien

| Szenario | Zielwert | Priorität |
|---|---|---|
| Ende-zu-Ende-Antwortzeit (Frage → Antwort mit Quellenverweis) | p95 ≤ 10 s | MUST (aus US-01) |
| Streaming-Beginn (erste Zeichen sichtbar) | ≤ 3 s nach Absenden | SHOULD |
| Dokument verfügbar nach Upload (≤ 50 Seiten / 10 MB) | ≤ 5 Minuten | MUST (aus US-04) |
| Seitenlade-Zeit (initiales Rendern, keine LLM-Anfrage) | ≤ 2 s | SHOULD |
| Quiz-Laden (5 Fragen aus bestehendem Pool) | ≤ 2 s | SHOULD |

### Massnahmen
- LLM-Streaming aktivieren, damit die Antwort progressiv erscheint (reduziert wahrgenommene Wartezeit)
- Embedding-Berechnung beim Dokument-Upload asynchron im Hintergrund (kein blockierender Upload-Request)
- Antwort-Timeouts server-seitig konfigurierbar; bei Überschreitung klare Fehlermeldung (kein Spinner ins Leere)

---

## QA-02 · Scalability

### Hintergrund
MVP ist ein Pilotbetrieb für einen einzigen Bereich. Die Nutzerzahl ist klein und bekannt. Die Architektur soll das Pilot-Volumen tragen, darf aber für Post-MVP-Skalierung nicht blind voroptimiert werden.

### Messbare Kriterien

| Szenario | Zielwert | Priorität |
|---|---|---|
| Gleichzeitige aktive Nutzer (Pilot-Betrieb) | 20 concurrent users ohne Degradation | MUST |
| Gleichzeitige LLM-Anfragen | ≤ 10 parallel (API-Quota-abhängig) | MUST |
| Dokument-Korpus (Pilot) | bis 500 Dokumente / ca. 5 GB Gesamtgrösse | SHOULD |
| Wachstum auf zweiten Bereich (Post-MVP) | Architektur muss erweiterbar sein — kein Hard-Coupling auf 1 Bereich | SHOULD |

### Massnahmen
- Anfrage-Queue oder Rate-Limiter vor LLM-Calls (verhindert API-Quota-Überschreitung)
- Bereichs-ID als First-Class-Konzept in Datenmodell und API, auch wenn im MVP nur ein Wert vorkommt
- Kein In-Memory-Zustand pro Server-Instanz (ermöglicht spätere horizontale Skalierung ohne Refactoring)

---

## QA-03 · Security

### Hintergrund
Interne Unternehmensdokumente dürfen nur autorisierten Mitarbeitenden zugänglich sein. Es gibt keine Self-Service-Registrierung. Post-MVP ist SSO geplant — die Architektur muss diesen Wechsel vorbereiten.

### Messbare Kriterien

| Szenario | Zielwert | Priorität |
|---|---|---|
| Zugriff ohne gültigen Session-Token | 100 % der Requests auf Login weitergeleitet | MUST (aus US-05) |
| Zugriff auf Admin-Seite ohne Admin-Rolle | HTTP 403, kein Inhalt sichtbar | MUST (aus US-11) |
| Zugriff auf Dokumente eines anderen Bereichs | HTTP 403 | MUST (aus US-04) |
| Passwort-Speicherung | Bcrypt oder Argon2 (kein Plaintext, kein MD5/SHA1) | MUST |
| Session-Token | HTTP-only Cookie oder kurzlebiges JWT (≤ 1 h) + Refresh-Token | MUST |
| Konfigurationsänderungen | Audit-Log mit Zeitstempel + ausführender Person | MUST (aus US-11) |
| LLM-API-Key | Niemals im Frontend oder Logs sichtbar | MUST |
| Feedback-Daten | Pseudonymisiert gespeichert — kein direkter User-FK | MUST (aus US-03) |
| Transport-Verschlüsselung | TLS 1.2+ für alle HTTP-Verbindungen | MUST |
| SSO-Readiness | Auth-Layer hinter Interface, das gegen SAML 2.0 / OIDC austauschbar ist | SHOULD |

### Massnahmen
- RBAC server-seitig erzwungen — kein Trust in Client-Assertions
- Separate Auth-Schicht (Middleware / Service), die für SSO-Anbindung ausgetauscht werden kann, ohne Business-Logik zu ändern
- Keine Query-Inhalte in Server-Logs (verhindert versehentliche Leakage vertraulicher Fragen)

---

## QA-04 · Reliability

### Hintergrund
LearnFlow ist ein internes Tool im Pilotbetrieb — kein 24/7-Produktivsystem. Kritisch ist jedoch, dass Fehler transparent kommuniziert werden: keine halluzinierten Antworten bei LLM-Ausfall (US-01), keine stummen Fehler.

### Messbare Kriterien

| Szenario | Zielwert | Priorität |
|---|---|---|
| Uptime (Geschäftszeiten Mo–Fr, 07:00–19:00) | ≥ 95 % | MUST |
| Uptime (ausserhalb Geschäftszeiten) | Best-effort, kein SLA | — |
| LLM-Service nicht erreichbar | Klare Fehlermeldung ≤ 5 s; keine erfundene Antwort | MUST (aus US-01) |
| LLM-Timeout (einzelner Call) | Retry 1×, dann Fehler — kein unbegrenztes Warten | MUST |
| Konfigurationsänderungen (Schwellenwerte) | Wirken sofort ohne Applikations-Neustart | MUST (aus US-11) |
| Health-Check-Endpoint | `/health` antwortet mit Status aller Abhängigkeiten (DB, LLM-API, Vektor-DB) | SHOULD |
| Fehler-Monitoring | Unerwartete Exceptions werden zentral erfasst (z. B. Sentry o. ä.) | SHOULD |
| Dokument-Processing-Fehler | Fehlgeschlagene Verarbeitung wird Stefan im Dashboard angezeigt | SHOULD |

### Massnahmen
- Circuit-Breaker vor LLM-API: nach N konsekutiven Fehlern direkt „Service nicht verfügbar" zurückgeben
- Konfigurationsparameter aus DB laden (nicht aus ENV/Config-File), damit Änderungen ohne Restart wirken
- Asynchrone Dokument-Verarbeitung mit explizitem Status (pending / processing / ready / failed)

---

## QA-05 · Maintainability

### Hintergrund
Das Team besteht aus 4 Personen mit je 1 Tag/Woche — effektiv 1 FTE. Maintenance-Aufwand muss minimal sein. Gleichzeitig sind Post-MVP-Erweiterungen absehbar (SSO, Multi-Bereich, DSGVO-Workflow).

### Messbare Kriterien

| Szenario | Zielwert | Priorität |
|---|---|---|
| Maintenance-Team-Grösse | 1 Person Teilzeit (0,2 FTE) für Betrieb und kleinere Anpassungen | MUST |
| Onboarding neuer Entwickler | Lokale Entwicklungsumgebung per README in ≤ 30 Minuten lauffähig | SHOULD |
| Konfidenz-/Stale-Schwellenwerte ändern | Kein Code-Deployment erforderlich | MUST (aus US-02, US-06) |
| LLM-Provider wechseln | Nur 1 Adapter-Klasse/-Modul ändern, keine Auswirkung auf Business-Logik | SHOULD |
| Neuen Bereich hinzufügen (Post-MVP) | Konfiguration + DB-Eintrag, kein strukturelles Refactoring | SHOULD |

### Modulare Struktur (Empfehlung)

```
┌─────────────────────────────────────┐
│           Frontend (UI)             │  React / Next.js o.ä.
└──────────────┬──────────────────────┘
               │ REST / GraphQL
┌──────────────▼──────────────────────┐
│         API / Application Layer     │  Routing, Auth-Middleware, Input-Validierung
└──────────┬───────────┬──────────────┘
           │           │
┌──────────▼──┐  ┌─────▼────────────┐
│  RAG Engine  │  │  Corpus Manager  │  Klar getrennte Domänen
│  (Retrieval  │  │  (Upload, Chunk, │
│  + LLM-Call) │  │  Index, Stale)   │
└──────────┬───┘  └─────┬────────────┘
           │             │
┌──────────▼─────────────▼────────────┐
│     Persistence Layer               │  DB (Postgres), Vektor-DB, File Storage
└─────────────────────────────────────┘
     ↕ (Interface)
┌─────────────────────────────────────┐
│     LLM Adapter (austauschbar)      │  Claude / OpenAI / Azure OAI
└─────────────────────────────────────┘
```

**Boundaries:**
- RAG Engine kennt keine Upload-Logik; Corpus Manager kennt keine Prompt-Konstruktion
- Auth-Logik nur in API-Layer, nicht in Business-Logik gestreut
- Konfigurationsparameter nur über einen zentralen Config-Service gelesen (kein direkter DB-Zugriff aus Business-Logik)

---

## QA-06 · Testability

### Hintergrund
Risiko 1 (RAG-Qualität) und Risiko 2 (Konfidenz-Scoring) erfordern systematische Evaluierbarkeit. Das kleine Team braucht automatisierte Sicherheitsnetze, um Regressionen ohne manuellen Aufwand zu erkennen.

### Messbare Kriterien

| Szenario | Zielwert | Priorität |
|---|---|---|
| Out-of-Corpus-Testfragen: „Weiss ich nicht"-Rate | ≥ 90 % | MUST (aus US-02) |
| CI-Pipeline bei jedem Push | Unit- und Integrationstests automatisch ausgeführt | MUST |
| RAG-Evaluierungs-Dataset | Vor Sprint 1 definiert (Go/No-Go-Grundlage für Risiko 1) | MUST |
| LLM-Abhängigkeit in Unit-Tests | LLM via Interface mockbar — kein echter API-Call in Unit-Tests | MUST |
| Konfidenz-Scoring isoliert testbar | Score-Logik ohne RAG-Pipeline aufrufbar | SHOULD |
| Testabdeckung kritischer Pfade | US-01, US-02, US-05 (Auth): ≥ 80 % Line Coverage | SHOULD |
| End-to-End-Test kritischer Flows | Login → Frage stellen → Quellenlink öffnen (automatisiert) | SHOULD |

### Massnahmen
- **Dependency Injection** für LLM-Adapter, Vektor-DB-Client und E-Mail-Service — alle als Interfaces definiert
- **RAG-Evaluierungs-Harness**: separates Script, das Testfragen gegen den Korpus schickt und Konfidenzwerte, Quellentreffer und „Weiss ich nicht"-Rate protokolliert
- **Contract Tests** für LLM-Adapter-Interface: bei Provider-Wechsel sofort sichtbar, wenn Antwort-Format abweicht
- Keine Tests gegen Produktions-DB; separate Test-Datenbank in CI

---

## Zusammenfassung: Nicht verhandelbare QAs (MUST)

| QA | Kriterium | Herkunft |
|---|---|---|
| Performance | p95 Antwortzeit ≤ 10 s | US-01 |
| Performance | Dokument nach Upload ≤ 5 min verfügbar | US-04 |
| Security | Unauthentifizierter Zugriff → Redirect zu Login | US-05 |
| Security | Admin-Seite ohne Admin-Rolle → HTTP 403 | US-11 |
| Security | Passwörter gehasht (Bcrypt / Argon2) | implizit |
| Security | Feedback pseudonymisiert | US-03 |
| Reliability | LLM-Fehler → Klare Meldung, keine erfundene Antwort | US-01 |
| Reliability | Schwellenwert-Änderung ohne Neustart wirksam | US-11 |
| Maintainability | Schwellenwerte ohne Code-Deployment änderbar | US-02, US-06 |
| Testability | Out-of-Corpus-Rate ≥ 90 % „Weiss ich nicht" | US-02 |
| Testability | LLM mockbar in Unit-Tests | Risiko 1+2 |

---

*Nächster Schritt: ADRs für die kritischsten Architekturentscheidungen — empfohlen: LLM-Provider-Wahl, RAG-Stack (Vektor-DB + Embedding), Auth-Strategie, Konfidenz-Scoring-Mechanismus*
