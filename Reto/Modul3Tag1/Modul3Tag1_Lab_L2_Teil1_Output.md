# L2 · Teil 1 · Architektur-Pattern wählen
*LearnFlow · Modul 3 Tag 1 · Reto Stucki · 2026-05-31*

---

## Ausgangslage

Prompt: [Modul3Tag1_Lab_L2_Teil1_Prompt.md](Modul3Tag1_Lab_L2_Teil1_Prompt.md)  
Top-3 Quality Attributes: **Reliability · Security · Maintainability**  
Entscheidungsrahmen: Pattern-Wahl für MVP · 3 Devs · 3 Monate · 1 Pilot-Bereich

---

## Frage 1 · Welches Pattern empfiehlst du — und warum?

**Modularer Monolith.**

LearnFlow hat heute klare, abgrenzbare Domains: RAG-Pipeline, Dokumentverwaltung, Quiz, Auth, Admin-Konfiguration. Diese Grenzen sind im C2 bereits sichtbar — Web App, API Server, Background Worker, Datenbank sind vier klar getrennte Container. Der API Server als einzelner Prozess kann intern sauber in Module aufgeteilt werden (rag/, documents/, quiz/, auth/, admin/) ohne den Overhead verteilter Services.

Begründung für Modularer Monolith statt reinem Monolith:
- Diszipliniert aufgebaute Modul-Grenzen jetzt ermöglichen eine spätere Extraktion einzelner Module zu Services — ohne vollständigen Umbau.
- Der Background Worker ist bereits ein separater Prozess (pgqueuer) — die Trennung ist dort wo sie sinnvoll ist schon vorhanden.

Begründung gegen Microservices: siehe Frage 2.

---

## Frage 2 · Was würde für Microservices sprechen in UNSEREM Fall?

Ehrlich: **sehr wenig.**

Das einzige echte Argument für Microservices bei LearnFlow wäre die RAG-Pipeline: Embedding-Generierung, Retrieval und LLM-Generierung haben unterschiedliche Skalierungscharakteristiken (Embedding ist CPU-/GPU-intensiv, Retrieval ist DB-bound, LLM ist I/O-bound auf OpenAI). Wenn LearnFlow auf 10 Bereiche mit 300 Nutzern skaliert, wäre eine separate Embedding-Service-Instanz denkbar.

Für den MVP gilt: 3 Devs, 360–480 h, 1 Bereich, < 30 Nutzer. Microservices bedeuten:
- Service Discovery, Inter-Service-Auth, Distributed Tracing, Independent Deployments
- Das sind Wochen Setup-Aufwand bevor eine einzige Fachfunktion gebaut ist
- Bei 3 Devs ist das Koordinationsproblem grösser als der Skalierungsvorteil

---

## Frage 3 · Was wäre der grösste Fehler den wir machen könnten?

**Microservices wählen weil die RAG-Komponenten «logisch getrennt» wirken.**

Der zweithäufigste Fehler bei kleinen Teams: zu früh aufteilen. Wenn die Chunking-Strategie noch «offen» ist (wie im C2 dokumentiert) und das Konfidenz-Scoring noch undefiniert ist (Risiko 2 aus Requirements), ist das Letzte was wir brauchen verteilte Services mit synchronen HTTP-Calls zwischen Komponenten die noch gar nicht stabil designt sind.

Konkreter Fehler: Embedding-Service, Retrieval-Service und Generation-Service als separate Microservices — dann merken wir in Sprint 2 dass der Self-Check eine kombinierte Operation über alle drei braucht und haben ein verteiltes Transaktionsproblem.

---

## Frage 4 · Wie würde sich unsere C2-Struktur mit jedem Pattern verändern?

| Pattern | Veränderung am C2 |
|---|---|
| **Monolith** | Web App + API Server + Background Worker kollabieren zu einem einzigen Deployment-Artefakt. Kein separater Worker-Prozess — Dokument-Processing läuft als Thread im Monolith. Einfacher zu starten, schwerer zu skalieren, schwerer zu testen isoliert. |
| **Modularer Monolith** (empfohlen) | C2 bleibt wie heute — 4 Container. Der API Server wird intern in Module aufgeteilt (`rag/`, `documents/`, `quiz/`, `auth/`, `admin/`). Nach aussen ein einziger Prozess, innen saubere Grenzen. Background Worker bleibt separater Prozess weil asynchrones Processing eine echte physische Grenze rechtfertigt. |
| **Microservices** | API Server explodiert in: Auth-Service, RAG-Service (Embedding + Retrieval + Generation), Document-Service, Quiz-Service, Admin-Service. Jeder Service eigene DB oder Shared DB mit Schema-Isolation. Zusätzliche Container: API Gateway, Service Mesh oder zumindest internes DNS. Für 3 Devs in 3 Monaten: nicht lieferbar. |

---

## AI empfiehlt — mit Begründung

**Modularer Monolith** — weil das Team klein ist, die Domain noch nicht vollständig verstanden ist (Konfidenz-Scoring undefiniert, Chunking-Strategie offen) und der MVP mit einem einzigen Pilot-Bereich startet. Die C2-Grenzen (4 Container) sind bereits die richtigen physischen Schnitte. Die interne Modul-Struktur des API Servers legt die Grundlage für eine spätere Service-Extraktion — ohne heute den Overhead verteilter Systeme zu tragen.

---

## Wo stimmen wir nicht überein — und warum?

Der Background Worker ist bei LearnFlow bereits ein separater Prozess — das ist technisch gesehen kein reiner Modularer Monolith mehr, sondern eine hybride Variante. Diese Entscheidung ist richtig (Async-Processing braucht physische Trennung für den 5-Minuten-SLA), aber sie sollte bewusst als Ausnahme dokumentiert werden, nicht als Einstieg in «wir machen jetzt doch Microservices».

Zweiter Punkt: Die Quellenhervorhebung im Browser (PDF.js) und das Konfidenz-Scoring sind Komplexitäten die unabhängig vom gewählten Pattern zuerst gelöst werden müssen. Das Pattern hilft hier nicht — es verschleiert das Problem nur.

---

*Quellen: [Docs/05_C4-C2_Container.md](../../Docs/05_C4-C2_Container.md) · [Docs/03_QualityAttributes.md](../../Docs/03_QualityAttributes.md) · [Docs/02_Requirements.md](../../Docs/02_Requirements.md)*
