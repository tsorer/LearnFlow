Hier ist unser Architecture Draft:

- C2 Container Diagram: Docs/06_Architecture-Draft.md (Abschnitt "C2: Container-Entscheidungen")
- ADR-001 (Architekturstil — Modularer Monolith): Docs/04_ADR-001_Architekturstil.md
- ADR-002 (Backend/Frontend-Stack — FastAPI + React): Docs/04_ADR-002_Backend-Frontend-Stack.md
- ADR-003 bis ADR-009: Docs/04_ADR-003_Datenpersistenz.md ff.
- Pattern-Entscheidungen aus Ü3: [EINFÜGEN nach Ü3]

Prüfe auf Konsistenz:

1. Stimmen ADRs mit dem C2-Diagram überein?
2. Gibt es Widersprüche zwischen den Entscheidungen?
3. Passen die gewählten Patterns zu unserem Team (3 Devs, 3 Monate, ~360 h, Deadline 30. September 2026)?
4. Was passt zusammen — was beisst sich?

---

# Output

*Konsistenzprüfung auf Basis von `Docs/` (ADR-001 bis ADR-009, `05_C4-C2_Container.md`, `06_Architecture-Draft.md`) · Stand: 2026-05-31*

> Vorab: Die Zeile **„Pattern-Entscheidungen aus Ü3: [EINFÜGEN nach Ü3]"** ist noch ein Platzhalter — die konkreten Pattern-Entscheide liegen nicht vor. Frage 3 ist daher auf Basis der *Architektur*-Entscheidungen beantwortet; die Pattern-Ebene muss nachgereicht werden.

## 1. Stimmen ADRs mit dem C2-Diagramm überein?

**Überwiegend ja.** Übereinstimmend: Stack-Versionen (Python 3.13, React 18, PostgreSQL 17), pgqueuer-Worker, LiteLLM mit MVP-/Prod-Provider-Staffelung, Embeddings, DB als Single-Service mit HNSW + `tsvector`/GIN + `bytea`, RAG-Flow mit Hybrid-Retrieval/RRF und Konfidenz-Stufen. Drei **Abweichungen**:

- ⚠️ **Reliability-Beschreibung veraltet:** C2 (Abschnitt 1.2) und der Draft beschreiben die Pipeline als *„Quellenprüfung → Konfidenz-Score → Self-Check"* (3 Stufen). ADR-008 definiert aber **4 Stufen** (Retrieval-Gate → Retrieval-Konfidenz → Grounding-/Citation-Check → LLM-Self-Check). Begriffs-Drift.
- ⚠️ **RBAC-Rollen widersprüchlich:** Der Draft nennt „RBAC (User / Admin)" — **zwei** Rollen. Das C2-Diagramm zeigt aber **drei** Personas (Lara = Lernende, Stefan = Bereichsverantwortlicher/Upload, Admin). Stefan ist weder „User" noch „Admin" sauber zugeordnet. Das Rollenmodell ist faktisch undefiniert.
- ⚠️ **Circuit Breaker** für LiteLLM steht im C2/Draft, ist aber in keinem ADR entschieden (ADR-004 nennt nur Fallback). Kleine Nachverfolgbarkeits-Lücke.

## 2. Widersprüche zwischen den Entscheidungen?

- ✅ **Aufgelöst:** Der alte Konflikt ADR-001 (Monolith) ↔ ADR-002 (Celery+Redis) ist durch ADR-006 (pgqueuer) sauber geschlossen; ADR-002 referenziert das jetzt korrekt.
- 🔴 **Streaming ↔ Grounding-Check:** ADR-008 ist *fail-closed* (Antwort erst prüfen, dann ausliefern), ADR-002/Performance-NFA will *Token-by-Token-Streaming*. Beides gleichzeitig ist nicht trivial — im Draft als offen markiert, aber **architektonisch noch nicht entschieden**.
- 🔴 **Max. Upload-Größe inkonsistent:** C2-Upload-Flow nennt **„≤ 50 Seiten / 10 MB"** für das 5-Min-SLA, ADR-003 argumentiert in der `bytea`-Konsequenz mit **„PDFs bis 100 MB"**. Es fehlt eine *eine* verbindliche Obergrenze.
- 🟠 **ADR-001-Status:** Im Draft „**Accepted** (nach Peer Review)", in der ADR-Datei selbst aber „**Proposed**". Statuskonflikt.
- ✅ **MVP-Provider-Prämisse:** über ADR-004/005, C1/C2 und Draft konsistent.

