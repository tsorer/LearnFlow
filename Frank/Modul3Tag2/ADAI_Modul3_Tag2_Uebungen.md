| **CAS Application Development with AI (ADAI) · 2026**<br>**Modul 3 · Tag 2  —  Übungen: Patterns & Architektur** | **BFH Biel · Ilja Rasin** |
| --- | --- |


**Patterns & Architektur — Drei Übungen**

**Heute wendet ihr Architektur-Patterns auf euer Projekt an — und trefft finale Entscheidungen.**

| **Ü1**<br>**09:15–10:00**<br>**Monolith vs. Microservices**<br>**Finale Entscheidung für euer Projekt** | **Ü2**<br>**10:15–11:00**<br>**API-First Design**<br>**OpenAPI Spec mit AI** | **Ü3**<br>**11:00–12:00**<br>**Patterns evaluieren**<br>**Event-Driven · CQRS · Strangler Fig** |
| --- | --- | --- |


| **Ü1** | **Monolith vs. Microservices**   ·   09:15 – 10:00<br>**Die wichtigste Architektur-Entscheidung — ehrlich betrachtet.** |
| --- | --- |


**Gestern habt ihr eine erste Entscheidung getroffen. Heute macht ihr sie final — mit echten Zahlen und ehrlicher Selbstreflexion.**

| **Entscheidungsrahmen — Was passt zu euch?** |
| --- |
| **Kriterium** — **Monolith** — **Modularer Monolith** — **Microservices**<br>**Team-Grösse** — **1-3 Devs** — **2-8 Devs** — **> 10 Devs**<br>**Zeitrahmen** — **< 6 Monate** — **6-18 Monate** — **> 18 Monate**<br>**Domain-Klarheit** — **Unbekannt** — **Teilweise klar** — **Sehr klar**<br>**Skalierungsbedarf** — **Niedrig** — **Mittel** — **Hoch**<br>**Deployment** — **Ein Mal** — **Pro Modul** — **Unabhängig**<br>**Debugging** — **Einfach** — **Mittel** — **Komplex**<br>**Netflix/Uber** — **❌ Nein** — **✅ Ja (Start)** — **✅ Heute** |


**Teil 1 · Selbstcheck (10 Min)**

**Füllt diese Tabelle für euer Projekt aus — ehrlich:**

| **Unser Projekt** | **Antwort** |
| --- | --- |
| **Team-Grösse** |  4 Entwickler|
| **Zeitrahmen bis MVP** | 8 Stunden x 8 Wochen (x 4 Entwickler) = 256h|
| **Kennen wir die Domain gut?** | nein |
| **Erwartete Nutzerzahl (Jahr 1)** | 10 |
| **Grösster Skalierungs-Treiber** | Benutzerzahl, Anzahl Dokumente |
| **Unser ADR-002 von gestern sagte:** | Wir bauen LearnFlow als **modularen Monolithen**: alle Module (RAG-Pipeline, Auth, Dokument-Management, Feedback, Admin) laufen in einem einzigen Deployment-Artefakt. Modul-Grenzen werden durch explizite Service-Interfaces durchgesetzt — kein direkter Datenbank-Aufruf über Modul-Grenzen hinweg, kein shared State. Das Design ist von Anfang an stateless, um einen späteren Ausbau zu ermöglichen. |

**Teil 2 · AI macht den Advocatus Diaboli (20 Min)**

**Gebt AI eure gestrige Entscheidung und lasst sie dagegen argumentieren:**

| Wir haben uns für [EUER PATTERN] entschieden.<br>Unser Kontext: [PROJEKTBESCHREIBUNG + TEAM + ZEITRAHMEN]<br>Spiele jetzt den Advocatus Diaboli:<br>1. Warum ist diese Entscheidung für uns FALSCH?<br>2. Was werden wir in 6 Monaten bereuen?<br>3. Welches Pattern wäre ehrlich gesagt besser — und warum?<br>4. Was müssen wir tun damit unsere Wahl wirklich funktioniert? |
| --- |


| **Die stärksten Gegenargumente von AI:** |
| --- |
| Nicht das „Monolith", sondern das „modular" ist die Lüge. Eure Modul-Grenzen sind Fiktion, weil alle Module dieselbe Datenbank teilen.  |
|  |
|  |


| **Ändert ihr eure Entscheidung — oder bleibt ihr dabei? Begründung:** |
| --- |
| Ja, Grundsatz stimmt. Ob man es nun 'Monolith', 'modularer Monolith' oder 'Majestic Monolith' ist Haarspalterei |
|  |


| ⚠️  Netflix, Uber und Amazon starteten als Monolithen. Microservices kamen erst bei echten Skalierungsproblemen. |
| --- |



| **Ü2** | **API-First Design**   ·   10:15 – 11:00<br>**API-Vertrag zuerst — dann implementieren.** |
| --- | --- |


**API-First bedeutet: Ihr definiert den Vertrag zwischen Frontend und Backend bevor eine Zeile Code geschrieben wird. Beide Seiten können dann parallel arbeiten.**

| **Was ist OpenAPI / Swagger?** |
| --- |
| **OpenAPI ist der Standard um REST APIs zu beschreiben — maschinenlesbar, menschenverständlich. Aus einer OpenAPI-Spec kann man automatisch generieren:**<br>**📄  Dokumentation**<br>**Swagger UI — interaktive API-Docs die jeder versteht** — **💻  Client-Code**<br>**TypeScript, Python, Java SDK — automatisch generiert** — **🧪  Mock-Server**<br>**Frontend kann testen bevor Backend fertig ist** |


**Teil 1 · Wichtigsten Endpoint identifizieren (10 Min)**

