# LearnFlow — Quality Attributes v1
*Modul 3 Tag 1 · Mai 2026*

---

## 1. Übersicht — alle Quality Attributes

| Quality Attribute | Nicht-funktionale Anforderung (NFA) — messbar & beobachtbar | Warum wichtig für uns? |
|---|---|---|
| **Performance** | Antwortzeit ≤ 10 s am 95. Perzentil unter Normallast · Dokument nach Upload innerhalb von ≤ 5 Minuten als Quelle verfügbar · Batch-Response (vollständige, geprüfte Antwort als JSON); Wartezeit wird über Retrieval-Optimierung (ADR-007) und Ladeanimation im Frontend eingehalten | RAG-Pipeline (Retrieval + Embedding + LLM-Generierung) addiert Latenzen inhärent. Überschreitet die Wartezeit die Schwelle, bricht Lara ab und fragt wieder bei Stefan nach — das Kernversprechen entfällt. |
| **Scalability** | Maximale Gleichzeitigkeit im MVP: < 30 Nutzer, 1 Pilot-Bereich hartcodiert · Architektur muss Multi-Bereich-Ausbau ermöglichen ohne Redesign (stateless Services, kein shared State) | Kein Skalierungsdruck heute — aber eine zustandsbehaftete Architektur würde den Post-MVP-Ausbau auf mehrere Bereiche zu einem vollständigen Umbau machen. |
| **Security** | Kein Systemzugriff ohne gültige Authentifizierung · Jede Ressource erfordert rollenbasierte Autorisierung (Lernende / Bereichsverantwortlicher / Admin) · Personenbezogene Daten verlassen die EU nicht (DSGVO) · Feedback und Query-Logs werden pseudonymisiert gespeichert · Cluster < 5 Fragen werden nicht angezeigt (Re-Identifikationsschutz) · Auth-Basis SSO-nachrüstbar ohne Umbau | Interne Unternehmensdokumente und Fachprozesse sind schützenswert. DSGVO-Compliance ist im Schweizer Enterprise-Umfeld nicht verhandelbar. Eine einmalige Datenpanne beendet den Piloten. |
| **Reliability** | Halluzinationsrate = 0 %: Das System darf niemals eine Antwort ohne valide, belegbare Quellenreferenz ausgeben · Ausfall des LLM-Service darf nie zu einer generierten Fallback-Antwort führen — kontrollierte Degradation (Fehlermeldung) ist Pflicht · Out-of-Corpus-Erkennungsrate: ≥ 90 % „Weiss ich nicht" · MVP bewusst: kein HA-Setup, Single-Instance, Business-Hours-Nutzung | Eine halluzinierte Antwort mit echter Quellenangabe ist unsichtbar — Lara merkt es nicht, handelt falsch, verliert Vertrauen erst Wochen später. Das ist existenziell für den Pilot, unabhängig von der Nutzerzahl. |
| **Maintainability** | Alle Konfigurationsparameter (Konfidenz-Schwellenwert, Stale-Schwellenwert, Cluster-Mindestgrösse) müssen ohne Code-Deployment und ohne Systemstart geändert werden können · LLM-Provider wechselbar durch Konfiguration — kein Code-Change (LiteLLM-Abstraktion) · Jede RAG-Komponente austauschbar ohne Seiteneffekte auf andere Module | 320–480 h Gesamtbudget. Jede Stunde für operative Anpassungen fehlt bei der Kernentwicklung. Provider-Wechsel (Cloud vs. OnPrem) muss ohne Entwickler-Eingriff möglich sein. |
| **Testability** | Out-of-Corpus-Erkennungsrate ≥ 90 % „Weiss ich nicht" als messbares Akzeptanzkriterium · Halluzinationsrate messbar und regressionsfähig bevor die Implementierung startet (Tech Spike als Go/No-Go) · Jede RAG-Komponente (Chunking, Embedding, Retrieval, Generierung) einzeln isolierbar und testbar · Konfidenz-Scoring-Mechanismus muss formal definiert sein, bevor er testbar ist | RAG-Qualität ist ein empirisches Phänomen — nicht durch Code-Review validierbar. Ohne Testability weiss das Team nie, ob Reliability (Halluzinationsrate = 0 %) tatsächlich erreicht ist. |

---

## 2. Ranking — Top 3 Quality Attributes

| Rang | QA | Begründung |
|---|---|---|
| 1 | **Reliability** | Stärkste und existenziellste NFA: Halluzinationsrate = 0 %, Out-of-Corpus ≥ 90 % „Weiss ich nicht". Eine halluzinierte Antwort mit echter Quellenangabe bricht das Vertrauen — irreparabel und unabhängig von der Nutzerzahl. |
| 2 | **Security** | Regulatorische NFA: DSGVO — personenbezogene Daten verlassen die EU nicht. Binär: entweder erfüllt oder nicht. Interne Dokumente machen unbefugten Zugriff zu einem Business-Stopper. |
| 3 | **Maintainability** | Budget-getriebene NFA: 320–480 h total. Schwellenwerte müssen ohne Entwickler-Einsatz änderbar sein. LLM-Provider-Wechsel (Cloud vs. OnPrem) muss per Konfigurationseintrag erfolgen — sonst ist es ein Vertriebshindernis. |

---

## 3. Tiefenanalyse Top 3

### #1 · Reliability

