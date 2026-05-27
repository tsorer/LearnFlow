
| CAS Application Development with AI (ADAI) · 2026 Modul 3 · Tag 1  —  Übungen: Architektur mit AI | BFH Biel · Ilja Rasin |
| --- | --- |


Architektur mit AI — Drei Übungen
Heute wendet ihr Architektur-Konzepte direkt auf euer eigenes Projekt an. Jede Übung baut auf der vorherigen auf.

| Ü1 09:15–10:00 Quality Attributes Von Requirements zur Architektur | Ü2 10:15–11:00 ADR schreiben Eure erste Architektur-Entscheidung | Ü3 11:15–12:00 C4 Diagramme Context + Container für euer Projekt |
| --- | --- | --- |



| Ü1 | Quality Attributes für euer Projekt   ·   09:15 – 10:00 Welche nicht-funktionalen Anforderungen treiben eure Architektur? |
| --- | --- |


Quality Attributes (QA) sind nicht-funktionale Anforderungen — sie bestimmen WIE das System funktioniert, nicht WAS es tut. Sie sind die eigentlichen Architektur-Treiber.

**Die wichtigsten Quality Attributes — Kurzreferenz**


| QA | Was es bedeutet | Typische Architektur-Konsequenz |
| --- | --- | --- |
| Performance | Wie schnell antwortet das System? | Caching · CDN · Async Processing |
| Scalability | Wie viele gleichzeitige Nutzer? | Stateless Services · Load Balancer |
| Security | Wie schützen wir Daten? | Auth Service · Encryption · Audit Log |
| Reliability | Wie verfügbar ist das System? | Health Checks · Retry Logic · Monitoring |
| Maintainability | Wie einfach ist es zu ändern? | Modulare Struktur · Klare Boundaries |
| Testability | Wie gut ist es testbar? | Dependency Injection · Interfaces |


Teil 1 · Quality Attributes identifizieren (15 Min)
Schaut eure Requirements aus Modul 2 an. Welche QAs sind für euer Projekt relevant?

| Quality Attribute | Konkretes Requirement aus unserem Projekt | Warum wichtig für uns? |
| --- | --- | --- |
| Performance | US-01: Max. 10 s Antwortzeit @ p95 für Q&A-Anfragen. US-04: Dokument-Upload verarbeitungsbereit in ≤ 5 Min. (50 Seiten / 10 MB) | RAG-Pipeline (Embedding + Vector Search + LLM-Call) addiert Latenzen auf. Streaming (Token-by-Token) ist erforderlich, sonst wirkt das System träge — direkte Auswirkung auf Nutzerakzeptanz bei Lara |
| Scalability | MVP: 1 Pilot-Bereich (hardcoded), kleine interne Nutzergruppe (< 30). pgvector-Ceiling ~1 M Vektoren — für MVP akzeptabel. Stateless FastAPI + Docker Compose | Kein Skalierungsdruck im MVP; das stateless Design sichert aber den Post-MVP-Pfad (multi-Area, mehr Nutzer) ohne Redesign. Bewusste Entscheidung: jetzt nicht über-engineeren |
| Security | US-05: JWT + bcrypt (DB-Script), Post-MVP Azure AD / SAML SSO. US-11: Admin-Funktionen nur mit Admin-Rolle (rollenbasierte Zugriffskontrolle). Azure OpenAI EU: Daten verlassen die EU nicht (GDPR) | Interne Wissensbasis mit sensiblen Geschäftsdaten. Eine Datenpanne oder unberechtigter Zugriff ist nicht tolerierbar. GDPR-Compliance ist im Schweizer Enterprise-Umfeld Pflicht |
| Reliability | MVP: Single-Instance Docker Compose, kein HA-Setup. Business-Hours-Nutzung (interne Nutzer). Keine explizite Uptime-SLA definiert. Fallback: Nutzer wenden sich direkt an Stefan | Geringer Architektur-Treiber im MVP — bewusste Entscheidung gegen Hochverfügbarkeit. Akzeptables Risiko bei < 30 internen Nutzern und vorhandenem menschlichen Fallback |
| Maintainability | Konfigurationsänderungen (Thresholds, LLM-Modell) ohne Code-Deployment oder Neustart wirksam. Alle Config-Änderungen werden mit Timestamp + Actor geloggt (Traceability). Modularer Aufbau erlaubt Änderungen an einzelnen Komponenten ohne Seiteneffekte. (Belegt durch: US-11, ADR-001 LangChain-Abstraktion) | Kleines Team (4 Devs, 320 h) kann sich keine langen Release-Zyklen leisten. Audit-Log ermöglicht schnelles Debugging wenn das System nach einer Config-Änderung anders reagiert |
| Testability | Komponenten sind isoliert testbar — Backend (RAG-Pipeline), Frontend und Datenbank sind klar voneinander entkoppelt. API-Vertrag (OpenAPI-Spec) ist unabhängig von Implementierungsdetails prüfbar. (Belegt durch: ADR-001 OpenAPI-Boundary, US-03 als Produktions-Qualitätssignal) | RAG-Qualität lässt sich nicht rein statisch beweisen. Ohne isolierbare Komponenten und klare Boundaries sind Regressionstests in einer 3-Monats-Entwicklung nicht praktikabel |


