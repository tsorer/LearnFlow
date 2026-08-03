# ADR-003: LiteLLM als LLM-Provider-Abstraktion

| | |
|---|---|
| **Status** | Accepted |
| **Datum** | 2026-05-27 |
| **Projekt** | LearnFlow — interne RAG-basierte Lernplattform |

---

## Context

LearnFlow muss auf unterschiedlichen Infrastrukturen betreibbar sein: Cloud-Deployments nutzen Azure OpenAI oder Anthropic Claude; datenschutzkritische Unternehmen ohne Cloud-Erlaubnis benötigen ein OnPrem-Deployment (Ollama oder vLLM). Ein Provider-Wechsel darf keinen Code-Change erfordern.

Das Team verfügt über 320–480 Stunden Gesamtbudget. Jede Stunde für Provider-Migration fehlt in der Kernentwicklung. Der Tech Spike muss ausserdem A/B-Tests zwischen Providern mit identischer RAG-Pipeline ermöglichen, um Risiko 3 (Provider-Qualität und -Verfügbarkeit) empirisch zu adressieren.

**Wichtige Einschränkung:** LLM-Provider sind nicht qualitativ gleichwertig austauschbar. Claude und GPT-4o liefern messbar bessere Antwortqualität als Llama 3.2 (Ollama/OnPrem). Die Konfidenz-Schwellenwerte aus ADR-001 sind **modellspezifisch** — bei einem Provider-Wechsel ist eine Neukalibrierung zwingend. "Provider wechseln" bedeutet Konfigurations-Änderung; "Provider-Qualität erhalten" bedeutet separaten Tech Spike.

**Kritische Einschränkung — Embeddings:** LearnFlow ist ein RAG-System. Embeddings sind genauso Provider-abhängig wie LLM-Aufrufe. Alle in pgvector gespeicherten Vektoren sind spezifisch für das Embedding-Modell, mit dem sie erzeugt wurden. Bei einem Wechsel des Embedding-Modells werden **alle gespeicherten Vektoren ungültig** und müssen neu berechnet werden. Ein Provider-Wechsel ist daher kein nahtloser Vorgang, sondern erfordert ein vollständiges Re-Embedding des Korpus.

## Decision

Wir verwenden **LiteLLM** als einzige Schnittstelle zu allen LLM-Providern und **LiteLLM's Embedding-Interface** für alle Embedding-Aufrufe. LiteLLM stellt ein OpenAI-kompatibles Interface bereit.

Der aktive Provider wird durch Konfigurationseinträge gesteuert:

```
# LLM-Generierung
LLM_PROVIDER=claude             # Anthropic Claude (Cloud)
LLM_PROVIDER=azure/gpt-4o       # Azure OpenAI (Cloud, DSGVO-konform)
LLM_PROVIDER=ollama/llama3.2    # Ollama (OnPrem)

# Embeddings — separat konfiguriert, da Modellwechsel Re-Embedding erfordert
EMBEDDING_PROVIDER=azure/text-embedding-3-small
EMBEDDING_PROVIDER=ollama/nomic-embed-text
```

**Embedding-Wechsel-Protokoll:** Ein Wechsel des Embedding-Providers ist kein normaler Konfigurationsvorgang. Er erfordert: (1) Neues Embedding-Modell kalibrieren, (2) gesamten Korpus neu einbetten, (3) pgvector-Index neu aufbauen, (4) ADR-001-Schwellenwerte neu kalibrieren. Dieser Prozess muss dokumentiert und geplant werden — er ist kein Hotfix.

Der LLM-Client und der Embedding-Client werden **per Dependency Injection** in die RAG-Pipeline übergeben. Das ermöglicht Mock-Objekte in Unit Tests und Provider-Swap ohne Deployment.

**Streaming:** LiteLLM unterstützt Streaming (SSE). Die Streaming-Implementierung und das Fehlerverhalten unter Streaming-Abbruch müssen im Tech Spike pro Provider explizit validiert werden — Streaming-Verhalten ist provider-spezifisch und nicht durch die Abstraktion garantiert homogen.

**Nutzbare Portabilität:** LiteLLM abstrahiert den Aufruf — nicht das Verhalten. Timeout-Handling, Fehlertypen und Rate-Limit-Responses unterscheiden sich zwischen Providern. Provider-spezifischer Code an Fehlerbehandlungs-Stellen ist trotz LiteLLM unvermeidbar und muss explizit als solcher markiert werden.

**OnPrem-Empfehlung:** Für Unternehmens-OnPrem-Deployments mit GPU-Infrastruktur empfehlen wir **vLLM statt Ollama**: bessere Performance unter Last, GPU-optimiert, nativ OpenAI-kompatibel. Ollama ist für Entwicklungsumgebungen und ressourcenarme Deployments geeignet.

## Consequences

**Positiv**

- LLM-Provider-Wechsel durch Konfiguration — kein Code-Change, kein Deployment (unter Vorbehalt: Qualität und Schwellenwerte müssen separat validiert werden)
- Cloud vs. OnPrem: gleiche Codebase, unterschiedliche Konfiguration
- LLM- und Embedding-Abstraktion unter einer Bibliothek — einheitliches Interface für beide Aufruftypen
- A/B-Tests zwischen Providern mit unveränderter RAG-Pipeline im Tech Spike möglich
- Dependency Injection macht beide Clients in Unit Tests mockbar
- Minimaler Overhead, kein Framework-Magic

**Negativ**

- Provider-Wechsel des Embedding-Modells invalidiert alle gespeicherten Vektoren: vollständiges Re-Embedding des Korpus erforderlich — kein Hotfix, geplante Operation
- Konfidenz-Schwellenwerte (ADR-001) sind modellspezifisch: Provider-Wechsel erfordert Neukalibrierung durch Tech Spike
- LiteLLM ist eine externe Abhängigkeit mit aktiver Entwicklung: Breaking Changes sind realistisch und müssen mit Versionspinning und Changelog-Monitoring gemanagt werden
- Streaming-Verhalten ist provider-spezifisch — muss im Tech Spike pro Provider validiert werden
- Provider-spezifisches Fehlerverhalten erfordert trotz Abstraktion stellenweise provider-spezifischen Code
- OnPrem-Deployments mit Ollama/Llama 3.2 liefern schlechtere Antwortqualität als Cloud-Provider — das muss in der Nutzerkommunikation transparent gemacht werden
