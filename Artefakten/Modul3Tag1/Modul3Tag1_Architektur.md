
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

> **Hinweis NFA vs. FA:** Quality Attributes sind nicht-funktionale Anforderungen — sie beschreiben WIE das System sein muss, nicht WAS es tut. In der Requirements-Spalte stehen daher messbare Qualitätskriterien (NFAs). US-Nummern dienen als Quellenangabe, sind aber selbst funktionale Anforderungen (FAs) und keine QA-Treiber.

| Quality Attribute | Nicht-funktionale Anforderung (NFA) — messbar & beobachtbar | Warum wichtig für uns? |
| --- | --- | --- |
| Performance | **Antwortzeit ≤ 10 s am 95. Perzentil** unter Normallast · Dokument nach Upload innerhalb von **≤ 5 Minuten** als Quelle verfügbar · Antwort-Streaming (Token-by-Token) erforderlich, da batch-Response träge wirkt *(abgeleitet aus FA: US-01, US-04)* | RAG-Pipeline (Retrieval + Embedding + LLM-Generierung) addiert Latenzen inhärent. Überschreitet die Wartezeit die Schwelle, bricht Lara ab und fragt wieder bei Stefan nach — das Kernversprechen entfällt. |
| Scalability | **Maximale Gleichzeitigkeit im MVP: < 30 Nutzer**, 1 Pilot-Bereich hartcodiert · Architektur muss Multi-Bereich-Ausbau ermöglichen **ohne Redesign** (stateless Services, kein shared State) *(MVP-Constraint; Post-MVP Out of Scope)* | Kein Skalierungsdruck heute — aber eine zustandsbehaftete Architektur würde den Post-MVP-Ausbau auf mehrere Bereiche zu einem vollständigen Umbau machen. |
| Security | **Kein Systemzugriff ohne gültige Authentifizierung** · Jede Ressource erfordert rollenbasierte Autorisierung (Lernende / Bereichsverantwortlicher / Admin) · **Personenbezogene Daten verlassen die EU nicht** (DSGVO) · Feedback und Query-Logs werden pseudonymisiert gespeichert · Cluster < 5 Fragen werden nicht angezeigt (Re-Identifikationsschutz) · Auth-Basis SSO-nachrüstbar ohne Umbau *(abgeleitet aus FA: US-05, US-11, US-03, US-10)* | Interne Unternehmensdokumente und Fachprozesse sind schützenswert. DSGVO-Compliance ist im Schweizer Enterprise-Umfeld nicht verhandelbar. Eine einmalige Datenpanne beendet den Piloten. |
| Reliability | **Halluzinationsrate = 0 %**: Das System darf niemals eine Antwort ohne valide, belegbare Quellenreferenz ausgeben · Ausfall des LLM-Service darf **nie** zu einer generierten Fallback-Antwort führen — kontrollierte Degradation (Fehlermeldung) ist Pflicht · Out-of-Corpus-Erkennungsrate: ≥ 90 % „Weiss ich nicht" *(messbare Schwelle; abgeleitet aus FA: US-01, US-02; Risiko 3)* · **MVP bewusst: kein HA-Setup**, Single-Instance, Business-Hours-Nutzung *(Kontroverse: → Teil 2)* | Eine halluzinierte Antwort mit echter Quellenangabe ist unsichtbar — Lara merkt es nicht, handelt falsch, verliert Vertrauen erst Wochen später. Das ist existenziell für den Pilot, unabhängig von der Nutzerzahl. |
| Maintainability | **Alle Konfigurationsparameter** (Konfidenz-Schwellenwert, Stale-Schwellenwert, Cluster-Mindestgrösse) müssen **ohne Code-Deployment und ohne Systemstart** geändert werden können · **LLM-Provider wechselbar durch Konfiguration** — kein Code-Change (LiteLLM-Abstraktion) · Jede RAG-Komponente austauschbar ohne Seiteneffekte auf andere Module *(abgeleitet aus FA: US-02, US-06, US-11)* | 320–480 h Gesamtbudget. Jede Stunde für operative Anpassungen fehlt bei der Kernentwicklung. Provider-Wechsel (Cloud vs. OnPrem) muss ohne Entwickler-Eingriff möglich sein — sonst ist es ein Vertriebshindernis. |
| Testability | **Out-of-Corpus-Erkennungsrate ≥ 90 %** „Weiss ich nicht" als messbares Akzeptanzkriterium · **Halluzinationsrate messbar und regressionsfähig** bevor die Implementierung startet (Tech Spike als Go/No-Go) · Jede RAG-Komponente (Chunking, Embedding, Retrieval, Generierung) **einzeln isolierbar und testbar** · Konfidenz-Scoring-Mechanismus muss formal definiert sein, bevor er testbar ist *(abgeleitet aus: Risiko 1, Risiko 2, FA: US-02)* | RAG-Qualität ist ein empirisches Phänomen — nicht durch Code-Review validierbar. Ohne Testability weiss das Team nie, ob Reliability (Halluzinationsrate = 0 %) tatsächlich erreicht ist. |


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