Teil 2 · AI analysiert eure Quality Attributes (15 Min)
Prompt — fügt eure Requirements aus Modul 2 ein:

```
Hier sind unsere User Stories und Requirements: [EINFÜGEN]
Analysiere welche Quality Attributes für unser Projekt
am kritischsten sind.
Für die Top 3 QAs:
1. Warum ist dieser QA für unser Projekt besonders wichtig?
2. Welche konkreten architektonischen Massnahmen empfiehlst du?
3. Was passiert wenn wir diesen QA ignorieren?
Sei konkret — keine generischen Antworten.
Beziehe dich auf unser spezifisches Projekt.
```



**Top 3 QAs laut AI — und warum:**

1. **Security** — Interne Wissensbasis mit sensiblen Unternehmensdaten, GDPR-Pflicht (CH/EU), JWT jetzt + Azure AD/SAML Post-MVP. Die Entscheidung für Azure OpenAI EU ist direkt aus diesem QA entstanden.
2. **Maintainability** — 320 h Budget, 4 Personen, 3 Monate. Thresholds müssen vom Business (Stefan) konfigurierbar sein ohne Entwickler-Eingriff. LangChain-Abstraktion und externalisierte Konfiguration (US-11) sind direkte Konsequenz dieses QA.
3. **Performance** — US-01 definiert ein hartes Akzeptanzkriterium: 10 s @ p95. Die RAG-Pipeline (Embedding + Vector Search + LLM) addiert Latenzen — Streaming und pgvector-Indexierung sind direkte architektonische Antworten darauf.



**Architektonische Massnahmen die wir umsetzen werden:**

- **Security:** JWT (8 h) + bcrypt-Hashing; Admin-Middleware für rollenbasierte Zugriffskontrolle; Azure OpenAI EU (GDPR).
- **Maintainability:** Admin-UI für Threshold-Änderungen ohne Neustart; Config-Änderungen in `config_audit_log` geloggt (Timestamp + Actor); LangChain-Abstraktion für Modellwechsel via Config; Docker Compose für reproduzierbare Deployments.
- **Performance:** Async Streaming-Response (FastAPI + React EventSource/SSE); pgvector HNSW-Index für schnelle Similarity-Suche; Dokument-Processing asynchron (Upload sofort bestätigt, Verarbeitung im Hintergrund).
- **Testability:** OpenAPI-Spec als Vertragstest-Basis zwischen Backend und Frontend; US-03 Feedback-Capture als Produktions-Qualitätssignal.
- **Reliability:** Bewusst kein HA-Setup im MVP — Docker Compose Single Instance ist ausreichend. Post-MVP: Monitoring + Health Checks falls Nutzerzahl steigt.


