# ADR-008: Konfidenz- & Unterdrückungspipeline — Mehrstufige Defense-in-Depth, fail-closed

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-31 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

Die Reliability-NFA (Halluzinationsrate = 0 %, bei Out-of-Corpus-Fragen ≥ 90 % „Weiss ich nicht") ist das zentrale Produktversprechen von LearnFlow: Lernende müssen den Antworten vertrauen können. US-02 verlangt zusätzlich, dass jede Antwort mit einer **Konfidenz-Angabe** versehen wird.

ADR-007 hat die *retrieval-seitige* Vorstufe entschieden (Schwellenwert-Gate: ohne ausreichend ähnlichen Chunk → kein LLM-Aufruf). Das allein genügt aber nicht: Auch wenn relevante Chunks gefunden werden, kann das LLM (a) über den Kontext hinaus halluzinieren, (b) Chunks falsch kombinieren oder (c) eine plausibel klingende, aber nicht belegte Antwort formulieren. Es braucht deshalb **nach** der Generierung weitere Prüfschichten und ein definiertes Konfidenz-Mass.

Diese „Konfidenz-Unterdrückungspipeline" wird im C4-Container-Diagramm und im Request-Flow vorausgesetzt (Quellenprüfung → Konfidenz → Self-Check, „< 50 % → unterdrückt"), war aber nie als Entscheidung dokumentiert.

