# Konversationsprotokoll — ADR-Review & Architektur-Konsolidierung

*Export für Doku-Zwecke · Datum: 2026-05-31 · Tool: Claude Code (KI-gestützt)*
*Kontext: LearnFlow, Sprint 0 / Tech-Spike · Arbeitsverzeichnis `Frank/Modul3Tag2/`*

> Dieses Dokument protokolliert den Dialog zwischen Entwickler (Frank) und Claude Code, der zur Überarbeitung der ADR-Serie, zwei neuen ADRs, der C4-Synchronisierung sowie dem Architecture Draft und dem HTML-Pitch geführt hat. Die Nutzer-Eingaben sind sinngemäß wiedergegeben, die Antworten zusammengefasst.

---

## 1. Python-Version (ADR-002)

**Frank:** Schau dir die Dateien im `docs`-Verzeichnis an. Macht es Sinn, Python 3.12 zu verwenden, wenn es bereits 3.14 gibt (04_ADR-002)?

**Claude:** Analyse: 3.12 ist nicht falsch, aber das ADR begründet die Versionswahl gar nicht. Empfehlung **Python 3.13** statt 3.12 oder 3.14 — Begründung: ML-Wheel-Reife (PyTorch/sentence-transformers hinken neuen Releases nach), 3.13 bietet vollen Ökosystem-Support plus async-/Tooling-Verbesserungen ohne Bleeding-Edge-Risiko von 3.14.

**Geklärt:** Dateistruktur — `Niklaus/`, `Reto/`, `Frank/` sind individuelle Arbeitsverzeichnisse; `Docs/` enthält Endergebnisse; die ADRs sollen (noch) nicht in `Docs/` liegen. Maßgeblich ist die Serie unter `Frank/Modul3Tag2/`.