## 3. Passen die Patterns/Architektur zum Team (3 Devs, ~360 h, Deadline 30.09.2026)?

Heute ist 2026-05-31 → ~4 Monate Kalenderzeit, 3 Monate MVP-Plan. **Die Architektur ist angemessen schlank**, aber die Reliability-Maschinerie ist der Budget-Treiber:

- ✅ **Gut dimensioniert:** Modularer Monolith + Docker Compose + ein PostgreSQL + pgqueuer — minimaler Ops-Overhead, passt zu 3 Devs/360 h. KI-Implementierung (Claude Code) stützt das zusätzlich.
- 🟠 **Budget-Risiko #1 — Reliability + Eval:** Hybrid-Retrieval + RRF + 4-stufige Konfidenzpipeline (ADR-007/008) + Gold-Dataset + RAGAS + CI-Gate (ADR-009) sind zusammen *erheblicher* Aufwand und hängen am fachlich erstellten Gold-Dataset (externe Abhängigkeit zu Stefan).
- 🟠 **Budget-Risiko #2 — Frontend:** React-SPA mit SSE + Quellen-Highlighting + Quiz-UI bei effektiv ≤ 1 Frontend-Person; der Draft flaggt PDF-Highlighting selbst mit „+2–3 Wochen".
- 🟢 **Zwei Sprachen** (Python + TS): zwei Toolchains für 3 Devs — vertretbar, in ADR-002 bewusst akzeptiert.

Fazit: Die *Patterns der Architektur* passen; das Risiko ist nicht die Struktur, sondern der **Scope der RAG-Qualitätssicherung** gegen die Deadline.

## 4. Was passt zusammen — was beisst sich?

**Passt zusammen (kohärenter Kern):** Monolith → pgqueuer → ein PostgreSQL → Docker Compose → LiteLLM-Portabilität → `config`-Tabelle für Tuning → KI-bewusste Stack-Wahl (stabile, dichte APIs). Diese Kette ist in sich stimmig und budgetbewusst.

**Beisst sich (zu klären):**

| # | Konflikt | Schwere |
|---|---|---|
| 1 | Streaming (Performance) ↔ Grounding-Check vor Auslieferung (fail-closed) | 🔴 |
| 2 | Max. Upload: 10 MB (C2) vs. 100 MB (ADR-003) | 🔴 |
| 3 | RBAC 2 Rollen (Draft) vs. 3 Personas (C2) | 🟠 |
| 4 | ADR-001 Status: Accepted (Draft) vs. Proposed (ADR) | 🟠 |
| 5 | Pipeline-Stufen: 3 (C2/Draft-Text) vs. 4 (ADR-008) | 🟠 |
| 6 | Circuit Breaker im C2, in keinem ADR entschieden | 🟢 |
| 7 | Ü3-Pattern-Platzhalter unausgefüllt → Frage 3 nur teilbeantwortbar | 🟢 |

Die ersten fünf sind konkret behebbar: Pipeline-Beschreibung auf die 4 ADR-008-Stufen vereinheitlichen (1, 5), verbindliche Upload-Obergrenze festlegen (2), Rollenmodell auf 3 Rollen schärfen (3), ADR-001-Status angleichen (4). Bei (2) und (3) ist je eine Entscheidung nötig (Obergrenze; eigene Rolle für Stefan).
