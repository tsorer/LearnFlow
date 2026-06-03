# ADR-004 · LLM-Provider-Wahl: Azure OpenAI Service oder Anthropic Claude API

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | LearnFlow Architecture Team |
| **Bezug** | US-01, US-02, QA-03 (Security), QA-04 (Reliability), Risiko 3 |
| **Abhängigkeit** | ADR-002 (LLMAdapter-Interface), ADR-005 (RAG-Stack / Embedding) |

---

## Kontext

LearnFlow schickt interne Unternehmensdokumente als Kontext an ein LLM. Das stellt die Wahl des Providers unter zwei Zwänge, die über reine Qualitäts- und Kostenüberlegungen hinausgehen:

**Datenschutz / Datenresidenz**: Jeder Prompt enthält Ausschnitte aus vertraulichen internen Dokumenten. Je nach Unternehmensstandort (CH/DE/AT) und interner IT-Policy kann die Übermittlung an einen US-amerikanischen API-Endpoint compliance-relevant sein.

**API-Quota** (Risiko 3): Quota-Anfragen bei Cloud-Providern können mehrere Wochen dauern. Die Provider-Entscheidung muss deshalb in Sprint 0 getroffen und die Quota-Anfrage sofort gestellt werden — nicht erst wenn die Story implementiert werden soll.

Das LLM-Adapter-Interface (ADR-002) stellt sicher, dass der Provider später ohne Änderung an der Business-Logik ausgetauscht werden kann. Diese ADR entscheidet den konkreten Provider für das MVP.

### Bewertungskriterien

| Kriterium | Gewicht | Begründung |
|---|---|---|
| Datenresidenz / DSGVO-Compliance | Hoch | Interne Dokumente im Prompt |
| RAG-Qualität (Long-Context, Präzision) | Hoch | Kernversprechen der Plattform |
| Quota-Verfügbarkeit für MVP | Hoch | Risiko 3 |
| Kosten (Token-Preis × geschätztes Volumen) | Mittel | 480h Budget, ~20 User |
| Streaming-Support | Mittel | p95 ≤ 10 s (QA-01) |
| Embedding-Verfügbarkeit beim selben Provider | Mittel | Vereinfacht ADR-005 |

---

## Entscheidung

**Zweistufige Empfehlung abhängig von der Compliance-Anforderung:**

### Pfad A · Azure OpenAI Service *(wenn Datenresidenz in EU/EWR gefordert)*

Azure OpenAI bietet dieselben Modelle (GPT-4o, GPT-4o-mini) über Microsoft-Infrastruktur in europäischen Rechenzentren an. Microsoft bietet einen EU-Datenverarbeitungsvertrag (DPA) nach Art. 28 DSGVO an.

**Empfohlene Modelle:**
- **GPT-4o-mini** — Hauptmodell für RAG-Antworten: niedrige Latenz, günstiger Token-Preis, ausreichende Qualität für strukturierte Dokumente
- **GPT-4o** — Fallback für komplexe, mehrstufige Kontextfragen

### Pfad B · Anthropic Claude API *(wenn US-Datenresidenz akzeptiert oder nicht relevant)*

Anthropic Claude 3.5 Sonnet / Claude 3.5 Haiku bieten hervorragende Qualität für Retrieval-gestützte Antwortgenerierung mit genauer Quellenreferenzierung.

**Empfohlene Modelle:**
- **Claude 3.5 Haiku** — Hauptmodell: sehr niedrige Latenz (p50 ~2–3 s), günstiger als Sonnet
- **Claude 3.5 Sonnet** — Fallback für komplexe Fragen, wenn Haiku-Qualität nicht ausreicht

> **Entscheidungsblockierer:** Die Compliance-Frage (Datenresidenz) muss durch die IT-/Legal-Abteilung des Unternehmens bis Ende Sprint 0 beantwortet werden. Bis dahin ist dieser ADR **Proposed**. Die technische Implementierung ist für beide Pfade identisch (LLM-Adapter-Interface, ADR-002).

### Gemeinsame Konfiguration (beide Pfade)

```typescript
// LLM-Adapter-Konfiguration (aus ADR-002)
interface LLMAdapter {
  complete(prompt: string, options?: CompletionOptions): Promise<Result<LLMResponse, LLMError>>
  stream(prompt: string, options?: CompletionOptions): AsyncIterable<string>
}

type CompletionOptions = {
  maxTokens?:   number    // Default: 1024
  temperature?: number    // Default: 0.1 (niedrig für faktische Antworten)
  timeoutMs?:   number    // aus ConfigService
}
```

```
LLMAdapter-Implementierungen:

  AzureOpenAIAdapter   implements LLMAdapter  [Pfad A]
  AnthropicAdapter     implements LLMAdapter  [Pfad B]
  MockLLMAdapter       implements LLMAdapter  [Tests]
```

### Modell-Konfiguration als Config-Parameter

```typescript
// config_params (→ ADR-003)
// 'llm_model'          : z.B. 'gpt-4o-mini' oder 'claude-3-5-haiku-20241022'
// 'llm_max_tokens'     : '1024'
// 'llm_temperature'    : '0.1'
// 'llm_timeout_ms'     : '15000'
```

Modellname und Timeout sind konfigurierbar ohne Code-Deployment — Provider-Wechsel innerhalb desselben Anbieters (z.B. Haiku → Sonnet) erfordert nur eine DB-Änderung.

### Kostenabschätzung MVP

| | Azure GPT-4o-mini | Claude 3.5 Haiku |
|---|---|---|
| Input (pro 1M Token) | ~$0.15 | ~$0.80 |
| Output (pro 1M Token) | ~$0.60 | ~$4.00 |
| Geschätzte Token/Anfrage | ~3 000 Input + ~500 Output | ~3 000 Input + ~500 Output |
| Kosten/Anfrage | ~$0.00075 | ~$0.0044 |
| Kosten bei 1 000 Anfragen/Monat | ~$0.75 | ~$4.40 |