**Ranking der drei Teammitglieder im Vergleich:**

| Rang | Frank | Nicklaus | Reto |
| --- | --- | --- | --- |
| 1 | Security | Reliability | Reliability |
| 2 | Maintainability | Testability | Security |
| 3 | Performance | Maintainability | Performance |

> **Reflexion: FA vs. NFA im Ranking**
> Frank, Nicklaus und Reto haben ursprünglich grösstenteils **funktionale Anforderungen** (User Stories US-xx) als Belege genannt — diese beschreiben WAS das System tut, nicht WIE gut. Bei der Neubewertung mit NFA-Brille (messbare Qualitätskriterien) verschiebt sich die Gewichtung: **Reliability** hat mit „Halluzinationsrate = 0 %" die härteste, existenziellste NFA des Projekts. **Security** hat mit der DSGVO-Pflicht eine nicht verhandelbare regulatorische NFA. **Performance** hat mit ≤ 10 s @ p95 eine klar messbare NFA. Franks ursprünglicher Reliability-Downgrade war auf eine FA-Perspektive gestützt (Uptime / HA-Setup) — unter NFA-Sicht bleibt die Korrektheitspflicht unabhängig von der Nutzerzahl bestehen.


**Top 3 QAs laut AI — NFA-gewichtet:**

