# LearnFlow Frontend – CLAUDE.md

Kontext für das Angular-Frontend. Ergänzt die root `CLAUDE.md`.

---

## Aufgabe dieses Moduls

Das Frontend liefert:
- Chat-UI (Frage stellen, Antwort mit Quellen anzeigen)
- Quellenanzeige mit Highlighting
- Feedback-Buttons (👍/👎 + Kategorie)
- Unsicherheits-Markierung bei niedrigem Konfidenz-Score
- Einfache Korpus-Status-Seite

---

## Verzeichnisstruktur

```
frontend/src/app/
├── core/
│   ├── services/
│   │   ├── qa.service.ts         ← HTTP-Calls an /api/qa
│   │   ├── feedback.service.ts   ← HTTP-Calls an /api/feedback
│   │   └── corpus.service.ts     ← HTTP-Calls an /api/corpus
│   └── models/
│       ├── qa.model.ts           ← QARequest, QAResponse (TS-Types)
│       └── feedback.model.ts
├── features/
│   ├── chat/
│   │   ├── chat.component.ts     ← Haupt-Chat-UI
│   │   └── message/
│   │       └── message.component.ts  ← Einzelne Nachricht + Quellen
│   ├── feedback/
│   │   └── feedback.component.ts
│   └── corpus-status/
│       └── corpus-status.component.ts
└── shared/
    └── components/               ← Wiederverwendbare UI-Elemente
```

---

## Wichtige Typen (müssen mit Backend-Models synchron bleiben)

```typescript
interface QAResponse {
  answer: string;
  sources: Source[];        // Niemals leer rendern
  confidence: number;       // 0.0 – 1.0
  is_uncertain: boolean;    // → UncertaintyBadge anzeigen
}

interface Source {
  document_id: string;
  title: string;
  excerpt: string;
  relevance_score: number;
}
```

---

## UI-Verhalten

| Zustand | Anzeige |
|---|---|
| `is_uncertain = true` | Gelbes Badge „Eingeschränkt belegt" |
| `sources` leer | Warnung anzeigen (sollte nie vorkommen) |
| API-Fehler | Freundliche Fehlermeldung, kein Stack-Trace |
| Laden | Skeleton-Loader im Chat |

---

## Wichtige Hinweise für Claude Code

- Kein HTTP direkt in Components – immer über Services
- Standalone Components (Angular 17+ Style)
- `environments/environment.ts` für API-URL (nicht hardcoden)
- `ng lint` und `ng test` müssen grün bleiben
- Keine direkte Azure OpenAI Anbindung im Frontend – alles über Backend-API