Bei 20 Pilotusern ist das Kostenvolumen in beiden Fällen vernachlässigbar.

---

## Begründung

**Warum kein Self-Hosted / Lokales Modell (Llama 3, Mistral)?**

Self-hosted LLMs (Ollama, vLLM) eliminieren Datenschutzrisiken und API-Quota-Abhängigkeiten vollständig. Für das MVP mit 480 Stunden Budget ist der Betriebsaufwand (GPU-Infrastruktur, Modell-Updates, Monitoring) jedoch unverhältnismässig. Qualität von Open-Source-Modellen bei komplexen, deutschen Fachdomänen-Dokumenten ist noch nicht auf dem Niveau der Cloud-Anbieter.

**Upgrade-Pfad:** Falls Post-MVP Datenschutzkritikalität steigt, kann der LLM-Adapter auf ein lokales Modell umgestellt werden — ohne Änderung an Pipeline, Konfidenz-Scoring oder Config-Service.

**Warum nicht Google Gemini / Cohere?**

Google: EU-Datenresidenz via Vertex AI möglich, aber Komplexität ähnlich wie Azure. Geringere Team-Erfahrung typischerweise. Cohere: stark bei RAG/Embeddings, aber LLM-Qualität für deutsche Fachdokumente weniger erprobt.

**Warum kein direkter OpenAI-Zugang (ohne Azure)?**

OpenAI API ohne Azure bietet keine europäische Datenresidenz-Garantie. Wenn Compliance irrelevant ist, wäre OpenAI direkt einfacher als Azure — in dem Fall ist Anthropic Claude die gleichwertige Alternative.

---

## Betrachtete Alternativen

### Alternative 1 · OpenAI API direkt

Einfachster Einstieg, kein Azure-Setup. GPT-4o-mini günstiger als Claude Haiku.

**Zurückgestellt**: Kein EU-Datenresidenz-Angebot. Wenn Compliance keine Rolle spielt, technisch gleichwertig mit Pfad B (Anthropic) und kostengünstiger als Pfad A (Azure).

### Alternative 2 · Self-Hosted (Ollama + Llama 3.1 70B)

Keine externen Daten, keine API-Kosten, kein Quota-Problem.

**Abgelehnt für MVP**: GPU-Infrastruktur ausserhalb des 480h-Budgets. Qualität bei deutschen Fachdokumenten ungesichert. Betriebsaufwand für 1 FTE Maintenance zu hoch.

### Alternative 3 · Mistral AI (EU-Provider, Le Chat Enterprise)

Französischer Anbieter mit europäischer Datenresidenz. DSGVO-konform.

**Zurückgestellt**: Mistral-Modelle bei deutschen Domänentexten weniger evaluiert als GPT-4o oder Claude. Kleineres Ökosystem. Viable Post-MVP-Alternative wenn Azure-Komplexität ein Problem wird.

---

## Konsequenzen

### Positiv
- LLM-Adapter-Interface (ADR-002) hält Provider-Wahl vollständig aus Business-Logik heraus
- Modell kann ohne Deployment gewechselt werden (ConfigService, ADR-003)
- Streaming-Support in beiden Pfaden verfügbar — p95 ≤ 10 s erreichbar
- Kostenvolumen bei Pilot-Nutzung minimal

### Negativ / Risiken
- **Quota-Risiko** (Risiko 3): Azure OpenAI Quota-Anfragen können 2–4 Wochen dauern; Anthropic Pro/Team-Pläne sind schneller verfügbar. Quota-Anfrage muss sofort nach Entscheid gestellt werden.
- **API-Key-Verwaltung**: Key darf nie in Code, Logs oder DB erscheinen (→ QA-03 M10)
- **Latenz-Varianz**: Cloud-LLMs haben kein garantiertes p95-SLA. Eigenes Timeout (15 s) und Circuit Breaker (ADR-002) als Absicherung nötig
- **Pfad A (Azure)**: Setup-Aufwand höher als direkter API-Zugang (Ressourcen, Deployment-Regionen, API-Keys je Deployment)

---

## Abhängigkeiten

| Abhängigkeit | Typ | Hinweis |
|---|---|---|
| ADR-002 (LLMAdapter-Interface) | Vorausgesetzt | Provider wird hinter Interface gekapselt |
| ADR-003 (ConfigService) | Vorausgesetzt | Modellname, Timeout, Temperature als Config-Parameter |
| ADR-005 (RAG-Stack / Embedding) | Nachgelagert | Embedding-Provider-Wahl hängt vom LLM-Provider ab |
| Risiko 3 (Externe Abhängigkeiten) | Direkt | Quota-Anfrage blockiert ggf. Sprint-1-Start |
| Legal/IT-Abteilung | Entscheidungsträger | Compliance-Anforderung (Datenresidenz) bis Ende Sprint 0 |

---

## Offen / Nächste Schritte

- [ ] **Bis Ende Sprint 0:** Legal/IT bestätigt: Datenresidenz EU/EWR gefordert? → Pfad A (Azure) oder Pfad B (Anthropic)
- [ ] **Sofort nach Entscheid:** Quota-Anfrage beim gewählten Provider stellen
- [ ] Prompt-Template für RAG-Antworten mit Quellenangabe ausarbeiten und im Spike testen
- [ ] API-Key-Rotation-Prozess definieren (wer hat Zugriff, wie oft rotieren)
- [ ] Rate-Limit-Werte des gewählten Providers dokumentieren → Circuit-Breaker-Konfiguration (ADR-002) ableiten
