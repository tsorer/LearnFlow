| **CAS Application Development with AI (ADAI) · 2026**<br>**Modul 3 · Tag 2  —  Lab 6: Architecture Finalisierung & Pitch** | **BFH Biel · Ilja Rasin** |
| --- | --- |


**Lab 6 · Architecture Finalisierung & Pitch**

**Heute schliesst ihr Modul 3 ab — mit einem vollständigen Architecture Draft und einem 5-minütigen Pitch vor der Gruppe.**

| **Was ihr heute abliefert — Deliverables** |
| --- |
| **1** — **Finales C2 Container Diagram** — **Alle Container, Technologien, Kommunikation — begründet**<br>**2** — **ADR-001 (Technologie)** — **Erste Architektur-Entscheidung — finalisiert**<br>**3** — **ADR-002 (Pattern)** — **Monolith / Modularer Monolith / Microservices — final**<br>**4** — **Pattern-Entscheidungsmatrix** — **Event-Driven / CQRS / API-First — was wann und warum**<br>**5** — **OpenAPI Spec (1 Endpoint)** — **Wichtigster Endpoint vollständig beschrieben**<br>**6** — **Architecture Pitch** — **5 Min vor der Gruppe — Entscheidungen verteidigen** |


| **L1**<br>**13:00–13:45**<br>**AI-Review** | **L2**<br>**13:45–14:30**<br>**Draft finalisieren** | **–**<br>**14:30–14:45**<br>**Pause** | **L3**<br>**14:45–15:15**<br>**Pitch vorbereiten** | **L4**<br>**15:15–16:15**<br>**Architecture Pitch** |
| --- | --- | --- | --- | --- |


| **L1** | **AI-Review des Architecture Drafts**   ·   13:00 – 13:45<br>**Lasst AI euren Draft systematisch analysieren — bevor ihr finalisiert.** |
| --- | --- |


**Bevor ihr finalisiert — lasst AI vier kritische Fragen an euren Draft stellen. Das deckt Schwachstellen auf die ihr übersehen habt.**

**Review 1 · Konsistenz-Check (10 Min)**

| Hier ist unser Architecture Draft:<br>- C2 Container Diagram: [EINFÜGEN]<br>- ADR-001: [EINFÜGEN]<br>- ADR-002: [EINFÜGEN]<br>- Pattern-Entscheidungen: [EINFÜGEN]<br>Prüfe auf Konsistenz:<br>1. Stimmen ADRs mit dem C2-Diagram überein?<br>2. Gibt es Widersprüche zwischen den Entscheidungen?<br>3. Passen die gewählten Patterns zu unserem Team (2-3 Devs, 3 Monate)?<br>4. Was passt zusammen — was beisst sich? |
| --- |


| **Gefundene Widersprüche oder Inkonsistenzen:** |
| --- |
|  |
|  |
|  |


**Review 2 · Skalierungs- und Security-Check (10 Min)**

| Analysiere unsere Architektur auf zwei Dimensionen:<br>Dimension 1 — Skalierung:<br>- Was bricht als erstes bei 10x mehr Usern?<br>- Wo ist unser Bottleneck?<br>- Was müssten wir ändern für 100x?<br>Dimension 2 — Security:<br>- Wo sind die grössten Angriffsflächen?<br>- Welche OWASP Top-10 Risiken betreffen uns?<br>- Was fehlt in unserer Architektur für GDPR-Compliance? |
| --- |


| **Skalierungs-Bottleneck:** |
| --- |
|  |
|  |


| **Grösste Security-Lücken:** |
| --- |
|  |
|  |


**Review 3 · Reality-Check (10 Min)**

| Sei radikal ehrlich:<br>Gegeben: unser Team (2-3 Devs, 3 Monate, gemischter Background).<br>1. Welche Teile unserer Architektur sind zu komplex für uns?<br>2. Was würde ein Senior-Entwickler sofort vereinfachen?<br>3. Was sollten wir aus dem MVP streichen damit es realistisch wird?<br>4. Ist unser Architecture Draft ehrlich — oder Wunschdenken? |
| --- |


| **Was wir vereinfachen oder streichen:** |
| --- |
|  |
|  |
|  |


| ⚠️  Ein vereinfachter Draft der wirklich gebaut werden kann ist besser als ein perfekter Draft der scheitert. |
| --- |



| **L2** | **Architecture Draft finalisieren**   ·   13:45 – 14:30<br>**Alle Erkenntnisse einarbeiten — euer finales Dokument.** |
| --- | --- |


**Jetzt arbeitet ihr alle Erkenntnisse aus dem Review ein und erstellt den finalen Architecture Draft.**

**Schritt 1 · C2 Diagram finalisieren (15 Min)**

| Basierend auf unserem Review — aktualisiere unser C2 Diagram:<br>Änderungen die wir einarbeiten wollen: [LISTE DER ÄNDERUNGEN]<br>Erstelle das finale C2 mit:<br>- Allen Containern (Name, Technologie, Kurzbeschreibung)<br>- Kommunikationspfeilen (sync/async, Protokoll)<br>- Markierung: welche Container sind MVP-kritisch?<br>- Markierung: was kommt nach MVP? |
| --- |


| **Finales C2 Container Diagram** |
| --- |
| **Container** — **Technologie** — **Aufgabe** — **Kommuniziert mit** — **MVP?** |


**Schritt 2 · ADRs finalisieren (15 Min)**