**Welcher API-Endpoint ist für euer Projekt am kritischsten? Der der am häufigsten aufgerufen wird oder am meisten Logik hat:**

| Hier ist unser Projekt: [BESCHREIBUNG]<br>Hier sind unsere Must-have User Stories: [EINFÜGEN]<br>Welche 5 API-Endpoints sind für unseren MVP am wichtigsten?<br>Für jeden Endpoint:<br>- HTTP Methode (GET/POST/PUT/DELETE)<br>- Path (/api/v1/...)<br>- Was macht er?<br>- Wer ruft ihn auf? |
| --- |


| **Method** | **Path** | **Aufrufer** | **Was macht er?** |
| --- | --- | --- | --- |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |


**Teil 2 · OpenAPI Spec für wichtigsten Endpoint (25 Min)**

**Wählt den wichtigsten Endpoint und lasst AI eine vollständige OpenAPI-Spec schreiben:**

| Schreibe eine OpenAPI 3.0 Spec für diesen Endpoint:<br>Endpoint: [EUER WICHTIGSTER ENDPOINT]<br>Projekt: [BESCHREIBUNG]<br>Inkludiere:<br>- Path, Method, Summary, Description<br>- Request Body mit Beispiel (JSON Schema)<br>- Response 200 mit Beispiel<br>- Response 400, 401, 404, 422 mit Fehlerbeschreibungen<br>- Security: Bearer Token<br>Format: YAML |
| --- |


| **Unsere OpenAPI Spec — zum Einfügen / Überarbeiten** |
| --- |
|  |


| **Was überrascht euch an der generierten Spec?** |
| --- |
|  |
|  |


| 💡  API-First Tipp: Speichert diese Spec in eurem Projekt-Repo als openapi.yaml. Sie wird eure Single Source of Truth für Frontend und Backend. |
| --- |



| **Ü3** | **Patterns evaluieren**   ·   11:00 – 12:00<br>**Event-Driven · CQRS · Strangler Fig — was braucht ihr wirklich?** |
| --- | --- |


**Drei Patterns — für jedes bewertet ihr ob es für euer Projekt sinnvoll ist. AI hilft euch die Konsequenzen verstehen.**

| **Pattern 1 · Event-Driven Architecture** |
| --- |
| **Was es ist:**<br>**Komponenten kommunizieren via Events statt direkter Aufrufe. BookingService ruft nicht EmailService.send() auf — er publiziert BookingCreated. EmailService abonniert das Event.**<br>**Wann sinnvoll:**<br>Async Prozesse: E-Mail, SMS, Push Notifications<br>Audit Log: alle Aktionen aufzeichnen<br>Entkopplung: Services sollen nichts voneinander wissen — **Wann NICHT:**<br>Kleines Team — viel Infrastruktur-Overhead<br>Einfache CRUD-Apps ohne Async-Bedarf<br>Wenn Debugging schon schwierig ist<br>**Für euer Projekt:**<br>Welche unserer User Stories würden von<br>Event-Driven profitieren?<br>Was wären die Events?<br>Lohnt sich der Aufwand für unser MVP?<br>**Unsere Bewertung: Brauchen wir Event-Driven? Welche Events — und wann?** |


| **Pattern 2 · CQRS — Command Query Responsibility Segregation** |
| --- |
| **Was es ist:**<br>**Schreib-Operationen (Commands) und Lese-Operationen (Queries) sind komplett getrennte Modelle. POST /bookings nutzt ein Write-Model, GET /bookings nutzt ein optimiertes Read-Model.**<br>**Wann sinnvoll:**<br>Lese- und Schreiblast sehr unterschiedlich<br>Komplexe Domain-Logik beim Schreiben<br>Verschiedene Darstellungen derselben Daten — **Ehrliche Einschätzung:**<br>**CQRS ist für die meisten MVPs Overkill. Es verdoppelt die Komplexität. Erst einsetzen wenn ihr echte Performance-Probleme habt — nicht vorbeugend.**<br>**Für euer Projekt:**<br>Habt ihr Endpoints die 100x häufiger<br>gelesen als geschrieben werden?<br>Braucht ihr CQRS jetzt — oder später?<br>**Unsere Bewertung: CQRS jetzt, später oder nie? Begründung:** |


| **Pattern 3 · Strangler Fig — Legacy-Migration ohne Big Bang** |
| --- |
| **Was es ist:**<br>**Statt das alte System komplett neu zu schreiben ('Big Bang Rewrite' — fast immer ein Misserfolg), baut man das neue System neben dem alten auf. Ein Proxy leitet Requests schrittweise um. Das alte System 'stirbt' organisch.**<br>**Die 3 Schritte:**<br>Proxy vor altes System stellen<br>Neuen Modul bauen → Proxy umleiten<br>Alten Modul abschalten wenn neu stabil — **Wann relevant für euch:**<br>**Relevant wenn ihr bei der Arbeit Legacy-Systeme habt oder euer Projekt irgendwann ein Legacy wird. Fast jede längerfristige Software-Arbeit kommt dazu.**<br>**Für euer Projekt:**<br>Gibt es Legacy-Systeme in eurem<br>beruflichen Kontext wo ihr dieses<br>Pattern anwenden könntet?<br>Was wäre der erste Schritt?<br>**Strangler Fig in unserem Arbeitskontext — wo und wie?** |


| **Pattern-Entscheidungsmatrix — euer finales Fazit** |
| --- |
| **Pattern** — **Für uns?** — **Wann?** — **Warum (nicht)?**<br>**Event-Driven**<br>**CQRS**<br>**Strangler Fig**<br>**API-First** |



**CAS ADAI 2026 · BFH Biel · Modul 3 Tag 2 · Ilja Rasin**


