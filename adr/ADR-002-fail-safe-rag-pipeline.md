# ADR-002 · Fail-Safe RAG-Pipeline: Discriminated Union als Ergebnistyp

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | LearnFlow Architecture Team |
| **Bezug** | US-01, US-02, QA-04 (Reliability), QA-06 (Testability) |
| **Massnahme** | M5 |

---

## Kontext

Die RAG-Pipeline ist der kritische Pfad von LearnFlow. Sie besteht aus mehreren sequenziellen Schritten:

```
Eingabe-Validierung → Retrieval → Konfidenz-Check → LLM-Call → Self-Check → Antwort-Assembly
```

An jedem Schritt kann ein anderer Fehler auftreten, der eine andere Reaktion erfordert:

| Fehlerzustand | Korrekte Reaktion | Falsche Reaktion |
|---|---|---|
| Kein Retrieval-Treffer | „Keine Quelle gefunden" anzeigen | Antwort ohne Quelle generieren |
| Konfidenz-Score zu tief | „Ich weiss es nicht" + Hinweis | Antwort mit tiefer Konfidenz ausgeben |
| LLM-API nicht erreichbar | Klare Fehlermeldung | Leere oder halluzinierte Antwort |
| LLM-Timeout | Fehlermeldung nach 1 Retry | Unbegrenztes Warten |
| Self-Check unter 50 % | Antwort vollständig unterdrücken | Unmarkierte Antwort ausgeben |

Das Requirements-Dokument formuliert die zentrale Anforderung explizit: *„Eine falsch dargestellte Antwort ist schlimmer als gar keine."* Das bedeutet: jeder Fehlerpfad muss zu einem definierten, sicheren Ergebnis führen — nicht zu einer unbehandelten Exception oder einem stillen Fehler.

Das Kernproblem mit klassischen Exception-Hierarchien: ein vergessener `catch`-Branch gibt implizit `undefined` oder einen Teilzustand zurück. Das ist der exakte Mechanismus, der halluzinierte Antworten bei Ausfällen ermöglicht.

---

## Entscheidung

Die RAG-Pipeline gibt **immer** einen explizit typisierten `RAGResult`-Wert zurück. Exceptions werden nur für wirklich unerwartete Zustände (Programmierfehler, nicht kontrollierbare Systemfehler) verwendet, **nicht** als Kontrollfluss für antizipierte Fehlerzustände.

Der Rückgabetyp ist ein **Discriminated Union** (Tagged Union): eine abgeschlossene Menge benannter Varianten, die alle möglichen Ausgaben der Pipeline vollständig beschreiben.

### Ergebnistyp

```typescript
type RAGResult =
  | {
      kind:       'answer'
      content:    string
      sources:    Source[]
      confidence: number
      label:      'ok' | 'limited'   // 'limited' = Self-Check 50–80 %
    }
  | {
      kind: 'dont_know'
      hint: string                   // Präzisierungshinweis für Lara
    }
  | { kind: 'no_source'   }          // kein Retrieval-Treffer oder Quelle nicht identifizierbar
  | { kind: 'suppressed'  }          // Self-Check-Anteil unter 50 %
  | { kind: 'unavailable'; message: string }  // LLM-API nicht erreichbar
  | { kind: 'timeout'     }          // LLM-Call überschreitet Timeout nach Retry
```

Jede Variante entspricht direkt einem UI-Zustand. Es gibt keine Variante, die eine halluzinierte oder ungeprüfte Antwort transportiert.

### Pipeline-Implementierung

```typescript
async function runRAGPipeline(question: string): Promise<RAGResult> {

  // Schritt 1: Retrieval
  const hits = await retriever.search(question)
  // retriever.search() wirft nie — leeres Array = kein Treffer

  // Schritt 2: Konfidenz-Check (→ ADR-001)
  const score     = computeRetrievalScore(hits)
  const decision  = await evaluator.evaluate(hits, score, '')
  // Frühe Exits: NO_SOURCE und DONT_KNOW vor dem LLM-Call
  if (decision.kind === 'NO_SOURCE') return { kind: 'no_source' }
  if (decision.kind === 'DONT_KNOW') return { kind: 'dont_know', hint: decision.hint }

  // Schritt 3: LLM-Call — Ergebnis als Result-Typ, kein throw
  const llmResult = await llmAdapter.complete(buildPrompt(question, hits))
  if (!llmResult.ok) {
    return llmResult.error.kind === 'timeout'
      ? { kind: 'timeout' }
      : { kind: 'unavailable', message: 'KI-Service vorübergehend nicht erreichbar.' }
  }

  // Schritt 4: Self-Check und finales Urteil
  const finalDecision = await evaluator.evaluate(hits, score, llmResult.value.text)
  switch (finalDecision.kind) {
    case 'SUPPRESSED': return { kind: 'suppressed' }
    case 'LIMITED':
      return {
        kind:       'answer',
        content:    llmResult.value.text,
        sources:    extractSources(hits),
        confidence: score,
        label:      'limited'
      }
    case 'OK':
      return {
        kind:       'answer',
        content:    llmResult.value.text,
        sources:    extractSources(hits),
        confidence: score,
        label:      'ok'
      }
    default:
      // Sollte nie eintreten — alle Varianten sind behandelt
      // TypeScript erkennt dies als Exhaustiveness-Check
      return { kind: 'unavailable', message: 'Unerwarteter Systemzustand.' }
  }
}
```

