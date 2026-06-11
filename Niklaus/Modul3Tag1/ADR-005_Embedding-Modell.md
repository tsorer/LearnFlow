# ADR-005: Embedding-Modell — Konfigurierbar via LiteLLM (OpenAI API oder Ollama lokal)

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

Die RAG-Pipeline braucht Embeddings in zwei Phasen: beim Dokument-Upload (alle Chunks indexieren) und bei jeder Nutzeranfrage (Query-Embedding für Retrieval). Das Embedding-Modell bestimmt die Vektor-Dimension, die im pgvector-Schema fest verankert ist. Ein Modellwechsel erfordert eine vollständige Re-Indexierung aller Dokumente — das ist kein Blocker, sondern ein bewusst akzeptierter Betriebsvorgang. Verschiedene Installationen (Entwicklung, Produktion) können unterschiedliche Modelle und Dimensionen verwenden, weil sie separate Datenbanken haben. Kompatibilität zwischen Installationen ist kein Ziel.

Das Projekt braucht zwei lauffähige Szenarien:
1. **Produktion / Standard**: OpenAI API — hohe Qualität, sofort verfügbar.
2. **Lokal / Datenschutz**: Ollama — keine API-Kosten, kein Datentransfer, offline-fähig.

---

## Entscheidung

Wir verwenden **LiteLLM als Abstraktions-Layer für Embeddings** — identisch zum LLM-Muster aus ADR-004. Modell, Provider und Dimension sind Konfigurationsparameter. Kein Code-Change bei einem Modell- oder Provider-Wechsel.

**Konfigurierte Standardwerte je Umgebung:**

| Umgebung | Provider | Modell | Dimension |
|---|---|---|---|
| Produktion / Standard | OpenAI API | `text-embedding-3-small` | 1536 |
| Lokal / Datenschutz | Ollama | `bge-m3` | 1024 |

Die aktive Konfiguration (Modell-Name + Dimension) wird beim Start in der Datenbank persistiert. Bei einem Modellwechsel triggert ein Migrations-Script die vollständige Re-Indexierung aller Dokumente.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Dasselbe Abstraktionsmuster wie ADR-004 (LiteLLM für LLM): ein konsistentes Konfigurationsschema für alle KI-Komponenten — ein API-Key, eine Kostenstelle für LLM und Embeddings.
- **+** Lokale Entwicklung funktioniert vollständig ohne Netzwerkzugang — `ollama pull bge-m3` genügt; kein API-Key nötig.
- **+** Kein PyTorch im Docker-Image des Backends: Ollama läuft als separater lokaler Prozess; das Backend ruft nur seine REST-API auf.
- **+** Provider-Wechsel (OpenAI → Ollama oder umgekehrt) ist ein Konfigurationseintrag, kein Code-Change und kein Deployment.
- **+** `bge-m3` (Ollama lokal) ist explizit multilingual trainiert — gut für deutschsprachige Fachtexte; deckt Datenschutz-Anforderungen ohne Cloud-Abhängigkeit ab.

### Negative Konsequenzen

- **−** Modellwechsel erfordert vollständige Re-Indexierung aller Dokumente (andere Dimension = Schema-Migration + alle Chunks neu generieren). Bewusst akzeptiert: betrifft eine geplante Betriebssituation, keinen Fehlerfall.
- **−** Dev- und Prod-Vektordatenbanken sind nicht kompatibel (unterschiedliche Dimensionen: 1536 vs. 1024). Bewusst akzeptiert: separate Installationen mit separaten Daten.
- **−** `bge-m3` (1024 Dim) hat geringere Qualität als `text-embedding-3-small` (1536 Dim) — Retrieval-Ergebnisse in der lokalen Entwicklung weichen von Produktion ab. Mitigation: Evaluations-Tests laufen immer gegen die Produktionskonfiguration (OpenAI).
- **−** Ollama muss auf dem Entwickler-Laptop installiert und das Modell heruntergeladen sein (~1.2 GB für `bge-m3`). Kein Blocker, aber Onboarding-Schritt mit Wartezeit beim ersten `ollama pull`.
- **−** Dokumentinhalte gehen beim Indexieren an die OpenAI API. Für datenschutzkritische Deployments: auf Ollama (lokal) umstellen — eine Konfigurationszeile.

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Feste Dimension für alle Umgebungen** | Unnötige Einschränkung: zwingt entweder OpenAI zur Dimension-Reduktion (Qualitätsverlust) oder Ollama zu einem suboptimalen Modell. Da Installationen ohnehin nicht kompatibel sind, gibt es keinen Grund zur Vereinheitlichung. |
| **`nomic-embed-text` statt `bge-m3` (Ollama lokal)** | 274 MB statt 1.2 GB — deutlich schlanker. Verworfen wegen englisch-primärem Training: auf deutschsprachigen Fachtexten schlechtere Retrieval-Qualität als `bge-m3`. Valide Alternative falls Laptop-Ressourcen knapp sind. |
| **`sentence-transformers` direkt im Backend** | PyTorch-Dependency (+1.5 GB Docker-Image); kein Vorteil gegenüber Ollama (gleiche Modelle verfügbar, aber Ollama läuft als separater Prozess ohne Image-Overhead). |
| **Nur OpenAI, kein lokaler Fallback** | Verhindert Entwicklung ohne Netzwerkzugang und schliesst datenschutzkritische Deployments aus — widerspricht der Maintainability-NFA. |

---

*Abhängigkeiten: ADR-003 (pgvector-Dimension folgt aus konfiguriertem Modell), ADR-004 (LiteLLM-Muster, OpenAI API)*