Teil 3 · Teamdiskussion (10 Min)
Besprecht im Team:
- Stimmt ihr mit AI überein? Wo nicht — und warum?
- Welcher QA ist der schwierigste für euch technisch?
- Was würdet ihr an eurem Projekt ändern basierend auf dieser Analyse?


**Unser wichtigstes Takeout aus Übung 1:**

Security ist unser primärer Architektur-Treiber — sensible interne Daten und GDPR-Pflicht lassen keinen Spielraum. Maintainability und Performance folgen direkt aus Budget-Constraints (320 h) und dem harten 10s-SLA aus US-01. Reliability (Uptime) ist dagegen bewusst kein MVP-Treiber — bei < 30 internen Nutzern ist ein Single-Instance-Deployment ausreichend.



| Ü2 | Architecture Decision Record schreiben   ·   10:15 – 11:00 Eure wichtigste Technologie-Entscheidung dokumentieren. |
| --- | --- |


Ein ADR dokumentiert eine Architektur-Entscheidung — damit zukünftige Entwickler verstehen warum so gebaut wurde. Ihr schreibt heute euer erstes echtes ADR.

**ADR-Format nach Michael Nygard — Kurzreferenz**


| Feld | Was hineingehört | Beispiel |
| --- | --- | --- |
| Titel | Kurze beschreibende Überschrift | ADR-001: PostgreSQL statt MongoDB |
| Status | Aktueller Stand | Proposed · Accepted · Deprecated |
| Kontext | Warum müssen wir entscheiden? | ACID-Compliance nötig für Buchungen |
| Entscheidung | Was haben wir entschieden — aktiv | Wir verwenden PostgreSQL |
| Konsequenzen | Was wird besser / schwieriger? | + ACID ✓  − Kein horizontales Sharding |


Teil 1 · Eure wichtigste Entscheidung identifizieren (10 Min)
Welche Technologie-Entscheidung ist für euer Projekt am kritischsten? Typische ADR-Kandidaten:

| Datenbank PostgreSQL vs MongoDB
vs SQLite vs Supabase | API-Stil REST vs GraphQL
vs gRPC | Architektur Monolith vs Modularer Monolith
vs Microservices |
| --- | --- | --- |



**Unsere Entscheidung für den ADR:**




**Die Alternativen die wir abgewogen haben:**




Teil 2 · ADR mit Claude erstellen (20 Min)
Schritt 1 — ADR generieren lassen:

```
Erstelle ein ADR im Michael Nygard Format für folgende
Entscheidung in unserem Projekt:
Projekt: [EUER PROJEKTNAME + KURZE BESCHREIBUNG]
Entscheidung: Wir müssen wählen zwischen [OPTION A] und [OPTION B]
Kontext: [WARUM MÜSSEN WIR ENTSCHEIDEN?]
Team: 2-3 Devs, 3 Monate Zeit
Wichtigste Requirements: [TOP 3 QAs aus Übung 1]
Erstelle das vollständige ADR mit:
- Titel, Status: Proposed
- Kontext (3-4 Sätze)
- Entscheidung (aktiv formuliert)
- Konsequenzen (+ positiv, - negativ, mind. je 3)
```



**Unser ADR — zum Ausfüllen / Überarbeiten**


**ADR-Nummer und Titel:**



**Status:**



**Kontext — Warum müssen wir entscheiden?**





**Entscheidung — Was haben wir entschieden?**




| Positive Konsequenzen: | Negative Konsequenzen: |
| --- | --- |


**+**





**−**





Teil 3 · AI reviewt euer ADR (10 Min)

```
Reviewe dieses ADR kritisch:
[EUER FERTIGES ADR EINFÜGEN]
Fragen:
1. Was haben wir nicht bedacht?
2. Welche Alternativen fehlen in der Analyse?
3. Sind die Konsequenzen vollständig und realistisch?
4. Was wäre das grösste Risiko dieser Entscheidung?
```



**Was AI an unserem ADR verbessern würde:**






**Was wir am ADR ändern nach dem Review:**





> ⚠️  Ein ADR pro grosser Entscheidung — nicht für alles. Weniger ist mehr.




