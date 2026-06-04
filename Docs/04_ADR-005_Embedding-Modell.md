# ADR-005: Embedding-Modell — Konfigurierbar via LiteLLM (MVP: OpenAI Direct · Produktion: Azure OpenAI EU · OnPrem: Ollama)

| Feld             | Inhalt                                                                    |
| ---------------- | ------------------------------------------------------------------------- |
| **Status**       | Proposed                                                                  |
| **Datum**        | 2026-05-27                                                                |
| **Aktualisiert** | 2026-05-31 — MVP-Prämisse (keine echten internen Dokumente) eingearbeitet |
| **Verfasser**    | LearnFlow-Team (Frank, Niklaus, Reto, Christoph)                                     |

---

## Kontext

Die RAG-Pipeline braucht Embeddings in zwei Phasen: beim Dokument-Upload (alle Chunks indexieren) und bei jeder Nutzeranfrage (Query-Embedding für Retrieval). Das Embedding-Modell bestimmt die Vektor-Dimension, die im pgvector-Schema fest verankert ist. Ein Modellwechsel erfordert eine vollständige Re-Indexierung aller Dokumente — das ist kein Blocker, sondern ein bewusst akzeptierter Betriebsvorgang. Verschiedene Installationen (Entwicklung, Produktion) können unterschiedliche Modelle und Dimensionen verwenden, weil sie separate Datenbanken haben. Kompatibilität zwischen Installationen ist kein Ziel.

**MVP-Prämisse:** Im MVP wird **kein echter interner Dokumentenbestand** indexiert (Test-/Dummy-/öffentliche Inhalte). Datenschutz ist im MVP daher kein Blocker — es darf der einfachste Provider verwendet werden.

**Datenschutz-Relevanz für die Produktion:** Beim Indexieren wird der *gesamte* Dokumentkorpus an den Embedding-Provider gesendet (jeder Chunk jedes Dokuments) — die datenintensivste Exposition der gesamten Pipeline. Sobald **echte interne Dokumente** indexiert werden, muss der Provider daher derselben EU-/Compliance-Linie folgen wie der LLM-Provider in ADR-004.

Das Projekt braucht drei lauffähige Szenarien:

1. **MVP / Standard**: OpenAI Direct — einfachste Anbindung (nur API-Key), zulässig mangels echter interner Daten.
2. **Produktion (echte interne Dokumente)**: Azure OpenAI EU — hohe Qualität bei garantierter EU-Datenresidenz.
3. **OnPrem / Datenschutz**: Ollama — keine API-Kosten, kein Datentransfer, offline-fähig.

---

## Entscheidung

Wir verwenden **LiteLLM als Abstraktions-Layer für Embeddings** — identisch zum LLM-Muster aus ADR-004. Modell, Provider und Dimension sind Konfigurationsparameter. Kein Code-Change bei einem Modell- oder Provider-Wechsel.

**Konfigurierte Standardwerte je Umgebung:**

| Umgebung                                             | Provider          | Modell                   | Dimension |
| ---------------------------------------------------- | ----------------- | ------------------------ | --------- |
| **MVP / Standard** (keine echten internen Dokumente) | **OpenAI Direct** | `text-embedding-3-small` | 1536      |
| Produktion (echte interne Dokumente)                 | Azure OpenAI EU   | `text-embedding-3-small` | 1536      |
| OnPrem / Datenschutz                                 | Ollama            | `bge-m3`                 | 1024      |

Die aktive Konfiguration (Modell-Name + Dimension) wird beim Start in der Datenbank persistiert. Bei einem Modellwechsel triggert ein Migrations-Script die vollständige Re-Indexierung aller Dokumente.

**Offen für den Tech-Spike (Sprint 0):** `text-embedding-3-small` ist als kosteneffizienter Standard gesetzt, aber für einen *deutschsprachigen Fachkorpus* nicht zwingend die qualitativ beste Wahl (das Modell ist englisch-optimiert). Vor Festlegung ist ein kurzer Retrieval-Eval auf echten Fachtexten vorgesehen — `text-embedding-3-small` vs. `text-embedding-3-large` vs. ein dediziert multilinguales Modell. Auffällig: das stärkste Deutsch-Modell (`bge-m3`) ist aktuell nur lokal vorgesehen, nicht in Produktion.

**Constraint (Kopplung an ADR-003):** pgvector indexiert HNSW nur bis **2000 Dimensionen**. Die gesetzten Werte (1536, 1024) sind unkritisch; ein Wechsel auf ein höherdimensionales Modell (z. B. `text-embedding-3-large`, 3072) erfordert Matryoshka-Reduktion auf ≤ 2000 oder den `halfvec`-Typ — sonst lässt sich der HNSW-Index nicht anlegen.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Dasselbe Abstraktionsmuster *und* dieselbe MVP-/Produktiv-Staffelung wie ADR-004 (LiteLLM; MVP: OpenAI Direct, Produktion: Azure OpenAI EU): ein konsistentes Konfigurationsschema für LLM und Embeddings — Provider-Wechsel für beide Komponenten gemeinsam als Konfigurationseintrag.
- **+** MVP sofort einsatzbereit: OpenAI-Direct-Embeddings brauchen nur einen API-Key, kein Azure-Setup.
- **+** Lokale Entwicklung funktioniert vollständig ohne Netzwerkzugang — `ollama pull bge-m3` genügt; kein API-Key nötig.
- **+** Kein PyTorch im Docker-Image des Backends: Ollama läuft als separater lokaler Prozess; das Backend ruft nur seine REST-API auf.
- **+** Provider-Wechsel (OpenAI → Ollama oder umgekehrt) ist ein Konfigurationseintrag, kein Code-Change und kein Deployment.
- **+** `bge-m3` (Ollama lokal) ist explizit multilingual trainiert — gut für deutschsprachige Fachtexte; deckt Datenschutz-Anforderungen ohne Cloud-Abhängigkeit ab.

