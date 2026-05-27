# ADR-002: Backend/Frontend-Stack — FastAPI + React (TypeScript)

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

Die RAG-Pipeline erzeugt Antworten token-by-token über einen LLM — eine batch-Response würde für Lara träge wirken und die Performance-NFA (≤ 10 s @ p95 wahrgenommene Wartezeit) gefährden. Das Backend muss deshalb async Streaming via Server-Sent Events (SSE) nativ unterstützen. Gleichzeitig zieht die gesamte RAG-Implementierung (Chunking, Embedding, Retrieval, Prompt-Engineering, LiteLLM) das Python-Ökosystem nach sich — ein Backend in einer anderen Sprache würde dieses Ökosystem über einen Adapter-Layer verfügbar machen und Budget verbrennen.

**Implementierungsmodell:** Der Code wird überwiegend KI-gestützt mit **Claude Code** erzeugt; die Teammitglieder agieren primär als Reviewer und Verifizierer, nicht als Autoren. Das verschiebt die Gewichtung der Frontend-Kriterien: Team-Vertrautheit und Schreibaufwand (Boilerplate) verlieren an Bedeutung, während **Trainingsdaten-Dichte** (→ Zuverlässigkeit der Generierung, geringe Halluzinationsrate bei stabilen APIs) und **statische Typisierung als Review-Netz** für KI-generierten Code an Bedeutung gewinnen.

---

## Entscheidung

Wir verwenden **Python 3.13 / FastAPI** als Backend und **React 18 (TypeScript 5)** als Frontend.

- FastAPI ist async-native (ASGI) und unterstützt SSE/StreamingResponse ohne zusätzliche Libraries.
- React's native `EventSource`-API konsumiert den SSE-Stream ohne Framework-Overhead.
- **React als Frontend (KI-Implementierungs-bewusst):** Da der Code mit Claude Code generiert wird, wiegt nicht Team-Vertrautheit, sondern (1) die **höchste Trainingsdaten-Dichte** aller UI-Frameworks → zuverlässigste, idiomatischste Generierung und geringste Rate halluzinierter/veralteter APIs; (2) **TypeScript als Compile-Zeit-Netz**, das genau die Fehlerklasse KI-generierten Codes (falsche Props, erfundene Signaturen) beim menschlichen Review abfängt; (3) das **grösste Komponenten-Ökosystem** für die konkreten Anforderungen (Markdown-/Quellen-Highlighting, Feedback-UI, Quiz). Reacts klassischer Nachteil (Boilerplate) ist neutralisiert, weil die KI ihn schreibt.
- **React 18** (statt einer neueren Major-Version): gleiches Reife-/Halluzinations-Argument wie bei Python — stabile, dicht dokumentierte APIs liefern verlässlicheren KI-Output als bleeding-edge-Versionen.
- **Python 3.13** (statt der neuesten 3.14): zum Entscheidungszeitpunkt seit ~1,5 Jahren stabil, daher voller Wheel-/Ökosystem-Support für die ML-Abhängigkeiten (PyTorch, sentence-transformers), die neuen Releases erfahrungsgemäss Monate hinterherhinken. Gleichzeitig bringt 3.13 die verbesserte asyncio-/Tooling-Basis mit, die zum async-SSE-Profil passt — ohne das bleeding-edge-Risiko von 3.14.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Python-Ökosystem für RAG direkt verfügbar: LangChain, LiteLLM, sentence-transformers, pypdf, python-docx — kein Adapter-Layer.
- **+** SSE-Streaming mit FastAPI `StreamingResponse` ist wenige Zeilen Code; React `EventSource` ist ein Web-Standard ohne externe Dependency.
- **+** TypeScript im Frontend fängt Typ-Fehler zur Compile-Zeit ab — bei einem kleinen Team ohne dedizierte QA besonders wertvoll.
- **+** Vite als Build-Tool: schnelle HMR-Entwicklungsschleife, minimaler Konfigurationsaufwand gegenüber Webpack.

### Negative Konsequenzen

- **−** Zwei Sprachen (Python + TypeScript) im selben Repo erfordern zwei separate Dependency-Verwaltungen (pip/uv + npm) und zwei Linting-Konfigurationen.
- **−** Python-Dependencies ziehen grosse Docker-Images nach sich: PyTorch (für lokale Embeddings) kann 1–2 GB zum Image beitragen. Mitigation: schlankes Base-Image, optionale Embedding-Dependencies nur wenn nötig (→ ADR-005).
- **−** FastAPI `BackgroundTasks` sind nicht persistent — bei Container-Neustart gehen laufende Dokument-Verarbeitungs-Jobs verloren. Mitigation: pgqueuer (PostgreSQL-nativer Job-Queue) für den Dokument-Processing-Workflow (US-04, 5-Minuten-SLA) — entschieden in ADR-006.

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Node.js / Express + Next.js** | LangChain.js ist weniger reif als LangChain-Python; das Python-ML-Ökosystem ist nicht vollwertig portierbar. Hätte einen Python-Sidecar-Service für Embeddings/Retrieval erfordert — mehr Komplexität, nicht weniger. |
| **Vue 3 + TypeScript** | Sanftere Lernkurve als React und gleichwertig bei SSE/Highlighting — dieser Vorteil zählt im KI-Implementierungsmodell jedoch kaum, da nicht der Mensch das Framework schreibt. Demgegenüber geringere Trainingsdaten-Dichte als React → tendenziell höhere Halluzinationsrate bei der Generierung. Bei vergleichbarer Eignung gibt das Ökosystem den Ausschlag für React. |
| **Svelte / SvelteKit** | Am wenigsten Boilerplate — der Hauptvorteil entfällt aber, wenn die KI den Code schreibt. Kleineres Ökosystem und schneller bewegte APIs (Runes) erhöhen die Halluzinations-/Veraltungsrate des KI-Outputs. Verworfen. |
| **FastAPI + HTMX (kein React)** | Einzige verbleibende ernsthafte Gegenoption — aber aus Architektur-, nicht Aufwandsgründen: weniger *System*komplexität (kein Build-Step, eine Sprache, kein zweiter Dependency-Baum). Verworfen, weil die untypisierte Vorlage das TypeScript-Review-Netz für KI-Code aufgibt und komplexe Interaktion (Inline-Quellen-Highlighting, Quiz) umständlicher wird. Bleibt valide als Vereinfachung, falls das Frontend-Budget knapp wird. |
| **Django (REST Framework)** | Schwergewichtiger als FastAPI; ASGI-Streaming ist nachträglich integriert, nicht nativ. Keine Vorteile gegenüber FastAPI für diesen Use Case. |
| **Python 3.14 (neueste)** | Verworfen zugunsten 3.13: ML-Wheels (PyTorch, sentence-transformers) hinken neuen Python-Releases nach → Risiko fehlender vorkompilierter Binaries und Build-Brüche im Spike. 3.13 bietet ausgereiften Ökosystem-Support plus die für SSE relevanten async-/Tooling-Verbesserungen ohne bleeding-edge-Risiko. 3.14 nur bei konkretem Feature-Bedarf. |

---

*Abhängigkeiten: ADR-001 (Modularer Monolith) · Nächste ADRs: ADR-003 (Persistenz), ADR-004 (LLM), ADR-005 (Embedding)*
