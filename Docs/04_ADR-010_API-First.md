# ADR-010: API-Design-Ansatz — API-First mit OpenAPI 3.0

| Feld          | Inhalt                                |
| ------------- | ------------------------------------- |
| **Status**    | Accepted                              |
| **Datum**     | 2026-06-03                            |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

LearnFlow hat ein klar getrenntes Frontend (React/TypeScript) und Backend (FastAPI). Mit nur 4 Devs und 360 h Gesamtbudget ist paralleles Arbeiten an Frontend und Backend entscheidend — jede Wartezeit auf eine fertige Implementierung kostet Budget. Zudem wird der Code überwiegend KI-gestützt mit Claude Code generiert: ohne einen formalen Vertrag (Spec) fehlt der KI der Kontext um konsistente Typen, Fehlerformate und Endpointstrukturen zu generieren. Die OpenAPI Spec als maschinenlesbare Single Source of Truth löst beide Probleme gleichzeitig.

---

## Entscheidung

Wir verwenden **API-First**: Die OpenAPI 3.0 Spec (YAML) wird geschrieben bevor Backend-Implementierung oder Frontend-Integration beginnt. Die Spec ist die verbindliche Schnittstellen-Definition — Abweichungen in der Implementierung gelten als Fehler, nicht die Spec.

Die Spec wird als `openapi.yaml` im Projekt-Root versioniert und ist Teil jedes Pull Requests der Endpunkte hinzufügt oder ändert.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Frontend und Backend können parallel entwickeln — Frontend nutzt einen Mock-Server aus der Spec, bevor das Backend steht.
- **+** Claude Code erhält mit der Spec präzisen Kontext für Typen, Fehlerformate und Validierungsregeln → weniger halluzinierte APIs, weniger Korrekturrunden.
- **+** Automatisch generierbare TypeScript-Typen (Frontend) und Pydantic-Schemas (Backend) aus einer einzigen Quelle.
- **+** Swagger UI als interaktive Doku für alle Teammitglieder ohne zusätzlichen Aufwand.

### Negative Konsequenzen

- **−** Spec-Änderungen brauchen Abstimmung zwischen Frontend und Backend — kein «schnell mal Endpoint anpassen». Bewusst akzeptiert: das ist der Punkt.

---

## Abgewogene Alternativen

| Alternative                               | Warum verworfen                                                                                                                                                                    |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Code-First** (Spec aus Code generieren) | FastAPI kann Spec auto-generieren — aber dann ist die Implementierung der Vertrag, nicht die Spec. Für parallele Entwicklung ungeeignet: Frontend wartet auf fertiges Backend.     |
| **Kein formaler API-Vertrag**             | Bei KI-generiertem Code ohne Spec entstehen inkonsistente Endpunktstrukturen und Fehlerformate zwischen Modulen — Maintainability-NFA (austauschbare Komponenten) nicht erfüllbar. |
| **AsyncAPI**                              | Nicht relevant — kein SSE-Streaming im System (ADR-002, aktualisiert 2026-06-03). OpenAPI 3.0 deckt alle Batch-Response-Endpoints vollständig ab.                                  |

---

*Abhängigkeiten: ADR-002 (FastAPI generiert Spec auto — bewusst deaktiviert zugunsten Spec-First) · Ergebnis aus Modul 3 Tag 2 Übung 2*
