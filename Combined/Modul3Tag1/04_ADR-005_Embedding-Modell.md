# ADR-005: Embedding-Modell — Konfigurierbar via LiteLLM (Azure OpenAI EU oder Ollama lokal)

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

Die RAG-Pipeline braucht Embeddings in zwei Phasen: beim Dokument-Upload (alle Chunks indexieren) und bei jeder Nutzeranfrage (Query-Embedding für Retrieval). Das Embedding-Modell bestimmt die Vektor-Dimension, die im pgvector-Schema fest verankert ist. Ein Modellwechsel erfordert eine vollständige Re-Indexierung aller Dokumente — das ist kein Blocker, sondern ein bewusst akzeptierter Betriebsvorgang. Verschiedene Installationen (Entwicklung, Produktion) können unterschiedliche Modelle und Dimensionen verwenden, weil sie separate Datenbanken haben. Kompatibilität zwischen Installationen ist kein Ziel.

**Datenschutz-Relevanz:** Beim Indexieren wird der *gesamte* Dokumentkorpus an den Embedding-Provider gesendet (jeder Chunk jedes internen Dokuments) — die datenintensivste Exposition der gesamten Pipeline. Der Produktiv-Default muss daher derselben EU-/Compliance-Linie folgen wie der LLM-Provider in ADR-004.

Das Projekt braucht zwei lauffähige Szenarien:
1. **Produktion / Standard**: Azure OpenAI EU — hohe Qualität bei garantierter EU-Datenresidenz.
2. **Lokal / Datenschutz**: Ollama — keine API-Kosten, kein Datentransfer, offline-fähig.

---

## Entscheidung

Wir verwenden **LiteLLM als Abstraktions-Layer für Embeddings** — identisch zum LLM-Muster aus ADR-004. Modell, Provider und Dimension sind Konfigurationsparameter. Kein Code-Change bei einem Modell- oder Provider-Wechsel.

**Konfigurierte Standardwerte je Umgebung:**

| Umgebung | Provider | Modell | Dimension |
|---|---|---|---|
| Produktion / Standard | Azure OpenAI EU | `text-embedding-3-small` | 1536 |
| Entwicklung / Test (keine Produktivdaten) | OpenAI Direct | `text-embedding-3-small` | 1536 |
| Lokal / Datenschutz | Ollama | `bge-m3` | 1024 |

Die aktive Konfiguration (Modell-Name + Dimension) wird beim Start in der Datenbank persistiert. Bei einem Modellwechsel triggert ein Migrations-Script die vollständige Re-Indexierung aller Dokumente.

**Offen für den Tech-Spike (Sprint 0):** `text-embedding-3-small` ist als kosteneffizienter Standard gesetzt, aber für einen *deutschsprachigen Fachkorpus* nicht zwingend die qualitativ beste Wahl (das Modell ist englisch-optimiert). Vor Festlegung ist ein kurzer Retrieval-Eval auf echten Fachtexten vorgesehen — `text-embedding-3-small` vs. `text-embedding-3-large` vs. ein dediziert multilinguales Modell. Auffällig: das stärkste Deutsch-Modell (`bge-m3`) ist aktuell nur lokal vorgesehen, nicht in Produktion.

**Constraint (Kopplung an ADR-003):** pgvector indexiert HNSW nur bis **2000 Dimensionen**. Die gesetzten Werte (1536, 1024) sind unkritisch; ein Wechsel auf ein höherdimensionales Modell (z. B. `text-embedding-3-large`, 3072) erfordert Matryoshka-Reduktion auf ≤ 2000 oder den `halfvec`-Typ — sonst lässt sich der HNSW-Index nicht anlegen.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Dasselbe Abstraktionsmuster *und* dieselbe Provider-Linie wie ADR-004 (Azure OpenAI EU + LiteLLM): ein konsistentes Konfigurationsschema für alle KI-Komponenten — eine Provider-Anbindung, eine Kostenstelle für LLM und Embeddings, durchgängige EU-Datenresidenz.
- **+** Lokale Entwicklung funktioniert vollständig ohne Netzwerkzugang — `ollama pull bge-m3` genügt; kein API-Key nötig.
- **+** Kein PyTorch im Docker-Image des Backends: Ollama läuft als separater lokaler Prozess; das Backend ruft nur seine REST-API auf.
- **+** Provider-Wechsel (OpenAI → Ollama oder umgekehrt) ist ein Konfigurationseintrag, kein Code-Change und kein Deployment.
- **+** `bge-m3` (Ollama lokal) ist explizit multilingual trainiert — gut für deutschsprachige Fachtexte; deckt Datenschutz-Anforderungen ohne Cloud-Abhängigkeit ab.

