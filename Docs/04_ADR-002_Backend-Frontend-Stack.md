# ADR-002: Backend/Frontend-Stack — FastAPI + React (TypeScript)

| Feld          | Inhalt                                |
| ------------- | ------------------------------------- |
| **Status**    | Accepted                              |
| **Datum**     | 2026-05-27 · aktualisiert 2026-06-03  |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

Die RAG-Pipeline durchläuft vor der Antwort mehrere Stufen (Retrieval → Konfidenz-Check → Grounding-Prüfung → optionaler Self-Check, ADR-008). Da ADR-008 fail-closed und sequenziell aufgebaut ist, muss die vollständige Prüfung abgeschlossen sein, bevor eine Antwort ausgeliefert werden kann. Token-by-Token-Streaming (SSE) widerspricht diesem Prinzip — man kann nicht streamen, bevor der Grounding-Check die Antwort freigegeben hat. Wir haben uns deshalb bewusst für **Batch-Response (JSON)** entschieden: die vollständige, geprüfte Antwort wird als einzelne HTTP-Response zurückgegeben. Die Performance-NFA (≤ 10 s @ p95) wird über Retrieval-Optimierung (ADR-007) und Ladeanimation im Frontend eingehalten, nicht über Streaming.

Gleichzeitig zieht die gesamte RAG-Implementierung (Chunking, Embedding, Retrieval, Prompt-Engineering, LiteLLM) das Python-Ökosystem nach sich — ein Backend in einer anderen Sprache würde dieses Ökosystem über einen Adapter-Layer verfügbar machen und Budget verbrennen.

**Implementierungsmodell:** Der Code wird überwiegend KI-gestützt mit **Claude Code** erzeugt; die Teammitglieder agieren primär als Reviewer und Verifizierer, nicht als Autoren. Das verschiebt die Gewichtung der Frontend-Kriterien: Team-Vertrautheit und Schreibaufwand (Boilerplate) verlieren an Bedeutung, während **Trainingsdaten-Dichte** (→ Zuverlässigkeit der Generierung, geringe Halluzinationsrate bei stabilen APIs) und **statische Typisierung als Review-Netz** für KI-generierten Code an Bedeutung gewinnen.

---

## Entscheidung

Wir verwenden **Python 3.13 / FastAPI** als Backend und **React 18 (TypeScript 5)** als Frontend.

- FastAPI ist async-native (ASGI) und verarbeitet die mehrstufige RAG-Pipeline (ADR-008) non-blocking — kein Thread-Blocking während LLM-Aufruf und Konfidenz-Checks.
- Die Antwort wird als **einzelne JSON-Response** zurückgegeben (kein SSE). Das Frontend zeigt während der Verarbeitung eine Ladeanimation.
- **React als Frontend (KI-Implementierungs-bewusst):** Da der Code mit Claude Code generiert wird, wiegt nicht Team-Vertrautheit, sondern (1) die **höchste Trainingsdaten-Dichte** aller UI-Frameworks → zuverlässigste, idiomatischste Generierung und geringste Rate halluzinierter/veralteter APIs; (2) **TypeScript als Compile-Zeit-Netz**, das genau die Fehlerklasse KI-generierten Codes (falsche Props, erfundene Signaturen) beim menschlichen Review abfängt; (3) das **grösste Komponenten-Ökosystem** für die konkreten Anforderungen (Markdown-/Quellen-Highlighting, Feedback-UI, Quiz). Reacts klassischer Nachteil (Boilerplate) ist neutralisiert, weil die KI ihn schreibt.
- **React 18** (statt einer neueren Major-Version): gleiches Reife-/Halluzinations-Argument wie bei Python — stabile, dicht dokumentierte APIs liefern verlässlicheren KI-Output als bleeding-edge-Versionen.
- **JWT-Storage ausschliesslich im React-State (In-Memory):** Der JWT wird nie in `localStorage` oder `sessionStorage` abgelegt. Grund: Die Plattform verarbeitet interne Unternehmensdokumente — ein XSS-Angriff darf keinen persistierten Token auslesen können. Konsequenz: Nach einem Browser-Refresh muss sich der Nutzer neu einloggen (akzeptiert für MVP).
- **Routing via `react-router-dom`:** Geschützte Ansichten sind als echte Routen umgesetzt; nicht authentifizierter Zugriff wird per `<Navigate>` URL-basiert auf `/login` umgeleitet (Protected Routes, US-05).
- **Python 3.13** (statt der neuesten 3.14): zum Entscheidungszeitpunkt seit ~1,5 Jahren stabil, daher voller Wheel-/Ökosystem-Support für die ML-Abhängigkeiten (PyTorch, sentence-transformers), die neuen Releases erfahrungsgemäss Monate hinterherhinken. Gleichzeitig bringt 3.13 die verbesserte asyncio-/Tooling-Basis mit, die zum async-Batch-Response-Profil passt — ohne das bleeding-edge-Risiko von 3.14.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Python-Ökosystem für RAG direkt verfügbar: LangChain, LiteLLM, sentence-transformers, pypdf, python-docx — kein Adapter-Layer.
- **+** Batch-Response löst den Streaming-vs.-Fail-Closed-Konflikt (ADR-008) vollständig: Konfidenz-Check, Grounding-Prüfung und Self-Check sind abgeschlossen, bevor die Antwort das Backend verlässt.
- **+** Einfachere Frontend-Integration: Standard `fetch()` statt `EventSource` — kein SSE-State-Management, kein Reconnect-Handling.
- **+** TypeScript im Frontend fängt Typ-Fehler zur Compile-Zeit ab — bei einem kleinen Team ohne dedizierte QA besonders wertvoll.
- **+** Vite als Build-Tool: schnelle HMR-Entwicklungsschleife, minimaler Konfigurationsaufwand gegenüber Webpack.