**Überarbeitet eure beiden ADRs basierend auf dem Review. Jedes ADR final — bereit für euer Projekt-Repo:**

| **ADR-001 finalisiert:**<br>**Titel:**<br>**Entscheidung:**<br>**Wichtigste Konsequenz:** | **ADR-002 finalisiert:**<br>**Titel:**<br>**Entscheidung:**<br>**Wichtigste Konsequenz:** |
| --- | --- |



| **L3** | **Architecture Pitch vorbereiten**   ·   14:45 – 15:15<br>**5 Minuten — euren Architektur-Entscheidungen verteidigen.** |
| --- | --- |


**Jedes Team hat 5 Minuten. Ihr präsentiert euren Architecture Draft — und verteidigt eure Entscheidungen. Die anderen Teams stellen Fragen.**

| **Pitch-Struktur — 5 Minuten** |
| --- |
| **1 Min** — **Das System** — **Was baut ihr? Für wen? Welches Problem löst es? — in 60 Sekunden**<br>**1 Min** — **C2 zeigen** — **Euer Container Diagram — kurz erklären was wo läuft**<br>**1 Min** — **Wichtigstes ADR** — **Eure kritischste Entscheidung — und warum ihr sie so getroffen habt**<br>**1 Min** — **Pattern-Wahl** — **Monolith / Modularer Monolith? Warum? Was spricht dagegen?**<br>**1 Min** — **Offene Fragen** — **Was bleibt unsicher? Was klärt ihr in Modul 4 & 5?** |


**Pitch vorbereiten mit AI (20 Min):**

| Wir haben 5 Minuten um unsere Architektur zu pitchen.<br>Hier ist unser finaler Architecture Draft: [EINFÜGEN]<br>Hilf uns:<br>1. Den stärksten 1-Satz für unser System formulieren<br>2. Die 3 Punkte identifizieren die ein CTO sofort fragen würde<br>3. Vorbereiten wie wir auf 'Warum nicht Microservices?' antworten<br>4. Vorbereiten wie wir auf 'Was ist euer grösstes Risiko?' antworten<br>5. Was wir NICHT sagen sollten um Zeit zu sparen |
| --- |


| **Unser 1-Satz für das System:**<br>**Antwort auf: «Warum nicht Microservices?»** | **Antwort auf: «Was ist euer grösstes Risiko?»**<br>**Was wir NICHT sagen werden:** |
| --- | --- |



| **L4** | **Architecture Pitch**   ·   15:15 – 16:15<br>**Jedes Team präsentiert · Jedes Team stellt Fragen · 10 Min pro Team.** |
| --- | --- |


**Jetzt wird es ernst. Ihr verteidigt eure Architektur-Entscheidungen vor der Gruppe. Das ist wie ein echtes Design Review in einem Unternehmen.**

| **Fragen für das Publikum — stellt mindestens 2 pro Team** |
| --- |
| **01** — **Single Point of Failure?**<br>**Was passiert wenn [Container X] ausfällt? Gibt es Fallbacks?**<br>**02** — **Warum diese Technologie?**<br>**Was war die Alternative? Warum habt ihr sie abgelehnt?**<br>**03** — **Passt das Pattern wirklich?**<br>**Ihr sagt Modularer Monolith — aber euer C2 sieht aus wie Microservices?**<br>**04** — **Was ist euer MVP-Critical Path?**<br>**Welche 3 Container müssen als erstes stehen damit ihr testen könnt?**<br>**05** — **Wie testet ihr das?**<br>**Wie schreibt ihr Tests für eure Architektur? Was ist schwer testbar?**<br>**06** — **Was würdet ihr heute anders machen?**<br>**Im Nachhinein — welche Entscheidung bereut ihr schon jetzt?** |


**Feedback-Protokoll — für das Publikum:**

| **Team 1** |
| --- |
| **Stärkste Architektur-Entscheidung:**<br>**Unsere Frage an das Team:** — **Schwächste Stelle / was wir anders machen würden:**<br>**Was wir von diesem Team lernen:** |
| **Team 2** |
| **Stärkste Architektur-Entscheidung:**<br>**Unsere Frage an das Team:** — **Schwächste Stelle / was wir anders machen würden:**<br>**Was wir von diesem Team lernen:** |
| **Team 3** |
| **Stärkste Architektur-Entscheidung:**<br>**Unsere Frage an das Team:** — **Schwächste Stelle / was wir anders machen würden:**<br>**Was wir von diesem Team lernen:** |


| **Modul 3 abgeschlossen — Ausblick Modul 4** |
| --- |
| **Ihr habt jetzt einen vollständigen Architecture Draft. Das ist die Grundlage für alles was kommt:**<br>Modul 4 — Planung: Euer Architecture Draft wird zum Sprint-Plan. Welche Container baut ihr zuerst?<br>Modul 5A — Claude Code: Ihr gebt Claude Code euren C2-Draft und lasst ihn die Struktur aufbauen<br>Modul 5B — Agents: Euer erster Agent bekommt eure OpenAPI Spec und nutzt sie als Tools<br>Modul 6 — Testing: Ihr testet gegen eure Acceptance Criteria aus Modul 2<br>**Hausaufgabe: Speichert euren Architecture Draft (C2 + ADRs) in eurem Projekt-Repo. Überlegt welchen Container ihr als erstes bauen würdet — und warum.** |



**CAS ADAI 2026 · BFH Biel · Modul 3 Tag 2 · Ilja Rasin**