**Warum existenziell:**
LearnFlow hat ein einziges Qualitätsversprechen: *Verlass dich auf die Antwort.* Eine halluzinierte Antwort mit echter Quellenangabe ist unsichtbar — Lara merkt es nicht, handelt danach, und verliert das Vertrauen erst Wochen später. Dann ist es zu spät für den Piloten.

**Architektonische Massnahmen:**

1. **Mehrschichtiger Unterdrückungsmechanismus** (Reihenfolge gemäss Entscheid 2026-05-20):
   ```
   Quellenprüfung → Konfidenz-Score → Self-Check-Anteil
        ↓ keine Quelle      ↓ Score < Schwelle    ↓ < 50 %
     "Keine Antwort"     "Weiss nicht"          Unterdrückt
   ```
2. **Circuit Breaker für LLM-Aufrufe** — Timeout, HTTP 5xx, Quota erschöpft → Fehlermeldung, nie ein generierter Fallback-Text.
3. **Fail-Safe als Designprinzip** — kein Antwort ist immer besser als eine unsichere Antwort; in Code-Reviews aktiv prüfen.
4. **Konfidenz-Schwellenwerte in der DB, nicht im Code** — empirisch kalibrierbar nach Tech Spike, änderbar ohne Deployment.

**Was passiert wenn wir Reliability ignorieren:**
Lara erhält eine plausibel klingende Antwort mit echter Quellenangabe, handelt danach falsch. Stefan erfährt es, verliert das Vertrauen. Der Pilot wird eingestellt — nicht weil die Technik versagte, sondern weil Vertrauen einmal gebrochen ist.

---

### #2 · Security

**Warum nicht verhandelbar:**
Interne Unternehmensdokumente im Korpus machen unbefugten Zugriff zu einem Business-Stopper. DSGVO-Verstoss ist kein technisches Risiko, sondern ein rechtliches.

**Architektonische Massnahmen:**

1. **JWT (8 h) + bcrypt-Hashing** für lokale Authentifizierung.
2. **Admin-Middleware für rollenbasierte Zugriffskontrolle** — URL-Zugriff ohne korrekte Rolle wird serverseitig abgewiesen.
3. **Pseudonymisierung** von Feedback und Query-Logs; Cluster < 5 Fragen nicht anzeigen.
4. **Auth-Schicht SSO-nachrüstbar** — ohne Umbau, wenn Post-MVP IdP-Anbindung kommt.
5. **DSGVO:** OpenAI API verwendet API-Daten standardmässig nicht für Training (API ≠ ChatGPT WebUI). Für datenschutzkritische Deployments: Ollama (lokal) — ein Konfigurationseintrag.

**Was passiert wenn wir Security ignorieren:**
Interne Fachprozesse und Dokumente sind öffentlich zugänglich. DSGVO-Verletzung beendet den Piloten rechtlich, bevor er technisch scheitern kann.

---

### #3 · Maintainability

**Warum budget-kritisch:**
320–480 h total — jede Stunde für operative Anpassungen fehlt bei der Kernentwicklung. Gleichzeitig muss der LLM-Provider für unterschiedliche Deployments (Cloud vs. OnPrem) konfigurierbar bleiben.

**Architektonische Massnahmen:**

1. **LiteLLM als Provider-Abstraktion** — `LLM_PROVIDER=openai` vs. `LLM_PROVIDER=ollama/llama3.2`: kein Code-Change, kein Deployment.
2. **Alle Schwellenwerte in der DB** (`config`-Tabelle) — Konfidenz-Schwellenwert, Stale-Schwellenwert, Cluster-Mindestgrösse. Wirken sofort ohne Neustart.
3. **Klare Modul-Grenzen** — RAG-Pipeline, Dokumentverwaltung, Quiz, Auth als eigenständige Module; kein Ripple-Effect bei Änderungen.
4. **Dependency Injection für den LLM-Client** — Provider-Swap in Produktion und Mock-Objekte in Tests; Maintainability und Testability verstärken sich gegenseitig.

**Was passiert wenn wir Maintainability ignorieren:**
Konfidenz-Schwellenwert ist falsch kalibriert — Stefan meldet das. Ein Entwickler braucht 2 Wochen (1 Tag/Woche). Stefan verliert die Geduld. Gleichzeitig fragt ein Kunde nach OnPrem-Betrieb — Antwort: „3 Wochen Umbau." Der Kunde entscheidet sich für eine andere Lösung.

---

## 4. Architektonische Massnahmen — Zusammenfassung

| QA | Massnahmen |
|---|---|
| **Reliability** | Mehrschichtiger Unterdrückungsmechanismus (Quellenprüfung → Konfidenz → Self-Check) · Circuit Breaker für LLM · Fail-Safe-Designprinzip · Schwellenwerte in DB |
| **Security** | JWT + bcrypt · RBAC-Middleware · Pseudonymisierung · SSO-nachrüstbar · Ollama für datenschutzkritische Deployments |
| **Maintainability** | LiteLLM-Abstraktion · `config`-Tabelle in DB · Modulare RAG-Komponenten · Dependency Injection |
| **Performance** | Batch-Response (FastAPI async + React fetch) · pgvector HNSW-Index · Dokument-Processing asynchron im Background Worker |
| **Testability** | Evaluationsdataset vor Sprint 1 · Automatisiertes Scoring im CI · Modulare RAG-Pipeline (jede Komponente einzeln testbar) |
| **Scalability** | Stateless Services · Docker Compose (Single Instance MVP) · Modul-Grenzen ohne shared State |

---

*Quelle: Docs/02_Requirements.md · BFH CAS ADAI 2026*
*Stand: v1 — 2026-05-27*
