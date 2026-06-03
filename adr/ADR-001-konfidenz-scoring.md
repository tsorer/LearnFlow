# ADR-001 · Konfidenz-Scoring: Strategy Pattern mit austauschbarem Scorer

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | LearnFlow Architecture Team |
| **Bezug** | US-02, QA-06 (Testability), QA-04 (Reliability) |
| **Massnahme** | M2 |

---

## Kontext

US-02 schreibt eine dreistufige Unterdrückungslogik für KI-Antworten vor. Der Entscheid vom 2026-05-20 legt die Vorrang-Reihenfolge fest:

1. **Quellenprüfung** — kein Retrieval-Treffer → Antwort wird nicht angezeigt
2. **Konfidenz-Score** — Score unter Schwellenwert → „Ich weiss es nicht"
3. **Self-Check-Anteil** — unter 80 % → „Eingeschränkt belegt"; unter 50 % → unterdrückt

Risiko 2 aus dem Requirements-Dokument benennt das zentrale offene Problem: *wie* der Self-Check-Anteil konkret berechnet wird, ist nicht definiert. Die zwei diskutierten Mechanismen — semantische Ähnlichkeit zwischen Antwort-Sätzen und Retrieval-Chunks vs. LLM-Selbstevaluation — haben unterschiedliche Qualitäts- und Kostenprofil. Eine Entscheidung ist vor Implementierungsstart nötig, aber der gewählte Algorithmus muss nachträglich austauschbar bleiben.

Zusätzlich fordert US-11, dass die Schwellenwerte ohne Code-Deployment änderbar sind.

---

## Entscheidung

Der Konfidenz-Scoring-Mechanismus wird als **Strategy Pattern** implementiert:

- Ein `ConfidenceScorer`-Interface kapselt ausschliesslich die Berechnung des Self-Check-Anteils.
- Ein `ConfidenceEvaluator` enthält die unveränderliche Stufenlogik und nimmt `ConfidenceScorer` sowie `ConfigService` als injizierte Abhängigkeiten entgegen.
- Schwellenwerte werden ausnahmslos über den `ConfigService` gelesen — nie als Konstanten im Code.

### Komponentenstruktur

```
ConfidenceEvaluator
    ├── ConfidenceScorer (Interface)
    │       ├── SemanticSimilarityScorer   [MVP]
    │       ├── LLMSelfEvaluationScorer    [Post-MVP]
    │       └── FixedRatioScorer           [Tests]
    └── ConfigService (Interface)
            ├── DBConfigService            [Produktion]
            └── InMemoryConfigService      [Tests]
```

### Interface-Definition

```typescript
interface ConfidenceScorer {
  /** Gibt einen Wert zwischen 0.0 und 1.0 zurück:
   *  Anteil der Antwort-Aussagen, die durch Retrieval-Chunks belegbar sind. */
  computeSelfCheckRatio(
    llmResponse: string,
    retrievalChunks: Chunk[]
  ): Promise<number>
}
```

### Stufenlogik (ConfidenceEvaluator)

```typescript
type AnswerDecision =
  | { kind: 'NO_SOURCE'  }
  | { kind: 'DONT_KNOW'; hint: string }
  | { kind: 'SUPPRESSED' }
  | { kind: 'LIMITED'    }
  | { kind: 'OK'         }

class ConfidenceEvaluator {
  constructor(
    private scorer:    ConfidenceScorer,
    private config:    ConfigService
  ) {}

  async evaluate(
    hits:     Chunk[],
    score:    number,
    response: string
  ): Promise<AnswerDecision> {

    const t = await this.config.getThresholds()

    // Stufe 1 — Quellenprüfung (US-01)
    if (hits.length === 0)
      return { kind: 'NO_SOURCE' }

    // Stufe 2 — Konfidenz-Score (US-02)
    if (score < t.minConfidenceScore)
      return { kind: 'DONT_KNOW',
               hint: 'Versuche, einen konkreten Prozess oder ein Dokument zu nennen.' }

    // Stufe 3 — Self-Check-Anteil (US-02)
    const ratio = await this.scorer.computeSelfCheckRatio(response, hits)
    if (ratio < t.suppressThreshold) return { kind: 'SUPPRESSED' }
    if (ratio < t.limitedThreshold)  return { kind: 'LIMITED' }
    return { kind: 'OK' }
  }
}
```

### MVP-Scorer: Semantische Ähnlichkeit

