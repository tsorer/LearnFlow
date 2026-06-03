# Architecture Decision Records — LearnFlow

ADRs dokumentieren signifikante Architekturentscheidungen: den Kontext, die Alternativen und die Begründung für den gewählten Ansatz.

## Status-Definitionen

| Status | Bedeutung |
|---|---|
| **Proposed** | Zur Review freigegeben, noch nicht beschlossen |
| **Accepted** | Beschlossen und verbindlich |
| **Superseded** | Abgelöst durch ein neueres ADR (Verweis angegeben) |
| **Deprecated** | Nicht mehr gültig, kein Nachfolger |

---

## Index

| ADR | Titel | Status | Priorität | Bezug |
|---|---|---|---|---|
| [ADR-001](ADR-001-konfidenz-scoring.md) | Konfidenz-Scoring: Strategy Pattern mit austauschbarem Scorer | Proposed | Hoch | US-02, M2 |
| [ADR-002](ADR-002-fail-safe-rag-pipeline.md) | Fail-Safe RAG-Pipeline: Discriminated Union als Ergebnistyp | Proposed | Hoch | US-01, US-02, M5 |
| [ADR-003](ADR-003-konfigurationsservice.md) | Konfigurationsservice: PostgreSQL mit In-Process-Cache und Audit-Log | Proposed | Hoch | US-11, M7 |
| [ADR-004](ADR-004-llm-provider.md) | LLM-Provider-Wahl: Azure OpenAI oder Anthropic Claude API | Proposed | **Blockierend** | US-01, Risiko 3 |
| [ADR-005](ADR-005-rag-stack.md) | RAG-Stack: pgvector + Multilinguales Embedding-Modell | Proposed | **Blockierend** | US-01, US-04, Risiko 1 |
| [ADR-006](ADR-006-authentifizierung.md) | Authentifizierungs-Strategie: JWT + HTTP-only Cookie, SSO-Ready | Proposed | Hoch | US-05, QA-03 |
| [ADR-007](ADR-007-frontend-framework.md) | Frontend-Framework: Next.js mit TypeScript und App Router | Proposed | Mittel | US-01, US-09, QA-05 |

---

## Abhängigkeitsgraph

```
ADR-007 (Frontend / Next.js)
    └── braucht TypeScript → bestätigt ADR-002 (Discriminated Union)
    └── koordiniert mit ADR-006 (Auth.js als Auth-Integration)

ADR-006 (Authentifizierung / JWT)
    └── koordiniert mit ADR-007 (Auth.js wenn Next.js)

ADR-005 (RAG-Stack / pgvector + Embedding)
    └── Retriever wird verwendet von ADR-002 (RAG-Pipeline)
    └── EmbeddingAdapter wird verwendet von ADR-001 (ConfidenceScorer)
    └── koordiniert mit ADR-004 (Datenresidenz → Embedding-Strategie)

ADR-004 (LLM-Provider / Azure oder Anthropic)
    └── LLMAdapter-Interface aus ADR-002 kapselt Provider
    └── beeinflusst ADR-005 (Embedding-Provider)

ADR-003 (ConfigService / PostgreSQL Cache)
    └── wird verwendet von ADR-001 (Schwellenwerte)
    └── wird indirekt verwendet von ADR-002 (via ADR-001)

ADR-001 (Konfidenz-Scoring / Strategy Pattern)
    └── wird verwendet von ADR-002 (RAG-Pipeline)
    └── verwendet ADR-003 (Schwellenwerte)
    └── verwendet ADR-005 (EmbeddingAdapter für SemanticScorer)

ADR-002 (RAG-Pipeline / Discriminated Union)
    └── verwendet ADR-001 (ConfidenceEvaluator)
    └── verwendet ADR-004 (LLMAdapter)
    └── verwendet ADR-005 (Retriever)
```

**Implementierungsreihenfolge (Sprint 0 → Sprint 1):**
```
ADR-004 entscheiden (Compliance-Frage) → Quota beantragen
ADR-005 Spike durchführen (Go/No-Go Risiko 1)
ADR-003 implementieren (Config-Tabellen, Seed)
ADR-006 implementieren (Auth, Login)
ADR-001 + ADR-002 implementieren (RAG-Pipeline)
ADR-007 implementieren (Frontend-Scaffolding)
```

---

## Offene Entscheidungsblockierer

| ADR | Blockierer | Verantwortlich | Frist |
|---|---|---|---|
| ADR-004 | Datenresidenz-Anforderung (EU/EWR?) von Legal/IT | Legal / IT | Ende Sprint 0 |
| ADR-004 | API-Quota-Anfrage beim gewählten Provider | Tech Lead | Sofort nach Entscheid |
| ADR-005 | RAG-Spike: Go/No-Go auf echten Dokumenten | Engineering | Vor Sprint 1 |
| ADR-006 | Auth.js vs. eigene JWT-Impl. (abhängig von ADR-007) | Engineering | Gleichzeitig mit ADR-007 |