### Exhaustiveness im UI-Controller

```typescript
// TypeScript-Compiler meldet Fehler, wenn ein neuer RAGResult-Variant
// nicht im switch behandelt wird — kein Runtime-Fehler, sondern Build-Fehler
function renderResult(result: RAGResult): ReactNode {
  switch (result.kind) {
    case 'answer':
      return result.label === 'limited'
        ? <LimitedAnswerCard content={result.content} sources={result.sources} />
        : <AnswerCard content={result.content} sources={result.sources} />
    case 'dont_know':    return <DontKnowCard hint={result.hint} />
    case 'no_source':    return <NoSourceCard />
    case 'suppressed':   return <NoSourceCard />
    case 'unavailable':  return <ErrorCard message={result.message} />
    case 'timeout':      return <ErrorCard message="Zeitüberschreitung — bitte erneut versuchen." />
    // Fehlender Case → TypeScript-Fehler: "Not all code paths return a value"
  }
}
```

### LLM-Adapter-Interface mit Result-Typ

```typescript
type LLMError =
  | { kind: 'timeout'   }
  | { kind: 'api_error'; statusCode: number; detail: string }
  | { kind: 'rate_limit' }

interface LLMAdapter {
  /** Gibt immer ein Result zurück — wirft nie. */
  complete(prompt: string): Promise<Result<LLMResponse, LLMError>>
}

// Result-Hilftypen
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E }
```

Der Adapter enthält die einzige `try/catch`-Grenze im System für LLM-Fehler. Oberhalb des Adapters gibt es keine Exceptions mehr für antizipierte Fehlerzustände.

### Flussdiagramm

```
question
    │
    ▼
retriever.search()
    ├─(leer)────────────────────────────────────► { kind: 'no_source' }
    │ hits
    ▼
evaluator.evaluate() [pre-LLM]
    ├─(NO_SOURCE)───────────────────────────────► { kind: 'no_source' }
    ├─(DONT_KNOW)───────────────────────────────► { kind: 'dont_know', hint }
    │ pass
    ▼
llmAdapter.complete()
    ├─(Err: timeout)────────────────────────────► { kind: 'timeout' }
    ├─(Err: api_error / rate_limit)─────────────► { kind: 'unavailable' }
    │ Ok: llmResponse
    ▼
evaluator.evaluate() [post-LLM, mit Self-Check]
    ├─(SUPPRESSED)──────────────────────────────► { kind: 'suppressed' }
    ├─(LIMITED)─────────────────────────────────► { kind: 'answer', label: 'limited' }
    └─(OK)──────────────────────────────────────► { kind: 'answer', label: 'ok' }
```

Jeder Pfad ist benannt. Es gibt keinen Pfad ohne Rückgabewert.

---

## Begründung

**Warum Discriminated Union statt Exception-Hierarchie?**

Exceptions sind für unerwartete Zustände konzipiert. Alle sechs `RAGResult`-Varianten sind *erwartete* Zustände — sie sind aus den Akzeptanzkriterien von US-01 und US-02 direkt ableitbar. Exception-Hierarchien bieten keine Compiler-Garantie, dass alle Fälle behandelt werden. Ein vergessener `catch`-Branch gibt implizit `undefined` zurück, was im Frontend zu einem leeren oder falschen UI-Zustand führt.

Discriminated Unions machen den Exhaustiveness-Check zum Build-Fehler, nicht zum Runtime-Problem.

**Warum zwei `evaluator.evaluate()`-Aufrufe?**

