# Lab L1 Teil 1 · Konsistenz-Check Architecture Draft

*LearnFlow · Modul 3 Tag 2 · Reto Stucki · 2026-06-03*
*Quellen: Docs/06_Architecture-Draft.md · Docs/04_ADR-001 bis ADR-010 · Docs/03_QualityAttributes.md*

---

## 1. Stimmen ADRs mit dem C2-Diagram überein?

**Mehrheitlich ja — mit zwei Ausnahmen:**

| ADR                           | C2-Eintrag                                                                                                                          | Konsistenz   |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| ADR-001 Modularer Monolith    | 4 Container in einem Stack, ein docker compose — ✅                                                                                  | ✅ Konsistent |
| ADR-002 FastAPI + React       | API Server (FastAPI/ASGI) + Web App (React 18/TS/Vite/Nginx) — ✅                                                                    | ✅ Konsistent |
| ADR-003 PostgreSQL + pgvector | Datenbank-Container: PostgreSQL 17 + pgvector — ✅                                                                                   | ✅ Konsistent |
| ADR-006 pgqueuer              | Background Worker (pgqueuer) — ✅                                                                                                    | ✅ Konsistent |
| ADR-004 LiteLLM               | API Server → Azure OpenAI EU via LiteLLM — ✅                                                                                        | ✅ Konsistent |
| ADR-010 API-First             | **Kein Eintrag im C2** — OpenAPI Spec als Artefakt fehlt im Diagram                                                                 | ⚠️ Lücke     |
| ADR-008 Konfidenz-Pipeline    | C2 nennt «Konfidenz-Scoring konzeptionell noch undefiniert» — ADR existiert, aber als «Proposed» ohne finale Mechanismus-Definition | ⚠️ Offen     |

---

## 2. Gibt es Widersprüche zwischen den Entscheidungen?

**Drei Spannungsfelder:**

**① SSE-Streaming vs. Fail-Closed (ADR-002 vs. ADR-008)**
ADR-002 entscheidet sich für Token-by-Token-Streaming wegen der ≤ 10 s-NFA. ADR-008 (Reliability) verlangt Fail-Closed: keine Antwort ohne valide Quellenprüfung. Das ist ein echtes Architekturproblem — wenn wir streamen, haben wir den Grounding-Check noch nicht abgeschlossen. Architecture-Draft nennt es als offene Frage. Muss vor Sprint 1 gelöst werden.

**② pgqueuer Single-Threaded vs. Parallele Uploads (ADR-006 vs. US-04)**
ADR-006 nennt «Single-Threaded: parallele Uploads stauen Queue» als grösstes Risiko. US-04 verlangt ≤ 5 Min für Dokumente ≤ 50 Seiten. Bei gleichzeitigen Uploads von mehreren Dokumenten wird diese SLA brechen. Für < 30 Pilotnutzer wahrscheinlich tolerierbar — aber nicht getestet.

**③ API-First (ADR-010) vs. FastAPI Auto-Spec (ADR-002)**
FastAPI generiert per Default eine OpenAPI Spec aus dem Code. ADR-010 setzt Spec-First voraus — das bedeutet, die Auto-Generierung muss bewusst deaktiviert oder ignoriert werden. Im Team muss klar sein: die `openapi.yaml` im Repo ist der Vertrag, nicht `/docs` in FastAPI.

---

## 3. Passen die Patterns zu unserem Team (3 Devs, 3 Monate, ~360 h)?

| Pattern / Entscheid                      | Fit? | Kommentar                                                                                                                                                            |
| ---------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Modularer Monolith (ADR-001)             | ✅    | Richtig für die Teamgrösse. Risiko: Modul-Grenzen ohne CI-Gate.                                                                                                      |
| API-First mit OpenAPI (ADR-010)          | ✅    | Erhöht Parallelisierung — kostet ~5–10 h für Spec-Erstellung, spart mehr durch parallele Entwicklung.                                                                |
| pgqueuer statt Celery+Redis (ADR-006)    | ✅    | Richtige Vereinfachung. Bewusst pragmatisch.                                                                                                                         |
| Hybrid-Retrieval + RRF (ADR-007)         | ⚠️   | Konzeptionell stark, aber die Parameter (Chunk-Grösse, k, Schwellenwerte) müssen im Tech Spike kalibriert werden — ohne das ist die gesamte RAG-Qualität unbekannt.  |
| Mehrstufige Konfidenz-Pipeline (ADR-008) | ⚠️   | Noch zu komplex und zu wenig definiert für Sprint 1. Mechanismus (Self-Check via LLM oder Embedding-Similarity?) ist offen. Das ist der grösste inhaltliche Blocker. |
| 9 ADRs + Eval-Strategie (ADR-009)        | ⚠️   | Architektonisch vollständig — aber das Scope-Risiko ist real. 360 h für Modularer Monolith + RAG + Eval + Quiz + Admin ist ambitioniert.                             |

---

## 4. Was passt zusammen — was beisst sich?

**Passt gut zusammen:**

- ADR-001 (Modularer Monolith) + ADR-006 (pgqueuer) + ADR-003 (PostgreSQL): ein Stack, ein Backup, ein docker compose — maximale Einfachheit für das Budget.
- ADR-002 (FastAPI/React) + ADR-010 (API-First): SSE-native Stack + OpenAPI Spec als Kontrakt — ermöglicht Frontend/Backend parallel. Starke Kombination.
- ADR-004 (LiteLLM) + ADR-005 (Embedding-Modell): Provider-Wechsel per Konfiguration — direkt aus Maintainability-NFA abgeleitet, sauber gelöst.

**Beisst sich:**

- **ADR-002 Streaming ↔ ADR-008 Fail-Closed** — Das grösste konzeptionelle Problem. Lösung vor Sprint 1 zwingend.
- **ADR-008 (Proposed, offen) ↔ Reliability als Top-1-NFA** — Der wichtigste Quality Attribute ist durch den noch undefinierten Mechanismus nicht abgesichert.
- **ADR-009 Eval-Strategie ↔ 360 h Budget** — Gold-Dataset + RAGAS + CI-Regressionsgate ist wertvoll aber aufwändig. Ohne Tech Spike weiss niemand, wie viele Stunden das kostet.

---

## Fazit: Was sind die gefundenen Widersprüche / Inkonsistenzen?

1. **Streaming vs. Fail-Closed** — offener Architekturkonflikt, Blocker für US-01 und US-02
2. **ADR-008 Konfidenz-Mechanismus undefiniert** — Top-1-NFA (Reliability) ist nicht abgesichert
3. **API-First nicht im C2 sichtbar** — openapi.yaml als zentrales Artefakt sollte im Architecture-Draft erwähnt sein
4. **pgqueuer Single-Threaded** — SLA-Risiko bei parallelen Uploads, noch nicht getestet