### Negative Konsequenzen

- **−** Zwei Sprachen (Python + TypeScript) im selben Repo erfordern zwei separate Dependency-Verwaltungen (pip/uv + npm) und zwei Linting-Konfigurationen.
- **−** Python-Dependencies ziehen grosse Docker-Images nach sich: PyTorch (für lokale Embeddings) kann 1–2 GB zum Image beitragen. Mitigation: schlankes Base-Image, optionale Embedding-Dependencies nur wenn nötig (→ ADR-005).
- **−** Batch-Response: Lara sieht nichts bis die vollständige Antwort fertig ist (kein inkrementelles Feedback). Mitigation: Ladeanimation + Fortschrittsindikator im Frontend; Performance-NFA (≤ 10 s p95) muss über Retrieval-Optimierung eingehalten werden.
- **−** FastAPI `BackgroundTasks` sind nicht persistent — bei Container-Neustart gehen laufende Dokument-Verarbeitungs-Jobs verloren. Mitigation: pgqueuer (PostgreSQL-nativer Job-Queue) für den Dokument-Processing-Workflow (US-04, 5-Minuten-SLA) — entschieden in ADR-006.

---

## Abgewogene Alternativen

| Alternative                        | Warum verworfen                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Node.js / Express + Next.js**    | LangChain.js ist weniger reif als LangChain-Python; das Python-ML-Ökosystem ist nicht vollwertig portierbar. Hätte einen Python-Sidecar-Service für Embeddings/Retrieval erfordert — mehr Komplexität, nicht weniger.                                                                                                                                                                                                                  |
| **Vue 3 + TypeScript**             | Sanftere Lernkurve als React und gleichwertig bei SSE/Highlighting — dieser Vorteil zählt im KI-Implementierungsmodell jedoch kaum, da nicht der Mensch das Framework schreibt. Demgegenüber geringere Trainingsdaten-Dichte als React → tendenziell höhere Halluzinationsrate bei der Generierung. Bei vergleichbarer Eignung gibt das Ökosystem den Ausschlag für React.                                                             |
| **Svelte / SvelteKit**             | Am wenigsten Boilerplate — der Hauptvorteil entfällt aber, wenn die KI den Code schreibt. Kleineres Ökosystem und schneller bewegte APIs (Runes) erhöhen die Halluzinations-/Veraltungsrate des KI-Outputs. Verworfen.                                                                                                                                                                                                                 |
| **FastAPI + HTMX (kein React)**    | Einzige verbleibende ernsthafte Gegenoption — aber aus Architektur-, nicht Aufwandsgründen: weniger *System*komplexität (kein Build-Step, eine Sprache, kein zweiter Dependency-Baum). Verworfen, weil die untypisierte Vorlage das TypeScript-Review-Netz für KI-Code aufgibt und komplexe Interaktion (Inline-Quellen-Highlighting, Quiz) umständlicher wird. Bleibt valide als Vereinfachung, falls das Frontend-Budget knapp wird. |
| **Django (REST Framework)**        | Schwergewichtiger als FastAPI; ASGI-Streaming ist nachträglich integriert, nicht nativ. Keine Vorteile gegenüber FastAPI für diesen Use Case.                                                                                                                                                                                                                                                                                          |
| **SSE-Streaming (Token-by-Token)** | Bewusst verworfen (2026-06-03): Streaming ist mit ADR-008 Fail-Closed unvereinbar — man kann nicht streamen, bevor Grounding-Check und Self-Check abgeschlossen sind. Batch-Response ist die konsequente Wahl.                                                                                                                                                                                                                         |
| **Python 3.14 (neueste)**          | Verworfen zugunsten 3.13: ML-Wheels (PyTorch, sentence-transformers) hinken neuen Python-Releases nach → Risiko fehlender vorkompilierter Binaries und Build-Brüche im Spike. 3.13 bietet ausgereiften Ökosystem-Support und async-/Tooling-Verbesserungen ohne bleeding-edge-Risiko. 3.14 nur bei konkretem Feature-Bedarf.                                                                                                           |

---

*Abhängigkeiten: ADR-001 (Modularer Monolith) · Nächste ADRs: ADR-003 (Persistenz), ADR-004 (LLM), ADR-005 (Embedding)*