Für das MVP wird `SemanticSimilarityScorer` implementiert: jeder Satz der LLM-Antwort wird mit dem Embedding-Modell vektorisiert und der Cosinus-Ähnlichkeit zu den Retrieval-Chunks verglichen. Überschreitet ein Satz den Ähnlichkeitsschwellenwert, gilt er als „belegt". Der Self-Check-Anteil ist der Quotient belegter Sätze zu Gesamtsätzen.

---

## Begründung

**Warum Strategy Pattern statt Pure Function?**

Eine einfache Pure Function (`evaluateConfidence(input): AnswerDecision`) wäre ausreichend, wenn der Self-Check-Algorithmus feststünde. Da Risiko 2 explizit offen ist und der Algorithmus sich voraussichtlich nach dem ersten Pilot-Betrieb ändern wird (z.B. von semantischer Ähnlichkeit auf LLM-Selbstevaluation), würde eine Pure Function einen späteren Umbau erzwingen, der die gesamte Stufenlogik tangiert.

Das Strategy Pattern trennt die stabile Stufenlogik vom instabilen Algorithmus. Kosten: eine zusätzliche Abstraktion und ca. 30 Minuten Mehraufwand bei der initialen Implementierung.

**Warum kein Chain-of-Responsibility?**

Drei fixe, geordnete Stufen rechtfertigen kein Pipeline-Pattern. Der Mehraufwand für ein Context-Objekt und Handler-Verkettung übersteigt den Nutzen für einen Anwendungsfall dieser Grösse.

---

## Betrachtete Alternativen

### Alternative 1 · Pure Function

```typescript
function evaluateConfidence(input: ScoringInput): AnswerDecision { ... }
```

**Abgelehnt**, weil der Self-Check-Algorithmus (Parameter `selfCheckRatio`) von aussen übergeben werden müsste — die Berechnung läge dann ungekapselt im aufrufenden Code. Das verlagert das Problem, löst es nicht.

### Alternative 2 · Chain of Responsibility

Jede Stufe ist ein eigenständiger Handler; Context-Objekt wandert durch die Kette.

**Abgelehnt**: drei fixe, sequenzielle Stufen mit eindeutiger Reihenfolge sind kein Anwendungsfall für dieses Pattern. Erhöhter Boilerplate ohne Mehrwert.

---

## Konsequenzen

### Positiv
- Self-Check-Algorithmus austauschbar ohne Änderung an der Stufenlogik
- `ConfidenceEvaluator` mit `FixedRatioScorer` und `InMemoryConfigService` in unter 5 Unit-Tests vollständig abgedeckt
- Schwellenwerte nie als Magic Numbers im Code — alle Änderungen laufen über `ConfigService` (→ ADR-003)
- Post-MVP ML-basierter Scorer als neue Implementierung einhängbar

### Negativ / Risiken
- Zwei Interfaces statt einer Funktion: minimaler Erklärungsaufwand beim Onboarding
- `SemanticSimilarityScorer` benötigt Zugriff auf den Embedding-Adapter (→ Abhängigkeit auf LLM-Infrastruktur auch im Scoring-Pfad)
- Die Qualität des MVP-Scorers (Semantische Ähnlichkeit) ist erst durch den RAG-Evaluierungs-Harness validierbar — kein theoretischer Nachweis möglich

---

## Abhängigkeiten

| Abhängigkeit | Typ | Hinweis |
|---|---|---|
| ADR-003 (ConfigService) | Voraussetzung | Schwellenwerte kommen aus `ConfigService` |
| ADR-002 (RAG-Pipeline) | Verwendend | `ConfidenceEvaluator` wird in der Pipeline aufgerufen |
| QA-06 Testability (M3) | Validierung | RAG-Evaluierungs-Harness prüft die 90%-„Weiss-ich-nicht"-Rate |
| Risiko 2 | Offen | Self-Check-Algorithmus muss vor Sprint 1 als Spike validiert werden |

---

## Offen / Nächste Schritte

- [ ] Spike: `SemanticSimilarityScorer` gegen Evaluierungs-Dataset ausführen; Qualitätsschwelle festlegen (Go/No-Go für Risiko 1+2)
- [ ] Konkrete Ähnlichkeitsschwelle für „Satz gilt als belegt" definieren (Cosinus-Score > X)
- [ ] Entscheiden, ob `selfCheckRatio` im Response-Objekt für Lara sichtbar ist oder nur als Metainfo intern bleibt
