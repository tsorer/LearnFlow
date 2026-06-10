# L4 · Peer Review — Architektur-Feedback
*LearnFlow · Modul 3 Tag 1 · Reto Stucki · 2026-05-31*

---

## Feedback-Protokoll — LearnFlow wird reviewed

| Feld | Inhalt |
|---|---|
| **Projekt das wir reviewen** | LearnFlow — interne RAG-Lernplattform |
| **Kritischste Schwachstelle** | Single Point of Failure Datenbank: kein Replica, kein Backup definiert, Original-Dokumente als bytea — ein DB-Crash vernichtet alles |
| **Was ist architektonisch stark?** | LiteLLM-Abstraktion ist konsequent durchgezogen — Provider-Wechsel ohne Code-Change ist für ein 3-Dev-Team ein echter Vorteil. pgqueuer statt Redis hält den Stack schlank. |
| **Was fehlt im Architecture Draft?** | Backup-Strategie fehlt vollständig. Kein Wort zu pg_dump, keinem Recovery-Plan. Für ein System das interne Unternehmensdokumente speichert ist das keine Kleinigkeit. |
| **Single Point of Failure den wir gefunden haben** | PostgreSQL ohne Replica. Alle anderen Container (API Server, Worker) sind recoverable in < 60 s. Die DB ist der einzige Container dessen Ausfall Datenverlust bedeutet — nicht nur Downtime. |
| **Welches Pattern würden WIR wählen — und warum?** | Ebenfalls Modularer Monolith — die Entscheidung ist für diesen Kontext richtig. Aber der Background Worker als «bewusste Ausnahme» muss streng bewacht werden: das ist der häufigste Einstiegspunkt in unkontrollierte Fragmentierung. |
| **Unsere wichtigste Frage an das Team** | Wie wird Quellenhervorhebung konkret implementiert? PDF.js im Browser ist nicht trivial — ist das MVP-Scope oder wird es für Tag 1 reduziert? Diese Entscheidung fehlt im Draft. |

---

## Review-Antworten — 6 Fragen

### 01 · Single Point of Failure?

**Die Datenbank — und sie ist schlechter abgesichert als dokumentiert.**

Der API Server fällt aus → Docker Restart Policy bringt ihn in ~30 s zurück, laufende SSE-Streams brechen ab.  
OpenAI API fällt aus → Circuit Breaker greift, Fehlermeldung, kein Halluzinations-Risiko.  
**Datenbank fällt aus → alles ist down, und bei Datenverlust gibt es keinen Fallback.**

Die Architektur dokumentiert die DB als Single Point of Failure, zieht aber keine Konsequenz daraus. Ein täglicher `pg_dump` ist notwendig — er ist nicht im Draft erwähnt, nicht im Docker Compose geplant, nicht als Risiko eingestuft.

---

### 02 · Wie skaliert das System — was bricht zuerst bei 10× Nutzern?

**OpenAI Rate Limits brechen zuerst, gefolgt von der Datenbank.**

| Komponente | Verhalten bei 10× Last | Massnahme |
|---|---|---|
| OpenAI API | Rate Limits: Requests-per-Minute und Tokens-per-Minute sind fix — 300 statt 30 parallele Anfragen erzeugen Throttling | Quota erhöhen (Wochen Vorlaufzeit), Retry mit Exponential Backoff |
| Datenbank | 300 parallele Similarity Searches (pgvector HNSW) + kein Connection Pooling → Verbindungserschöpfung | PgBouncer, Read Replica |
| Background Worker | Single-Threaded: Queue wächst, SLA bricht — aber keine Daten verloren | Worker-Parallelität erhöhen |
| API Server | FastAPI async hält 10× Last aus — kein Problem | — |
| Web App | Nginx Static Serving skaliert horizontal trivial | — |

Für den MVP (< 30 Nutzer) ist das irrelevant. Für Post-MVP Multi-Bereich ist OpenAI-Quota das erste echte Hindernis.

---

### 03 · Wo sind die Security-Risiken?

**API Server und Datenbank sind die kritischen Punkte.**

| Risiko | Container | Beschreibung |
|---|---|---|
| **Sensitive Daten im Klartext** | Datenbank | Original-Dokumente (bytea), Embeddings, Query-Logs, Feedback-Freitext — alles in einer unverschlüsselten PostgreSQL-Instanz. Kein Encryption-at-Rest im Draft erwähnt. |
| **XSS bei Quellenrendering** | Web App | Wenn Quellentext als HTML gerendert wird (für Hervorhebung), entsteht XSS-Risiko. React schützt bei `dangerouslySetInnerHTML` nicht automatisch. |
| **LLM-Prompt-Injection** | API Server | User-Input fliesst direkt in LLM-Prompts. Ein gezielter Prompt kann das System zu unerwünschten Ausgaben bringen. Kein Input-Sanitizing im Draft dokumentiert. |
| **bytea-Zugriff über API** | API Server | Jeder authentifizierte User kann theoretisch Dokumente abrufen — RBAC muss Dokument-Zugriff auf den eigenen Bereich beschränken. MVP: 1 Bereich, unkritisch. Post-MVP: ohne Bereichs-Isolation ein Datenleck. |