**Ergebnis:** ADR-002 auf Python 3.13 umgestellt (Entscheidung + Begründung + Alternativen-Zeile „Python 3.14").

---

## 2. Alternativen zu React (ADR-002)

**Frank:** Welche Alternativen gibt es zu React 18? Die Begründung für React ist schwach.

**Claude:** Bestätigt — die Begründung ist schwach und widersprüchlich („Team kennt es" vs. „.NET-Team, Web nicht Schwerpunkt"). Alternativen abgewogen: Vue 3, Svelte/SvelteKit, Blazor, HTMX+Alpine, SolidJS.

**Frank:** Umgesetzt wird mit Claude Code. Inwieweit beeinflusst das die Bewertung?

**Claude:** Das verschiebt die Kriterien deutlich: Lernkurve/Boilerplate verlieren an Gewicht; **Trainingsdaten-Dichte** (weniger Halluzination bei Generierung) und **statische Typisierung** (Review-Netz) gewinnen. Netto: React-Entscheidung wird gestärkt — aber aus anderen Gründen als im ADR. HTMX bleibt einzige ernsthafte Gegenoption (Systemkomplexität).

**Frank:** Ja [umsetzen].

**Ergebnis:** Frontend-Abschnitt von ADR-002 neu begründet (KI-Implementierungs-bewusst), Kontext-Absatz zum Implementierungsmodell ergänzt, Alternativen-Tabelle um Vue/Svelte erweitert, HTMX-Zeile geschärft, React 18 statt bleeding-edge begründet.

---

## 3. PostgreSQL-Version (ADR-003)

**Frank:** Weiter mit ADR-003. Warum PostgreSQL 16?

**Claude:** Anders als bei Python greift das Wheel-Reife-Argument hier nicht (pgvector ist versionsunabhängig, Postgres-Majors ab Release stabil). Maßgeblich sind Docker-Image-Verfügbarkeit und Lebenszyklus. Empfehlung **PostgreSQL 17**.

**Frank:** [Auswahl] PostgreSQL 17.

**Ergebnis:** ADR-003 auf PostgreSQL 17 umgestellt (Titel, Entscheidung, Begründungsabsatz, Alternativen-Zeile „PostgreSQL 18").

---

## 4. Validität der Persistenz-Alternativen (ADR-003)

**Frank:** Ist die Bewertung der anderen Alternativen valide? Warum ist Postgres die beste Wahl?

**Claude:** Überwiegend valide, aber ein **sachlicher Fehler**: Supabase als „keine On-Prem-Option" ist falsch (Supabase ist self-hostbar; echter Grund = Ops-Last). Konzeptionell schwächste Stelle ist die `bytea`-Entscheidung für große Dateien (MinIO/Object Storage fehlte als Alternative). Postgres gewinnt, weil es als einziges relational + Vektor in einem ACID-Service bei kleiner Skala + On-Prem erfüllt.

**Frank:** Ja, bitte korrigieren.

**Ergebnis:** Supabase-Zeile korrigiert; MinIO-Zeile als Datei-Ablage-Alternative ergänzt.

---

## 5. LLM-Provider (ADR-004)

**Frank:** Weiter mit ADR-004.

**Claude:** Inhaltlicher Widerspruch: OpenAI Direct (US-Server) als Produktions-Default widerspricht der Datenschutz-Linie (interne Dokumente, ADR-001 wählte Azure OpenAI EU). Beim Indexieren geht der ganze Korpus an den Provider.

**Frank:** [Auswahl] EU-konform als Default.

**Ergebnis:** ADR-004 auf **Azure OpenAI EU** als Produktiv-Default umgestellt (LiteLLM), OpenAI Direct als Dev-/Test-Pfad ohne Produktivdaten, Ollama als OnPrem. Kontext, Konsequenzen und Alternativen (inkl. Anthropic via Bedrock EU als echtem Kriterium) überarbeitet.

---

## 6. Embedding-Modell (ADR-005)

**Frank:** Weiter mit ADR-005.

**Claude:** Datenschutz-Punkt zieht durch (Indexierung = datenintensivste Exposition). Konsistent zu ADR-004 angeglichen.

**Frank:** Machen die angegebenen Modelle und Dimensionen Sinn?

**Claude:** Dimensionen faktisch korrekt (1536 / 1024 / 768). Zwei Kritikpunkte: (1) Sprach-Fit „verkehrt herum" — englisch-optimiertes `text-embedding-3-small` in Produktion, starkes Deutsch-Modell `bge-m3` nur lokal; (2) fehlende Kopplung zu ADR-003: pgvector-HNSW indexiert nur bis 2000 Dim (`text-embedding-3-large`/3072 bräuchte Matryoshka oder `halfvec`). Empfehlung: Produktionsmodell als Spike-Eval offen lassen.

**Frank:** Ja [beides umsetzen].

**Ergebnis:** ADR-005 — Provider auf Azure EU; `text-embedding-3-large`-Alternative; Spike-Eval-Markierung; HNSW-2000-Dim-Constraint dokumentiert (auch in ADR-003); Matryoshka-Hinweis ergänzt.

---

## 7. Background-Worker (ADR-006)

**Frank:** Weiter mit ADR-006.

**Claude:** Stärkstes ADR der Serie. Kritik: Alternativen-Tabelle zu schmal (es fehlen **procrastinate**, handgerollt `SKIP LOCKED`, FastAPI BackgroundTasks-Querverweis, ARQ/Dramatiq/SAQ). Konsistenz-Fixes: „OpenAI Rate Limit" → Azure; stale Pfadverweis.

**Frank:** Ja, bitte beides anpassen.

**Ergebnis:** Alternativen erweitert, Konsistenz-Fixes umgesetzt.

---

## 8. Vollständigkeit für die Umsetzung

**Frank:** Würden die ADRs für eine Umsetzung reichen oder fehlen noch relevante Sachen?

**Claude:** Nein, noch nicht. Implementierungs-blockierend: (1) **Chunking-/Retrieval-Strategie (ADR-007 fehlt)**, (2) Datenmodell + OpenAPI-Kontrakt, (3) `bytea` vs. `lo`, (4) Spezifikation der Konfidenz-Pipeline. Wichtig: Auth-Detail, Quiz, Eval-Harness, Secrets, Bulk-Upload-Rate-Limiting. Plus Konsistenz-Drift im C4-Dokument.

---

## 9. Neue ADRs

**Frank:** Erstell zunächst den ADR-007.

**Ergebnis:** **ADR-007 (Chunking & Retrieval)** — struktur-bewusstes Chunking, Hybrid-Retrieval (Dense + Postgres-FTS, RRF), Schwellenwert-Gate, Grounding-Prompt-Kontrakt; Werte als Spike-Hypothesen; eröffnet ADR-008.

**Frank:** Bitte ADR-008 erstellen.

**Ergebnis:** **ADR-008 (Konfidenz- & Unterdrückungspipeline)** — mehrstufige, fail-closed Defense-in-Depth (Stufen 0–3), provider-portabel (keine Logprobs), 3-Band-Anzeige für US-02.

**Frank:** Ein ADR für die Eval-Strategie erstellen.

**Ergebnis:** **ADR-009 (Eval-Strategie)** — Gold-Dataset (In-/Out-of-Corpus/Adversarial), RAGAS + Custom-Gates, CI-Regressionsgate (Build bricht bei Halluzination > 0 %), Produktions-Monitoring; statistische Ehrlichkeit (0 % nur demonstrierbar).

---

## 10. C4-Dokumente synchronisieren

**Frank:** Aktualisiere die beiden C4-Dokumente.

**Ergebnis:**
- **C4-C1 (System-Context):** „OpenAI API" → Azure OpenAI EU; Quellen erweitert.
- **C4-C2 (Container):** Python 3.12→3.13, PostgreSQL 16→17, Provider→Azure EU; Volltext-Index ergänzt; RAG-Flow auf Hybrid-Retrieval + Konfidenz-Stufen (ADR-007/008); Chunking-Strategie konkretisiert; Pfade entstaltet; Stand v3.

---

## 11. Review-Dokument aktualisieren

**Frank:** Aktualisiere `04_ADR-Review_Kritik.md` auf Basis der 9 ADRs.

**Ergebnis:** Review neu aufgesetzt (ADR-001–009): erledigte Punkte markiert, echte Restlücken erhalten (LangChain-Entscheidung, `bytea`/`lo`, Kostenschätzung, Rate-Limiting, Datenmodell/OpenAPI, Autovacuum), Bewertung der neuen ADRs 007–009, aktualisierte Risiken und Zusammenfassungstabelle.

---

## 12. Architecture Draft

**Frank:** Erstelle aus den 9 ADRs einen strukturierten Architecture Draft (neue md-Datei) mit Anhang: Was ist unklar/widersprüchlich? Was sind die wichtigsten offenen Fragen?

**Ergebnis:** `06_Architecture-Draft.md` — konsolidiertes Architekturbild (Kontext, Stil, Stack, Komponenten, Datenarchitektur, RAG-Pipeline, LLM/Embedding, Worker, Querschnitt, ADR-Index) + **Anhang A** (Unklar/Widersprüchlich, inkl. Streaming-↔-Grounding-Konflikt) + **Anhang B** (priorisierte offene Fragen: vor dem Code / im Spike / vor MVP).

---

## 13. Architecture Pitch (HTML)

**Frank:** Erstelle zusätzlich einen Architecture Pitch als HTML-Datei (5 Minuten), ohne Countdown.

**Ergebnis:** `07_Architecture-Pitch.html` — eigenständiges Slide-Deck mit Tastatur-Navigation und Fortschrittsanzeige.

**Frank:** [Detail-Feedback pro Slide]

**Ergebnis:** Überarbeitet — 11 Slides: ADR-Übersicht statt Kontext; North-Star-Slide entfernt; Monolith ohne Microservices-Verweis; „warum Python" statt Versionsphilosophie; PostgreSQL im Titel; Reliability-Slide entmarketingt; pgqueuer erklärt; Eval verständlicher; Schluss-Slide mit neuer Überschrift und „wartbar & umkehrbar" statt „gebaut für KI-Implementierung".

---

## Resultierende Artefakte (`Frank/Modul3Tag2/`)

| Datei | Inhalt |
|---|---|
| `04_ADR-001_Architekturstil.md` | Modularer Monolith |
| `04_ADR-002_Backend-Frontend-Stack.md` | Python 3.13/FastAPI + React 18/TS (überarbeitet) |
| `04_ADR-003_Datenpersistenz.md` | PostgreSQL 17 + pgvector (überarbeitet) |
| `04_ADR-004_LLM-Provider.md` | Azure OpenAI EU + LiteLLM (überarbeitet) |
| `04_ADR-005_Embedding-Modell.md` | Embedding konfigurierbar (überarbeitet) |
| `04_ADR-006_Background-Worker.md` | pgqueuer (überarbeitet) |
| `04_ADR-007_Chunking-Retrieval.md` | **neu** — Chunking & Hybrid-Retrieval |
| `04_ADR-008_Konfidenz-Pipeline.md` | **neu** — Konfidenz-/Antwortprüfung |
| `04_ADR-009_Eval-Strategie.md` | **neu** — Eval-Strategie |
| `04_ADR-Review_Kritik.md` | Review aktualisiert (ADR-001–009) |
| `05_C4-C1_System-Context.md` | synchronisiert |
| `05_C4-C2_Container.md` | synchronisiert (v3) |
| `06_Architecture-Draft.md` | **neu** — konsolidiertes Architekturbild + Anhang |
| `07_Architecture-Pitch.html` | **neu** — 11-Slide-Pitch |
| `08_Konversation_Architektur-Review.md` | dieses Protokoll |

---

## Wichtigste offene Punkte (Stand 2026-05-31)

1. Gold-Eval-Dataset mit dem Fachbereich aufbauen (vor Spike-Kalibrierung).
2. Datenmodell + OpenAPI-Kontrakt spezifizieren (vor dem ersten Code).
3. `bytea` vs. `lo` entscheiden (vor Schema-Erstellung).
4. Streaming ↔ Grounding-Check architektonisch auflösen (Performance-NFA vs. fail-closed).
5. RAG-Parameter und Produktions-Embedding-Modell im Spike kalibrieren.
6. Auth-Rollenmodell, Bulk-Upload-Rate-Limiting, Quiz-Generierung, Secrets, LangChain-Frage, Kostenschätzung.

---

*Protokoll-Ende.*