### Negative Konsequenzen

- **−** Modellwechsel erfordert vollständige Re-Indexierung aller Dokumente (andere Dimension = Schema-Migration + alle Chunks neu generieren). Bewusst akzeptiert: betrifft eine geplante Betriebssituation, keinen Fehlerfall.
- **−** Dev- und Prod-Vektordatenbanken sind nicht kompatibel (unterschiedliche Dimensionen: 1536 vs. 1024). Bewusst akzeptiert: separate Installationen mit separaten Daten.
- **−** `bge-m3` (1024 Dim) hat geringere Qualität als `text-embedding-3-small` (1536 Dim) — Retrieval-Ergebnisse in der lokalen Entwicklung weichen von Produktion ab. Mitigation: Evaluations-Tests laufen immer gegen die Produktionskonfiguration (OpenAI).
- **−** Ollama muss auf dem Entwickler-Laptop installiert und das Modell heruntergeladen sein (~1.2 GB für `bge-m3`). Kein Blocker, aber Onboarding-Schritt mit Wartezeit beim ersten `ollama pull`.
- **−** **Zwingende Umstellung vor echten internen Dokumenten:** Im MVP gehen Chunks an OpenAI Direct (US-Server) — zulässig nur mit Test-/Dummy-Daten. Vor dem Indexieren echter interner Dokumente muss auf Azure OpenAI EU (oder Ollama) umgestellt werden — eine Konfigurationszeile, aber harte Go-Live-Vorbedingung (vgl. ADR-004). Wird dies vergessen, würde der vollständige Korpus auf US-Servern verarbeitet (Compliance-Verstoss). Mitigation: Go-Live-Checklist + optionaler Guard gegen Nicht-EU-Provider bei „intern/produktiv" markiertem Korpus.

---

## Abgewogene Alternativen

| Alternative                                             | Warum verworfen                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Feste Dimension für alle Umgebungen**                 | Unnötige Einschränkung, da Installationen ohnehin nicht kompatibel sind und keine Vereinheitlichung brauchen. (Anmerkung: `text-embedding-3-small` unterstützt Matryoshka-Dimension-Reduktion nahezu verlustfrei, z. B. auf 1024 — eine Vereinheitlichung wäre also technisch günstig möglich, ist aber kein Ziel.)                                                        |
| **`text-embedding-3-large` (3072 Dim) in Produktion**   | Deutlich höhere Retrieval-Qualität, insbesondere für deutschsprachige Fachtexte, ebenfalls auf Azure OpenAI EU verfügbar. **Offen für den Spike-Eval** (siehe Constraint unten) statt heute fix verworfen: höhere Kosten pro Token, und 3072 Dim überschreiten das HNSW-Indexlimit von pgvector (2000) — erfordert Matryoshka-Reduktion auf ≤ 2000 oder den `halfvec`-Typ. |
| **`nomic-embed-text` statt `bge-m3` (Ollama lokal)**    | 274 MB statt 1.2 GB — deutlich schlanker. Verworfen wegen englisch-primärem Training: auf deutschsprachigen Fachtexten schlechtere Retrieval-Qualität als `bge-m3`. Valide Alternative falls Laptop-Ressourcen knapp sind.                                                                                                                                                 |
| **`sentence-transformers` direkt im Backend**           | PyTorch-Dependency (+1.5 GB Docker-Image); kein Vorteil gegenüber Ollama (gleiche Modelle verfügbar, aber Ollama läuft als separater Prozess ohne Image-Overhead).                                                                                                                                                                                                         |
| **Azure OpenAI EU als MVP-Default**                     | EU-konform, aber der Setup-/Quota-Aufwand bringt im MVP keinen Schutzwert, solange keine echten internen Dokumente indexiert werden. Zugunsten OpenAI Direct als MVP-Start zurückgestellt; bleibt der Produktiv-Pfad.                                                                                                                                                      |
| **OpenAI Direct auch in Produktion (mit echten Daten)** | Sofort einsatzbereit ohne Azure-Setup. Verworfen aus demselben Grund wie in ADR-004: der vollständige interne Korpus würde auf US-Servern verarbeitet — kein EU-Datenhaltungs-Guarantee, Widerspruch zur Datenschutz-Linie. Nur zulässig im MVP ohne echte interne Dokumente.                                                                                              |
| **Nur Cloud, kein lokaler Fallback**                    | Verhindert Entwicklung ohne Netzwerkzugang und schliesst datenschutzkritische OnPrem-Deployments aus — widerspricht der Maintainability-NFA.                                                                                                                                                                                                                               |

---

*Abhängigkeiten: ADR-003 (pgvector-Dimension folgt aus konfiguriertem Modell), ADR-004 (LiteLLM-Muster, gleiche MVP-/Produktiv-Provider-Staffelung)*