---

### 04 · Passt das Pattern zum Team?

**Ja — aber mit zwei konkreten Einschränkungen.**

Der Modulare Monolith ist die richtige Wahl für 3 Devs in 3 Monaten. Ein einziges `docker compose up`, kein Distributed-Systems-Overhead, das gesamte Python-KI-Ökosystem im API Server.

**Einschränkung 1:** Die RAG-Pipeline ist algorithmisch komplex — Chunking-Strategie, Konfidenz-Scoring, Self-Check sind keine Framework-Fragen. Das kostet Sprint-0-Zeit die im Plan stehen muss, sonst gerät Sprint 1 sofort in Verzug.

**Einschränkung 2:** Frontend ist Backend-lastig. PDF-Rendering + Quellenhervorhebung + SSE-Streaming-UI sind Frontend-Aufgaben die 2–3 Wochen kosten wenn kein dedizierter Frontend-Dev im Team ist. Das Pattern hilft hier nicht — das ist ein Ressourcenproblem.

---

### 05 · Stimmen ADRs mit C2 überein?

**Weitgehend ja — eine Inkonsistenz.**

ADR-001 (Modularer Monolith) beschreibt alle Module in einem Deployment-Artefakt. Das C2-Diagram zeigt jedoch 4 Container — darunter den Background Worker als separaten Prozess. Das ist kein Widerspruch wenn man die Ausnahme explizit dokumentiert (was ADR-002 tut), aber ADR-001 müsste aktualisiert werden um die Worker-Ausnahme zu reflektieren. Aktuell steht ADR-001 noch auf «Proposed» — er sollte vor Sprint 1 auf «Accepted» gesetzt und um den Worker-Entscheid ergänzt werden.

---

### 06 · Was hat AI nicht bedacht?

**Drei business-spezifische Constraints die im Draft fehlen:**

1. **Onboarding-Prozess für Stefan** — Wie kommt das erste Dokument in den Korpus? Wer legt Stefans Account per DB-Script an? Der MVP hat kein Admin-UI für User-Management — der Prozess für den Pilot-Start (Wer macht das? Wann? Wie?) ist nicht dokumentiert.

2. **Qualitätsschwelle für den Go/No-Go-Entscheid** — Der Tech Spike soll zeigen ob die RAG-Qualität erreichbar ist. Aber: welche Qualität ist «gut genug»? Ohne definiertes Evaluationsdataset und festgelegte Mindest-Scores (z. B. «80 % der Testfragen korrekt beantwortet») ist der Spike kein Go/No-Go, sondern ein Experiment ohne Abbruchkriterium.

3. **E-Mail-Service für US-06** — Stefan soll monatlich einen Report über veraltete Dokumente erhalten. Im gesamten Architecture Draft ist kein Mail-Service, kein SMTP-Provider, keine Konfiguration dafür erwähnt. Das ist eine externe Abhängigkeit die früh in Sprint 0 angestossen werden muss.

---

## Feedback empfangen — was nehmen wir mit

| Feld | Inhalt |
|---|---|
| **Was nehmen wir aus dem Peer Review mit?** | Backup-Strategie (pg_dump) muss vor Pilot-Start explizit implementiert und dokumentiert werden. Prompt-Injection als Security-Risiko war im Draft nicht auf dem Radar — muss in Sprint 1 adressiert werden. |
| **Was ändern wir noch heute am Draft?** | ADR-001 Status von «Proposed» auf «Accepted» setzen und Worker-Ausnahme ergänzen. Backup-Strategie als offene Frage in L3-Output nachtragen. |
| **Offene Fragen die wir in Tag 2 klären wollen** | (1) Evaluationsdataset und Go/No-Go-Kriterien für Tech Spike definieren. (2) Quellenhervorhebung: MVP-Scope festlegen (PDF.js oder vereinfacht). (3) E-Mail-Service-Entscheid vor US-06-Implementierung. |

---

*Quellen: [Modul3Tag1_Lab_L3_Output.md](Modul3Tag1_Lab_L3_Output.md) · [Docs/05_C4-C2_Container.md](../../Docs/05_C4-C2_Container.md) · [Docs/02_Requirements.md](../../Docs/02_Requirements.md)*
