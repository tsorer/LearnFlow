# Advocatus Diaboli: Modularer Monolith für LearnFlow

*Frage gestellt: 2026-06-03 · Kontext: 4 Developer, 3 Monate Zeitrahmen*

---

## Frage

> Für die LearnFlow Applikation haben wir uns generell für das Design **Modularer Monolith** entschieden.
> Unser Kontext: Wir sind 4 Developer, der Zeitrahmen ist 3 Monate.
>
> Spiele jetzt den Advocatus Diaboli:
> 1. Warum ist diese Entscheidung für uns FALSCH?
> 2. Was werden wir in 6 Monaten bereuen?
> 3. Welches Pattern wäre ehrlich gesagt besser — und warum?
> 4. Was müssen wir tun damit unsere Wahl wirklich funktioniert?

---

## Antwort

### 1. Warum diese Entscheidung FALSCH ist

**Ihr baut gar keinen Monolith — ihr nennt ihn nur so.**

Schaut auf eure tatsächliche Laufzeit-Architektur:

```
Process 1:  FastAPI (async, IO-bound)        → API-Server
Process 2:  Background Worker (pgqueuer)     → Dokument-Indexierung
Process 3:  Ollama / Azure OpenAI            → Embedding-Inferenz
Process 4:  React SPA (Nginx)                → Frontend
Process 5:  PostgreSQL                       → Datenbank
```

**Das sind fünf Prozesse.** Die Entscheidung "Modularer Monolith" beschreibt die Deployment-Fantasie, nicht die Realität. Ihr habt euch bereits gegen einen Monolith entschieden, ohne es zu merken.

Das eigentliche Problem ist tiefer: LearnFlow ist **keine CRUD-Applikation** mit gleichartigen Komponenten — es ist eine ML-Inferenz-Pipeline mit einer CRUD-Applikation obendrauf. Diese beiden Welten haben fundamental unterschiedliche Profile:

| | API-Server | Document-Worker |
|---|---|---|
| **Charakter** | IO-bound, async, latenz-kritisch | CPU-bound, sync, throughput-kritisch |
| **Ausfallreaktion** | → 503, User sieht Fehler | → Job bleibt in Queue, kein User-Impact |
| **Skalierung** | horizontal (mehr Requests) | vertikal (mehr CPUs) |
| **Ressource** | RAM, Netzwerk | CPU, Speicher |

Diese beiden Dinge in dieselbe "modulare" Einheit zu zwingen ist wie ein Taxiservice und ein Transportunternehmen zu fusionieren, weil beide Autos haben.

**Das konkrete technische Risiko:** FastAPI ist async. Embedding-Inferenz (Ollama, sentence-transformers) ist synchron und CPU-intensiv. Wenn ihr einen Embedding-Aufruf im async Event Loop macht ohne `run_in_executor`, blockiert **jede laufende Anfrage aller Nutzer** bis der Aufruf fertig ist. Das ist kein Stil-Problem — das ist ein Korrektheitsproblem.

---

### 2. Was ihr in 6 Monaten bereuen werdet

**Bereuen 1: Die Module bluten ineinander.**

Mit 4 Entwicklern unter Deadline-Druck werden Modulgrenzen innerhalb von Wochen gebrochen. Nicht böswillig — sondern weil `from rag.pipeline import _internal_helper` schneller geht als das richtige Interface zu schreiben. Nach 3 Monaten MVP-Sprint ist aus "Modularer Monolith" ein klassischer Big Ball of Mud geworden. Ihr werdet einen `utils.py` mit 800 Zeilen haben.

**Bereuen 2: Das Embedding-Modell muss gewechselt werden.**

ADR-005 ist explizit: das produktive Embedding-Modell (`text-embedding-3-small`) ist für deutschen Fachkorpus möglicherweise nicht optimal. Der Spike soll das klären. Wenn ihr nach Monat 2 das Modell wechselt, bedeutet das:
- Vollständige Re-Indexierung aller Dokumente
- Während der API-Server weiter Requests beantwortet
- Im selben Prozess, der den Worker betreibt
- Ohne Rollback-Mechanismus

In einer echten Zwei-Service-Architektur würdet ihr einfach einen neuen Worker starten, parallel re-indexieren und dann switchen.

**Bereuen 3: Ein grosses PDF lähmt alle Nutzer.**

Stefan lädt eine 100-MB-Compliance-Doku hoch. Der Background Worker (pgqueuer, single-threaded) fängt an zu parsen, zu chunken, zu embedden. Das dauert Minuten. Gleichzeitig versucht Lara eine Frage zu stellen. Beide sind im selben Prozess. Ihr werdet `ulimit`, Thread-Pools und Process-Isolation nachträglich einbauen — unter Druck, mit schlechtem Testablauf.

**Bereuen 4: Observability ist blind.**

In einem echten Monolith gehen alle Logs in denselben Stream. Wenn eine p95-Latenzspike auftaucht, könnt ihr nicht einfach sagen "das ist der Worker, nicht der API-Server". Ihr werdet Stunden in Incident-Debugging verlieren, die ihr in der Entwicklung hättet investieren sollen.

**Bereuen 5: Post-MVP-SSO und Multi-Bereich.**