Der erste Aufruf (vor dem LLM-Call) behandelt Stufe 1 und 2 — diese sind ohne LLM-Antwort prüfbar und sparen API-Kosten bei frühen Exits. Der zweite Aufruf (nach dem LLM-Call) führt den Self-Check (Stufe 3) durch, der die Antwort selbst benötigt.

**Warum kein `async`/`await` mit globaler Error-Boundary?**

Eine globale `try/catch`-Boundary würde alle Fehlerzustände auf einen einzigen Fehlertyp reduzieren und die differenzierte UI-Darstellung (unterschiedliche Nachrichten für `timeout` vs. `unavailable` vs. `no_source`) unmöglich machen.

---

## Betrachtete Alternativen

### Alternative 1 · Exception-Hierarchie

```typescript
class RAGException extends Error {}
class NoSourceException extends RAGException {}
class LLMUnavailableException extends RAGException {}
```

**Abgelehnt**: kein Compiler-Exhaustiveness-Check; vergessener `catch`-Branch führt zu undefiniertem Verhalten; Kontrollfluss via Exceptions ist schwerer nachzuvollziehen und zu testen.

### Alternative 2 · Result-Monad (fp-ts / neverthrow)

```typescript
import { pipe } from 'fp-ts/function'
import * as TE from 'fp-ts/TaskEither'
```

**Abgelehnt für MVP**: vollwertige Monad-Komposition (`.chain()`, `.map()`, `pipe()`) erhöht die Einstiegshürde für das Team erheblich. Der Mehrwert gegenüber einfachen Discriminated Unions ist für diesen Anwendungsfall gering. Für ein Python-Backend ist der native `match`-Ausdruck (ab 3.10) die bessere Alternative.

### Alternative 3 · Response-Objekt mit Status-Feld

```typescript
type RAGResponse = { status: 'ok' | 'error' | 'dont_know'; data?: ...; error?: ... }
```

**Abgelehnt**: optionale Felder (`?`) entfernen die Compiler-Garantie. `result.data` könnte `undefined` sein, auch wenn `status === 'ok'`. Discriminated Unions sind präziser.

---

## Konsequenzen

### Positiv
- Vollständige Abdeckung aller Fehlerpfade ist vom Compiler erzwingbar — kein vergessener Fall schleicht sich unbemerkt ein
- Jede `RAGResult`-Variante ist isoliert und ohne Netzwerk testbar (Mock-Adapter gibt vordefinierte Results zurück)
- UI-Komponenten sind direkt auf Varianten gemappt — keine implizite Null-Prüfung nötig
- Neue Fehlerzustände (z.B. `content_policy_violation`) können als neue Variante ergänzt werden; der Compiler zeigt sofort alle unbehandelten Stellen

### Negativ / Risiken
- Discriminated Unions sind in Python nicht nativ (Klassen-Hierarchie oder `dataclass`-Varianten nötig); der Exhaustiveness-Check muss manuell diszipliniert werden
- Die `Result<T, E>`-Abstraktion am LLM-Adapter ist für Entwickler ungewohnt, die ausschliesslich exception-basiert gearbeitet haben — einmalige Einführung nötig
- Jede neue RAGResult-Variante erfordert eine Anpassung im UI-Controller (gewünscht, aber expliziter Aufwand)

---

## Abhängigkeiten

| Abhängigkeit | Typ | Hinweis |
|---|---|---|
| ADR-001 (ConfidenceEvaluator) | Verwendet | Pipeline ruft `evaluator.evaluate()` zweimal auf |
| ADR-003 (ConfigService) | Indirekt | Über `ConfidenceEvaluator` — Schwellenwerte aus Config |
| US-01 AC: Fehlermeldung bei Ausfall | Validierung | `unavailable`-Variante deckt dieses Kriterium ab |
| US-02 AC: Unterdrückung unter 50 % | Validierung | `suppressed`-Variante deckt dieses Kriterium ab |
| QA-04: Circuit Breaker (M6) | Vorgelagert | Circuit Breaker im LLM-Adapter gibt `Err(rate_limit)` zurück — Pipeline reagiert auf den Result-Typ |

---

## Offen / Nächste Schritte

- [ ] Entscheiden: TypeScript (Frontend + BFF) oder Python (Backend)? Bestimmt die konkrete Syntax des Discriminated Union
- [ ] `Source`-Typ definieren (Dokumenttitel, Abschnitt, Upload-Datum, Highlight-Offset für US-01)
- [ ] Timeout-Wert für LLM-Call konfigurierbar machen (→ ADR-003, ConfigService)
- [ ] Retry-Logik im LLM-Adapter spezifizieren: 1 Retry mit wie viel Backoff?