| Ü3 | C4 Diagramme — Context + Container   ·   11:15 – 12:00 Visualisiert eure Architektur auf zwei Ebenen. |
| --- | --- |


Das C4 Model beschreibt Architektur in vier Zoom-Ebenen — wie Google Maps. Heute macht ihr C1 und C2.

**C4 Model — Übersicht**


|  | Level | Was zeigt es? | Heute |
| --- | --- | --- | --- |
| C1 | System Context | Euer System + wer damit interagiert (Nutzer, externe Systeme) | ✅ Ja — in dieser Übung |
| C2 | Container | Was läuft wo? Web App, API, DB, Mobile App — jeder Container = eigener Prozess | ✅ Ja — in dieser Übung |
| C3 | Component | Was ist innerhalb eines Containers? Module, Klassen, Services | Modul 5 — Coding Phase |
| C4 | Code | UML-Diagramme, Klassen-Details — meistens zu viel Detail | Optional |


Teil 1 · C1 System Context Diagram (15 Min)
Das grosse Bild: Euer System als schwarze Box — wer interagiert damit von aussen?

```
Erstelle ein C4 System Context Diagram für unser Projekt.
Projektname: [EUER PROJEKTNAME]
Beschreibung: [KURZE BESCHREIBUNG]
Zeige:
- Unser System (als Hauptelement in der Mitte)
- Alle Nutzertypen die damit interagieren
- Alle externen Systeme (E-Mail, Payment, Auth, APIs...)
- Wie sie interagieren (kurze Beschriftung der Pfeile)
Beschreibe das Diagram als Text mit klaren Boxes und Pfeilen.
Dann: Was haben wir vergessen?
```



**C1 — System Context: [EUER PROJEKTNAME]**


**System-Name (Mitte):**



**Nutzertypen (wer interagiert?):**




**Externe Systeme (welche Abhängigkeiten?):**





**Überraschungen — was hat AI gefunden das wir vergessen hatten?**




Teil 2 · C2 Container Diagram (20 Min)
Jetzt zoomen wir rein: Was läuft technisch wo? Welche Technologien nutzt ihr?

```
Erstelle jetzt ein C4 Container Diagram für unser Projekt.
Basierend auf unseren Quality Attributes aus Übung 1:
[TOP 3 QAs EINFÜGEN]
Und unserer Systemübersicht aus C1:
[C1 ERGEBNIS EINFÜGEN]
Fragen:
1. Welche Container brauchen wir? (Web App, API, DB, Cache?)
2. Welche Technologien passen zu unserem Team und QAs?
3. Wie kommunizieren die Container miteinander?
4. Begründe jeden Container in einem Satz.
Unser Team: 2-3 Devs, 3 Monate, gemischter Background.
```



**C2 — Container Diagram: Unsere Technologie-Entscheidungen**


| Container | Technologie | Aufgabe | Kommuniziert mit |
| --- | --- | --- | --- |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |



**Was überrascht uns an der AI-Empfehlung?**





**Was ändern wir und warum?**




Teil 3 · Kurze Vorstellung im Plenum (5 Min pro Team)
Jedes Team zeigt in 5 Minuten:
- C1: Wer interagiert mit eurem System?
- C2: Welche Container — und welche Technologie für die wichtigste Entscheidung?
- Euer ADR aus Übung 2: Was habt ihr entschieden und warum?
- Eine Überraschung: Was hat AI gefunden das ihr nicht erwartet hattet?


**Ausblick: Was kommt in Tag 2 und Modul 4?**
Heute habt ihr Quality Attributes, ein ADR und erste C4-Diagramme für euer Projekt. Das ist die Basis für: Tag 2 — System Design Patterns: Monolith vs Microservices, API-First, Event-Driven Modul 4 — Planung: Eure Architektur wird zum Sprint-Plan Modul 5 — Coding: Claude Code arbeitet mit eurer C2/C3-Struktur Je präziser eure Architektur heute — desto klarer der Weg durch den Rest des Kurses.



CAS ADAI 2026 · BFH Biel · Modul 3 Tag 1 · Ilja Rasin