Leitprinzip: **fail-closed**. Da die NFA 0 % Halluzination *über* hohem Recall priorisiert, wird im Zweifel unterdrückt („Weiss ich nicht") statt eine unsichere Antwort auszuliefern. Eine fälschlich unterdrückte Antwort ist ein akzeptabler Fehler; eine ausgelieferte Halluzination nicht.

**Abgrenzung:** ADR-007 = Chunking/Retrieval/Gate. ADR-008 = alles *nach* dem Retrieval-Gate (Konfidenz-Berechnung, Post-Generierungs-Prüfungen, User-Anzeige).

---

## Entscheidung

Wir implementieren die Reliability als **mehrstufige Defense-in-Depth-Pipeline** im API Server. Jede Stufe kann unterdrücken; eine Antwort wird nur ausgeliefert, wenn alle Stufen passieren. Alle Schwellen liegen in der `config`-Tabelle (ADR-003) und sind **ohne Deployment** kalibrierbar.

### Stufe 0 — Retrieval-Gate *(aus ADR-007, vorgelagert)*
Kein Chunk über Similarity-Schwelle → sofort „Weiss ich nicht", kein LLM-Aufruf.

### Stufe 1 — Retrieval-Konfidenz (deterministisch, vor der Generierung)
Aus den Retrieval-Signalen wird ein **Retrieval-Konfidenz-Score** berechnet:
- maximale Similarity des Top-Chunks,
- mittlere Similarity der Top-`n`,
- Anzahl Chunks über Schwelle (Evidenz-Dichte).

Liegt der Score unter `min_retrieval_confidence` → „Weiss ich nicht" (kein LLM-Aufruf).

### Stufe 2 — Grounding-/Citation-Check (deterministisch, nach der Generierung)
Der Grounding-Prompt (ADR-007) zwingt das LLM, **jede Aussage mit einer Chunk-Referenz** zu belegen. Nach der Generierung wird deterministisch geprüft:
- Anteil belegter Antwort-Segmente (**Citation-Coverage**),
- Gültigkeit der Referenzen (zeigen sie auf tatsächlich gelieferte Chunks?).

Coverage unter `min_citation_coverage` (Startwert **50 %**) oder ungültige/erfundene Referenzen → **unterdrückt**.

### Stufe 3 — LLM-Self-Check (nur für Grenzfälle, kostenkontrolliert)
Für Antworten, deren Konfidenz **nahe der Schwelle** liegt, erfolgt **ein** zusätzlicher, günstiger LLM-Aufruf (Verifikations-Prompt): „Ist diese Antwort vollständig durch den bereitgestellten Kontext gedeckt? Welche Teile nicht?". Meldet der Self-Check ungedeckte Aussagen → unterdrückt. Antworten mit klar hoher Konfidenz überspringen diese Stufe (kein Token-Overhead im Normalfall).

### Komposit-Konfidenz & Anzeige (US-02)
Der **angezeigte** Konfidenzwert ist eine gewichtete Kombination aus Retrieval-Konfidenz (Stufe 1) und Citation-Coverage (Stufe 2); Gewichte in `config`. Mapping auf drei Bänder für die UI:

| Band | Bedeutung | UI |
|---|---|---|
| **Hoch** | gut belegt, hohe Coverage | Antwort + Quellen, grün |
| **Mittel** | belegt, aber lückenhaft | Antwort + Quellen + Hinweis, gelb |
| **Niedrig / unterdrückt** | unter Schwelle / ungedeckt | „Weiss ich nicht" (+ optional nächstliegende Quellen, ohne generierten Inhalt) |

Unterdrückte Antworten liefern eine **standardisierte** „Weiss ich nicht"-Meldung — nie generierten Fließtext.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Defense-in-Depth: mehrere unabhängige Schichten — eine durchgerutschte Halluzination müsste Retrieval-Gate, Retrieval-Konfidenz, Citation-Check *und* Self-Check passieren. Das ist der Kern der 0 %-NFA.
- **+** **Fail-closed** als bewusste Auslegung: Precision vor Recall — passt zur Priorität „lieber keine Antwort als eine falsche".
- **+** Stufen 0–2 sind **deterministisch** (keine LLM-Abhängigkeit) → reproduzierbar, testbar und kostenlos; nur der Grenzfall (Stufe 3) kostet einen Zusatz-Token-Aufruf.
- **+** Alle Schwellen/Gewichte in der `config`-Tabelle → empirische Kalibrierung im Spike ohne Deployment (Maintainability-NFA).
- **+** US-02 direkt erfüllt: das Komposit-Mass ist die angezeigte Konfidenz, mit nachvollziehbarer Herleitung statt einer LLM-Selbsteinschätzung.
- **+** Provider-portabel: keine Abhängigkeit von providerspezifischen Token-Logprobs → funktioniert über LiteLLM mit Azure OpenAI EU *und* Ollama (ADR-004).

### Negative Konsequenzen

- **−** Höhere Latenz für Grenzfälle (Stufe 3 = zweiter LLM-Aufruf). Mitigation: nur nahe der Schwelle ausgelöst; bei klar hoher/niedriger Konfidenz übersprungen. Im Rahmen der Performance-NFA (≤ 10 s p95).
- **−** Fail-closed senkt den Recall: korrekte, aber knapp belegte Antworten werden evtl. fälschlich unterdrückt. Bewusst akzeptiert; über `config`-Schwellen justierbar.
- **−** Citation-Coverage misst *Beleg-Form*, nicht *inhaltliche Korrektheit* — ein LLM könnte korrekt zitieren und trotzdem falsch schlussfolgern. Mitigation: Stufe 3 (Self-Check) fängt einen Teil davon; Restrisiko über Eval messen.
- **−** Alle Startwerte (Coverage 50 %, Gewichte, Band-Grenzen) sind **Hypothesen** und ohne Kalibrierung gegen ein Eval-Dataset nicht NFA-garantierend. Abhängigkeit zur (noch offenen) Eval-Strategie.
- **−** Mehrere Stufen = mehr Code/Test-Oberfläche als ein simpler Schwellenwert. Mitigation: jede Stufe ist isoliert testbar (Testability-NFA, vgl. C4).

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Nur LLM-Selbsteinschätzung** („Wie sicher bist du? 0–100 %") | Einfach, aber notorisch unzuverlässig — LLMs sind oft selbstsicher *und* falsch. Als alleiniges Mass ungeeignet für eine 0 %-Halluzinations-NFA. Fließt allenfalls als schwaches Zusatzsignal in Stufe 3 ein. |
| **Token-Logprob-/Perplexity-basierte Konfidenz** | Token-Wahrscheinlichkeiten wären ein echtes Signal, sind aber providerabhängig und über die Chat-API uneinheitlich verfügbar — bricht die Provider-Portabilität (Azure ↔ Ollama via LiteLLM, ADR-004). Verworfen. |
| **Nur Schwellenwert-Gate (ADR-007), keine Post-Generierungs-Prüfung** | Günstig, aber lässt Halluzinationen *innerhalb* gefundener Chunks ungeprüft (falsche Kombination/Übergeneralisierung). Reicht für eine 0 %-NFA nicht. |
| **Self-Check für *jede* Antwort (immer zweiter LLM-Aufruf)** | Maximale Sicherheit, aber verdoppelt Tokens/Latenz pro Anfrage. Verworfen zugunsten des kostenkontrollierten Grenzfall-Triggers (Stufe 3 nur nahe der Schwelle). |
| **Separater Klassifikator/Cross-Encoder als Faithfulness-Modell** | Stärkste Faithfulness-Prüfung, holt aber PyTorch/ein Zusatzmodell zurück (gegen ADR-005) oder einen weiteren Provider. Post-MVP-Option; Schnittstelle bleibt offen. |

---

## Offene Punkte / nächste Schritte

1. **Spike-Eval (Woche 1):** Schwellen (Retrieval-Konfidenz, Citation-Coverage, Band-Grenzen, Self-Check-Triggerbereich) gegen ein Eval-Dataset kalibrieren — inkl. Messung von Halluzinationsrate und „Weiss ich nicht"-Quote. Gemeinsame Abhängigkeit mit ADR-007 zur noch fehlenden **Eval-Strategie** (Kandidat für ein eigenes ADR/Spike-Deliverable).
2. **Citation-Format festlegen:** maschinell prüfbares Referenzformat im Grounding-Prompt (ADR-007), damit Stufe 2 deterministisch parsen kann.
3. Schwellen nach dem Spike als „Accepted" fixieren.

---

*Abhängigkeiten: ADR-007 (Retrieval-Gate als Stufe 0, Grounding-Prompt/Citations), ADR-004 (LLM-Aufruf für Self-Check, Provider-Portabilität), ADR-003 (`config`-Tabelle für Schwellen), ADR-005 (kein PyTorch-Re-Ranker/Klassifikator) · Erfüllt: Reliability-NFA, US-02 (Konfidenz-Anzeige)*