Beide sind angekündigt. Multi-Bereich bedeutet: isolierte Datenräume, möglicherweise verschiedene Embedding-Corpora, verschiedene Konfigurations-Sets. Ein sauber getrennter Worker ist dabei direkt erweiterbar. Ein Monolith, der beides macht, bekommt schnell eine `if area_id == 'bereich_2': use_different_config()` Logik.

---

### 3. Welches Pattern wäre ehrlich gesagt besser

**Nicht Microservices. Aber auch kein Monolith.**

Das ehrliche Optimum für euren Kontext heisst:

> **Intentional Two-Container Architecture** — zwei Docker-Container, eine Datenbank, keine verteilte Komplexität.

```
┌─────────────────────┐     ┌──────────────────────────┐
│   API Container     │     │    Worker Container       │
│                     │     │                           │
│  FastAPI (async)    │     │  Document Parser          │
│  Auth / RBAC        │     │  Chunking Pipeline        │
│  RAG Query          │     │  Embedding (LiteLLM)      │
│  Quiz / Feedback    │     │  pgvector Indexing        │
│  Admin Config       │     │  pgqueuer Job Consumer    │
│                     │     │                           │
│  Port 8000          │     │  No HTTP — only DB        │
└─────────┬───────────┘     └────────────┬─────────────┘
          │                              │
          └──────────┬───────────────────┘
                     │
          ┌──────────▼───────────┐
          │   PostgreSQL 17      │
          │   + pgvector         │
          │   + pgqueuer         │
          └──────────────────────┘
```

**Docker Compose:**
```yaml
services:
  api:      # FastAPI — skalierbar, isoliert
  worker:   # Document processing — crasht ohne User-Impact
  db:       # PostgreSQL 17 + pgvector
  frontend: # React + Nginx
```

Das sind **4 Container in Docker Compose** — vollständig managebar für 4 Entwickler. Ihr könnt lokal mit `docker compose up api db` arbeiten ohne den Worker zu starten. Ein Worker-Crash bricht nicht die API. Ein API-Redeploy stoppt nicht die laufenden Indexierungs-Jobs.

**Warum das besser ist als Modularer Monolith:**
- Ihr seid ehrlich über die Grenze, die eh da ist
- CPU-bound Worker und IO-bound API konkurrieren nicht um denselben Event-Loop
- Worker-Failures haben null User-Impact
- Ihr könnt den Worker unabhängig resource-limitieren (`--cpus 2`)

**Warum das NICHT Microservices sind:**
- Eine gemeinsame Datenbank — kein verteiltes State-Management
- Kein Service-Discovery, kein API-Gateway
- Kein Netzwerk-Hop zwischen API und Worker (beide nutzen DB)
- Deployment: ein `docker compose up` — keine Kubernetes-Komplexität

---

### 4. Was ihr tun müsst, damit eure Wahl wirklich funktioniert

Falls ihr am Modularen Monolith festhaltet, müsst ihr **vier Dinge ohne Kompromiss** durchziehen:

**1. Architektur-Fitness-Funktionen von Woche 1**

Schreibt automatische Tests, die prüfen, dass Modulgrenzen nicht verletzt werden:

```python
# test_architecture.py — läuft in CI
def test_rag_module_does_not_import_auth():
    import ast, pathlib
    for f in pathlib.Path("app/rag").rglob("*.py"):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert "auth" not in str(node.names), \
                    f"{f}: RAG-Modul importiert Auth — Grenzüberschreitung!"
```

Ohne diese Tests ist "modular" ein Wunsch, keine Garantie.

**2. Event-Loop niemals mit CPU-Arbeit blockieren**

Jeder synchrone Call muss in einen Thread-Pool:

```python
# FALSCH — blockiert alle anderen Requests:
embedding = ollama.embed(text)

# RICHTIG:
embedding = await asyncio.get_event_loop().run_in_executor(
    cpu_executor, ollama.embed, text
)
```

Macht das zu einer Lint-Regel: kein direkter Aufruf von Embedding/Parsing-Funktionen aus async-Routen.

**3. Worker als separate Entry-Point — auch wenn co-deployed**

Zwei separate Python-Einstiegspunkte von Anfang an:

```
app/
  main.py          # uvicorn app.main:app  → API
  worker.py        # python app/worker.py  → pgqueuer consumer
```

Das ermöglicht euch, in 3 Monaten auf zwei Container umzustellen, ohne Code zu ändern — nur die Deployment-Konfiguration ändert sich.

**4. Definiert den Extraktionspunkt jetzt**

Schreibt heute in ein Dokument:

> *"Sobald wir X Nutzer / Y gleichzeitige Uploads / Z Dokumente erreichen, wird der Worker in einen separaten Container extrahiert."*

Ohne diese Entscheidung im Voraus ist die Monolith-Wahl ein implizites "nie wieder anfassen". Das ist kein Architekturentscheid — das ist Vermeidung.

---

## Fazit

> Ihr habt euch bereits für eine Zwei-Service-Architektur entschieden (API + Worker) — die Frage ist nur, ob ihr das **explizit und sauber** macht, oder **implizit und schmerzhaft**.

---

*Christoph A. Amstutz, MD-PhD · Claude Sonnet 4.6 · 2026-06-03*
