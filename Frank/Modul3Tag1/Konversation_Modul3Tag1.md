# Konversation — ADAI Modul 3 Tag 1
**Datum:** 2026-05-27  
**Kontext:** Übungen Architektur mit AI — LearnFlow Projekt

---

## 1. DOCX → Markdown Konvertierung

**User:** wandel ADAI Modul3 Tag1 Uebungen.docx in eine md-Datei um

**Claude:** Konvertiert `ADAI Modul3 Tag1 Uebungen.docx` in `ADAI Modul3 Tag1 Uebungen.md` mittels PowerShell-XML-Parsing (pandoc nicht verfügbar). Besonderheiten:
- Tabellen als Markdown-Tabellen
- AI-Prompts als Code-Blöcke (` ``` `)
- Ausfüllfelder als fette Labels mit Leerzeilen
- Verschachtelte Referenztabellen (nested XML) korrekt extrahiert

---

## 2. Vorschlag für Ü1 Teil 1 — Quality Attributes identifizieren

**User:** @Modul3Tag1 Erstelle einen Vorschlag für Teil 1 · Quality Attributes identifizieren

**Claude:** Liest `LearnFlow_UserStories_v3.md`, `requirements_report_learnflow.md` und `ADR-001-Tech-Stack.md` und befüllt die QA-Tabelle sowie Top 3 und Massnahmen.

### Ausgefüllte QA-Tabelle (initialer Vorschlag)

| Quality Attribute | Konkretes Requirement | Warum wichtig |
|---|---|---|
| Performance | US-01: 10s @ p95; US-04: ≤5 Min Upload | RAG-Pipeline addiert Latenzen; Streaming nötig |
| Scalability | MVP: 1 Bereich, <30 Nutzer, pgvector-Ceiling | Stateless Design sichert Post-MVP-Pfad |
| Security | JWT + bcrypt, Azure OpenAI EU (GDPR), Admin-Rolle | Sensible Daten, GDPR-Pflicht |
| Reliability | US-01/US-02: Confidence-Threshold, Silence > Halluzination | Falscher Hinweis zerstört Vertrauen dauerhaft |
| Maintainability | US-11: Thresholds via Admin-UI, kein Neustart | Kleines Team, kurze Release-Zyklen |
| Testability | OpenAPI-Spec, LangChain isolierbar, US-03 Feedback | RAG-Qualität nicht statisch beweisbar |

**Top 3 (initial):** Reliability → Security → Maintainability

---

## 3. Korrektur: Reliability bezieht sich auf Verfügbarkeit

**User:** Reliability soll sich auf die Anwendung beziehen. Macht 97% Sinn?

**Claude:** Nein — wenn Reliability = Verfügbarkeit/Uptime (NFR), dann ist es für LearnFlow MVP der **schwächste** QA:
- Single-Instance Docker Compose, kein HA
- < 30 interne Nutzer, Business-Hours-Tool
- Kein Uptime-SLA definiert
- Fallback: Nutzer fragen Stefan direkt

Die "Antwortqualität" (Confidence-Threshold, kein Halluzinieren) ist eine **funktionale** Anforderung (US-01/US-02), kein QA.

**Neue Top 3:** Security → Maintainability → Performance

**User:** Ja *(Korrektur bestätigt)*

### Aktualisierte QA-Tabelle

| Quality Attribute | Konkretes Requirement | Warum wichtig |
|---|---|---|
| Reliability | Single-Instance Docker Compose, kein HA, Business-Hours | Bewusste Entscheidung gegen HA — akzeptables Risiko |

---

## 4. Korrektur: NFR-Sauberkeit bei Maintainability und Testability

**User:** Beziehen sich nun alle 6 Quality Attributes auf nicht-funktionale Anforderungen?

**Claude:** 4 von 6 sauber. Zwei gemischt:
- **Maintainability:** Referenz auf US-11 (FA) statt auf die Eigenschaft selbst
- **Testability:** Referenz auf US-03 (FA) statt auf Isolierbarkeit/Entkoppelung

**User:** Ja *(Bereinigung bestätigt)*

### Bereinigt
- **Maintainability:** *"Konfigurationsänderungen ohne Code-Deployment oder Neustart wirksam. Modularer Aufbau..."* (US-11 nur als Beleg in Klammern)
- **Testability:** *"Komponenten sind isoliert testbar — klare API-Boundary..."* (US-03 nur als Beleg in Klammern)

---

## 5. Korrektur: "Monika" existiert nicht als Persona

**User:** Bei Performance: Wer ist Monika?

**Claude:** Monika kommt nicht aus den Projektdokumenten — halluzinierter Name. Korrekte Personas laut User Stories: **Lara** (Lernende) und **Stefan** (Fachexperte). Korrigiert zu "Lara".

---

## 6. Audit-Logging: Security oder Maintainability?

**User:** Security: Wieso Änderungen auditieren? Wie hoch wäre der Aufwand dafür?

**Claude:**
- **Warum:** US-11 schreibt es explizit vor ("Changes logged with timestamp + actor"). Zweck: Traceability — nachvollziehen wer den Confidence-Threshold wann geändert hat, wenn das System plötzlich anders antwortet.
- **Aufwand:** Gering, ca. 2–4 Stunden. Eine `config_audit_log`-Tabelle (id, actor, field, old_value, new_value, timestamp) + Insert-Aufruf im Admin-Endpoint.
- **Einordnung:** Gehört zu **Maintainability** (Traceability), nicht Security.

**User:** Ja *(Verschiebung bestätigt)*

### Resultat
- **Security:** Nur noch JWT + bcrypt, rollenbasierte Zugriffskontrolle, Azure OpenAI EU (GDPR)
- **Maintainability:** +Config-Änderungen in `config_audit_log` geloggt (Timestamp + Actor)

---

## 7. Konsistenzprüfung Teil 2

**User:** Stimmen die Angaben für Teil 2 noch?

**Claude:** Ein Punkt inkonsistent — Zeile "Security-Massnahmen" enthielt noch das Audit-Logging. Korrigiert:
- Security-Massnahmen: Audit-Logging entfernt
- Maintainability-Massnahmen: Audit-Logging ergänzt

---

## Finaler Stand der QA-Tabelle

| Quality Attribute | Konkretes Requirement aus unserem Projekt | Warum wichtig für uns? |
|---|---|---|
| **Performance** | US-01: Max. 10s @ p95 für Q&A. US-04: Upload ≤5 Min (50 S./10 MB) | RAG-Pipeline addiert Latenzen; Streaming erforderlich — Auswirkung auf Nutzerakzeptanz bei Lara |
| **Scalability** | MVP: 1 Bereich, <30 Nutzer, pgvector-Ceiling ~1M Vektoren. Stateless FastAPI + Docker Compose | Kein MVP-Skalierungsdruck; stateless Design sichert Post-MVP-Pfad ohne Redesign |
| **Security** | JWT + bcrypt (DB-Script), Post-MVP Azure AD/SAML. Admin-Rolle für geschützte Funktionen. Azure OpenAI EU (GDPR) | Sensible Geschäftsdaten; GDPR-Pflicht im CH/EU Enterprise-Umfeld |
| **Reliability** | Single-Instance Docker Compose, kein HA. Business-Hours-Nutzung. Kein Uptime-SLA. Fallback: Stefan | Bewusste Entscheidung gegen HA — akzeptables Risiko bei <30 Nutzern |
| **Maintainability** | Thresholds + LLM-Modell ohne Code-Deployment änderbar. Config-Änderungen geloggt (Timestamp + Actor). Modularer Aufbau | Kleines Team (4 Devs, 320h) — Stefan muss Parameter ohne Dev-Eingriff tunen; Audit-Log für schnelles Debugging |
| **Testability** | Komponenten isoliert testbar (RAG-Pipeline, Frontend, DB entkoppelt). OpenAPI-Spec als Vertragstest-Basis | RAG-Qualität nicht statisch beweisbar; isolierbare Komponenten essentiell für 3-Monats-Entwicklung |

## Finaler Stand Top 3

1. **Security** — GDPR + sensible Daten; Azure OpenAI EU direkt daraus entstanden
2. **Maintainability** — 320h Budget; Business muss selbst konfigurieren können
3. **Performance** — Hartes Akzeptanzkriterium 10s @ p95 in US-01

## Finaler Stand Architektonische Massnahmen

| QA | Massnahme |
|---|---|
| Security | JWT (8h) + bcrypt; Admin-Middleware (rollenbasiert); Azure OpenAI EU |
| Maintainability | Admin-UI ohne Neustart; `config_audit_log` (Timestamp + Actor); LangChain-Abstraktion; Docker Compose |
| Performance | Async Streaming (FastAPI + SSE); pgvector HNSW-Index; asynchrones Dokument-Processing |
| Testability | OpenAPI-Spec als Vertragstest-Basis; US-03 Feedback als Produktions-Qualitätssignal |
| Reliability | Bewusst kein HA im MVP; Post-MVP: Monitoring + Health Checks |