### Negative Konsequenzen

- **−** Modellwechsel erfordert vollständige Re-Indexierung aller Dokumente (andere Dimension = Schema-Migration + alle Chunks neu generieren). Bewusst akzeptiert: betrifft eine geplante Betriebssituation, keinen Fehlerfall.
- **−** Dev- und Prod-Vektordatenbanken sind nicht kompatibel (unterschiedliche Dimensionen: 1536 vs. 1024). Bewusst akzeptiert: separate Installationen mit separaten Daten.
- **−** `bge-m3` (1024 Dim) hat geringere Qualität als `text-embedding-3-small` (1536 Dim) — Retrieval-Ergebnisse in der lokalen Entwicklung weichen von Produktion ab. Mitigation: Evaluations-Tests laufen immer gegen die Produktionskonfiguration (OpenAI).
- **−** Ollama muss auf dem Entwickler-Laptop installiert und das Modell heruntergeladen sein (~1.2 GB für `bge-m3`). Kein Blocker, aber Onboarding-Schritt mit Wartezeit beim ersten `ollama pull`.
- **−** Beim Indexieren gehen Dokumentinhalte an einen Cloud-Provider — über Azure OpenAI EU bleibt die Verarbeitung jedoch in europäischen Rechenzentren (kein Drittland-Transfer). Für Deployments, in denen Daten die eigene Infrastruktur gar nicht verlassen dürfen: auf Ollama (lokal) umstellen — eine Konfigurationszeile.

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Feste Dimension für alle Umgebungen** | Unnötige Einschränkung, da Installationen ohnehin nicht kompatibel sind und keine Vereinheitlichung brauchen. (Anmerkung: `text-embedding-3-small` unterstützt Matryoshka-Dimension-Reduktion nahezu verlustfrei, z. B. auf 1024 — eine Vereinheitlichung wäre also technisch günstig möglich, ist aber kein Ziel.) |
| **`text-embedding-3-large` (3072 Dim) in Produktion** | Deutlich höhere Retrieval-Qualität, insbesondere für deutschsprachige Fachtexte, ebenfalls auf Azure OpenAI EU verfügbar. **Offen für den Spike-Eval** (siehe Constraint unten) statt heute fix verworfen: höhere Kosten pro Token, und 3072 Dim überschreiten das HNSW-Indexlimit von pgvector (2000) — erfordert Matryoshka-Reduktion auf ≤ 2000 oder den `halfvec`-Typ. |
| **`nomic-embed-text` statt `bge-m3` (Ollama lokal)** | 274 MB statt 1.2 GB — deutlich schlanker. Verworfen wegen englisch-primärem Training: auf deutschsprachigen Fachtexten schlechtere Retrieval-Qualität als `bge-m3`. Valide Alternative falls Laptop-Ressourcen knapp sind. |
| **`sentence-transformers` direkt im Backend** | PyTorch-Dependency (+1.5 GB Docker-Image); kein Vorteil gegenüber Ollama (gleiche Modelle verfügbar, aber Ollama läuft als separater Prozess ohne Image-Overhead). |
| **OpenAI Direct als Produktiv-Default** | Sofort einsatzbereit ohne Azure-Setup. Verworfen aus demselben Grund wie in ADR-004: der vollständige Dokumentkorpus würde auf US-Servern verarbeitet — kein EU-Datenhaltungs-Guarantee, Widerspruch zur Datenschutz-Linie. Bleibt als Dev-/Test-Pfad ohne Produktivdaten zugelassen. |
| **Nur Cloud, kein lokaler Fallback** | Verhindert Entwicklung ohne Netzwerkzugang und schliesst datenschutzkritische OnPrem-Deployments aus — widerspricht der Maintainability-NFA. |

---

*Abhängigkeiten: ADR-003 (pgvector-Dimension folgt aus konfiguriertem Modell), ADR-004 (LiteLLM-Muster, Azure OpenAI EU)*