1. **Reliability** *(NFA: Halluzinationsrate = 0 %, Out-of-Corpus ≥ 90 % „Weiss ich nicht")* — Die stärkste und existenziellste NFA des Projekts. Eine halluzinierte Antwort mit echter Quellenangabe ist unsichtbar und nicht reparierbar — Lara merkt es nicht, handelt falsch, das Vertrauen bricht. Diese NFA hängt nicht an der Nutzerzahl; sie gilt für den ersten Nutzer wie für den tausendsten. Das ist der Unterschied zu Uptime-Reliability (HA-Setup), die Frank bewusst zurückgestellt hat.
2. **Security** *(NFA: Kein unbefugter Zugriff; DSGVO — personenbezogene Daten verlassen die EU nicht)* — Regulatorische NFAs sind nicht verhandelbar. DSGVO-Verstoss ist kein technisches Risiko, sondern ein rechtliches. Interne Unternehmensdokumente im Korpus machen unbefugten Zugriff zu einem Business-Stopper. Die NFA „kein Zugriff ohne Authentifizierung und Autorisierung" ist binär — entweder erfüllt oder nicht.
3. **Maintainability** *(NFA: Konfigurationsparameter änderbar ohne Code-Deployment; LLM-Provider wechselbar ohne Code-Change)* — Die stärkste Budget-getriebene NFA. 320–480 h Gesamtbudget bedeutet: jede operative Stunde fehlt in der Entwicklung. Die NFA ist eindeutig messbar: Kann Stefan den Konfidenz-Schwellenwert ändern, ohne einen Entwickler zu rufen? Kann der LLM-Provider per Konfigurationseintrag gewechselt werden?


**Architektonische Massnahmen die wir umsetzen werden:**

- **Reliability:** Mehrschichtiger Unterdrückungsmechanismus (Quellenprüfung → Konfidenz-Score → Self-Check-Anteil). Circuit Breaker für LLM-Aufrufe (Timeout, HTTP 5xx, Quota). Fail-Safe als Designprinzip: „keine Antwort" ist immer besser als eine unsichere Antwort. Konfidenz-Schwellenwerte in der DB, nicht im Code — empirisch kalibrierbar nach Tech Spike.
- **Security:** JWT (8 h) + bcrypt-Hashing; Admin-Middleware für rollenbasierte Zugriffskontrolle; URL-Zugriff ohne Admin-Rolle wird serverseitig abgewiesen; OpenAI API (GDPR). Auth-Schicht so bauen, dass SSO später ohne Umbau nachrüstbar ist.
- **Maintainability:** Admin-UI für Threshold-Änderungen ohne Neustart; LiteLLM-Abstraktion für Modellwechsel via Config; Docker Compose für reproduzierbare Deployments; klare Modul-Grenzen ohne Ripple-Effects.
- **Performance:** Async Streaming-Response (FastAPI + React EventSource/SSE); pgvector HNSW-Index für schnelle Similarity-Suche; Dokument-Processing asynchron (Upload sofort bestätigt, Verarbeitung im Hintergrund). 10-Sek.-Limit als festes Akzeptanzkriterium in CI/CD-Tests verankern.
- **Testability:** Evaluationsdataset vor Sprint 1 (echte Dokumente, In-Corpus + Out-of-Corpus Fragen, erwartete Antworten). Automatisiertes Scoring im CI. LiteLLM ermöglicht A/B-Tests zwischen Providern mit identischer RAG-Pipeline.
- **Reliability (MVP-Entscheid):** Bewusst kein HA-Setup — Docker Compose Single Instance ist ausreichend für < 30 interne Nutzer. Post-MVP: Monitoring + Health Checks falls Nutzerzahl steigt.


Teil 3 · Teamdiskussion (10 Min)
Besprecht im Team:
- Stimmt ihr mit AI überein? Wo nicht — und warum?
- Welcher QA ist der schwierigste für euch technisch?
- Was würdet ihr an eurem Projekt ändern basierend auf dieser Analyse?


**Unser wichtigstes Takeout aus Übung 1:**

Reliability und Security sind die primären Architektur-Treiber — sensible interne Daten, GDPR-Pflicht und das Kernversprechen „quellenbelegte Antworten ohne Halluzinationen" lassen keinen Spielraum. Maintainability folgt direkt aus dem Budget-Constraint (320–480 h, 1 Tag/Woche). Performance ist ein hartes Akzeptanzkriterium (10 s @ p95), aber technisch lösbar. Die grösste Team-Diskussion: Ob Reliability ein MVP-Treiber ist (Nicklaus/Reto: ja, weil eine einzige falsche Antwort den Pilot kippt) oder bewusst zurückgestellt werden kann (Frank: Single-Instance für < 30 Nutzer akzeptabel).



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

**ADR-001 — Tech-Stack:** Modularer Monolith mit Python/FastAPI + React (TypeScript) + PostgreSQL + pgvector + LiteLLM (OpenAI API) + Docker Compose

**Die Alternativen die wir abgewogen haben:**

| Option A | Option B | Option C |
|---|---|---|
| Modularer Monolith (gewählt) | Microservices | Node.js / Next.js Fullstack |




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

> ADRs aufgeteilt nach Review: [ADR-001](ADR-001_Architekturstil.md) · [ADR-002](ADR-002_Backend-Frontend-Stack.md) · [ADR-003](ADR-003_Datenpersistenz.md) · [ADR-004](ADR-004_LLM-Provider.md) · [ADR-005](ADR-005_Embedding-Modell.md)

**ADR-Nummer und Titel:**

ADR-001 · Tech-Stack — Modularer Monolith mit FastAPI, React und PostgreSQL + pgvector

**Status:**

Proposed

**Kontext — Warum müssen wir entscheiden?**

LearnFlow ist eine RAG-Plattform für < 30 Nutzer, 1 Pilot-Bereich, 360 h Gesamtbudget. Die Top-3-QAs (Reliability, Security, Maintainability) verlangen eine klar modulare, aber deploymentarme Architektur. Stack muss in Woche 1 fixiert sein — ein späterer Umbau ist bei diesem Budget nicht möglich.

**Entscheidung — Was haben wir entschieden?**

Wir bauen einen modularen Monolithen: Python/FastAPI (Backend) + React/TypeScript (Frontend) + PostgreSQL + pgvector (Datenbank + Vektor-Suche) + LiteLLM/OpenAI API (LLM) + Docker Compose (Deployment).

| Positive Konsequenzen: | Negative Konsequenzen: |
| --- | --- |
| + Python KI/ML-Ökosystem direkt verfügbar (LangChain, LiteLLM) | − Single Instance: kein Failover bei Ausfall (akzeptiert für Pilot) |
| + Ein PostgreSQL-Server statt separater Vector-DB — minimaler Ops-Aufwand | − pgvector skaliert nicht auf Milliarden Vektoren (kein Problem für < 5 000 Chunks) |
| + LiteLLM ermöglicht Provider-Wechsel via Config — Maintainability-NFA erfüllt | − Azure OpenAI Quota-Genehmigung kann Wochen dauern — Risiko 3 |
| + Docker Compose auf jedem Dev-Laptop reproduzierbar | − GIL-Engpass bei parallelen Embeddings (Mitigation: Background Workers) |
| + FastAPI + React im Team bekannt — keine Lernkurve | − Monolith schwerer in Microservices aufzuteilen (Mitigation: Stateless-Design) |


**+**

Vollständige Positivliste → [ADR-001_Tech-Stack.md](ADR-001_Tech-Stack.md)


**−**

Vollständige Negativliste → [ADR-001_Tech-Stack.md](ADR-001_Tech-Stack.md)




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



**C1 — System Context: LearnFlow**

> Vollständiges Diagram: [C4_C1_System-Context.md](C4_C1_System-Context.md)

**System-Name (Mitte):**

LearnFlow — Interne RAG-Lernplattform. Quellenbelegte KI-Antworten aus kuratiertem Wissenskorpus. Ein Pilot-Bereich, Web-App.

**Nutzertypen (wer interagiert?):**

| Person | Rolle | Interaktion |
|---|---|---|
| Lara | Lernende / Junior Developer | Frage stellen, Antwort lesen, Feedback geben, Quiz absolvieren |
| Stefan | Bereichsverantwortlicher / Knowledge Owner | Dokumente hochladen, Quiz freigeben, Stale-Inhalte validieren |
| Admin | Technisch verantwortlich | Konfidenz- und Stale-Schwellenwerte konfigurieren |

**Externe Systeme (welche Abhängigkeiten?):**

| System | Zweck | Status |
|---|---|---|
| OpenAI API | LLM (gpt-4o-mini) + Embeddings (text-embedding-3-small) via LiteLLM | MVP |
| Unternehmens-IdP (Azure AD / SAML 2.0) | SSO-Authentifizierung + Rollen-Synchronisation | Post-MVP |

**Überraschungen — was hat AI gefunden das wir vergessen hatten?**

1. **Kein Monitoring / Alerting** — Für Reliability-NFA (Halluzinationsrate messbar) braucht es Observability. Kein externer Service definiert; strukturiertes Container-Logging als Pilot-Lösung.
2. **Ollama im Entwicklungs-Kontext** — Im Produktions-C1 korrekt nicht gezeigt; im Dev-Systemkontext wäre Ollama ein zusätzlicher Knoten.


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
