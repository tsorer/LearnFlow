# ADR-002: Backend/Frontend-Stack — FastAPI + React (TypeScript)

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

Die RAG-Pipeline erzeugt Antworten token-by-token über einen LLM — eine batch-Response würde für Lara träge wirken und die Performance-NFA (≤ 10 s @ p95 wahrgenommene Wartezeit) gefährden. Das Backend muss deshalb async Streaming via Server-Sent Events (SSE) nativ unterstützen. Gleichzeitig zieht die gesamte RAG-Implementierung (Chunking, Embedding, Retrieval, Prompt-Engineering, LiteLLM) das Python-Ökosystem nach sich — ein Backend in einer anderen Sprache würde dieses Ökosystem über einen Adapter-Layer verfügbar machen und Budget verbrennen.

---

## Entscheidung

Wir verwenden **Python 3.12 / FastAPI** als Backend und **React 18 (TypeScript 5)** als Frontend.

- FastAPI ist async-native (ASGI) und unterstützt SSE/StreamingResponse ohne zusätzliche Libraries.
- React's native `EventSource`-API konsumiert den SSE-Stream ohne Framework-Overhead.
- Beide Technologien sind im Team bekannt — keine Lernkurve auf der Haupt-Entwicklungsachse.

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
- **−** FastAPI `BackgroundTasks` sind nicht persistent — bei Container-Neustart gehen laufende Dokument-Verarbeitungs-Jobs verloren. Mitigation: Celery + Redis für den Dokument-Processing-Workflow (US-04, 5-Minuten-SLA).

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Node.js / Express + Next.js** | LangChain.js ist weniger reif als LangChain-Python; das Python-ML-Ökosystem ist nicht vollwertig portierbar. Hätte einen Python-Sidecar-Service für Embeddings/Retrieval erfordert — mehr Komplexität, nicht weniger. |
| **FastAPI + HTMX (kein React)** | Eliminiert die TypeScript-Toolchain; einfacheres SSR-Deployment. Gegenargument: SSE-Streaming ist mit HTMX umständlicher; interaktive Komponenten (Feedback-UI, Quellenhervorhebung, Quiz) sind mit React deutlich einfacher. Bleibt valide als Vereinfachung falls das Frontend-Budget knapp wird. |
| **Django (REST Framework)** | Schwergewichtiger als FastAPI; ASGI-Streaming ist nachträglich integriert, nicht nativ. Keine Vorteile gegenüber FastAPI für diesen Use Case. |

---

*Abhängigkeiten: ADR-001 (Modularer Monolith) · Nächste ADRs: ADR-003 (Persistenz), ADR-004 (LLM), ADR-005 (Embedding)*
