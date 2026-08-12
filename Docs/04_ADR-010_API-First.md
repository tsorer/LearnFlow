# ADR-010: API-Design-Ansatz — API-First mit OpenAPI 3.0

| Feld          | Inhalt                                |
| ------------- | ------------------------------------- |
| **Status**    | Accepted                              |
| **Datum**     | 2026-06-03                            |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

LearnFlow hat ein klar getrenntes Frontend (React/TypeScript) und Backend (FastAPI). Mit nur 4 Devs und 360 h Umsetzungsbudget ist paralleles Arbeiten an Frontend und Backend entscheidend — jede Wartezeit auf eine fertige Implementierung kostet Budget. Zudem wird der Code überwiegend KI-gestützt mit Claude Code generiert: ohne einen formalen Vertrag (Spec) fehlt der KI der Kontext um konsistente Typen, Fehlerformate und Endpointstrukturen zu generieren. Die OpenAPI Spec als maschinenlesbare Single Source of Truth löst beide Probleme gleichzeitig.

---

## Entscheidung

Wir verwenden **API-First**: Die OpenAPI 3.0 Spec (YAML) wird geschrieben bevor Backend-Implementierung oder Frontend-Integration beginnt. Die Spec ist die verbindliche Schnittstellen-Definition — Abweichungen in der Implementierung gelten als Fehler, nicht die Spec.

Die Spec wird als `src/backend/openapi.yaml` versioniert (dort im Backend-Container und damit in der CI per `openapi-spec-validator` prüfbar) und ist Teil jedes Pull Requests der Endpunkte hinzufügt oder ändert.

**Verbindlich in beide Richtungen, maschinell durchgesetzt (ergänzt 2026-08-12, T-39).** «Abweichungen gelten als Fehler» blieb bis dahin eine Absichtserklärung: das Frontend rief zwei Endpunkte auf, die nirgends deklariert waren, und die handgepflegten UI-Typen für `/query` hatten mit dem Spec-Schema kein einziges Feld gemeinsam. Drei Checks schliessen das:

| Richtung | Prüfung | Wo |
|---|---|---|
| Code → Spec | jede vom Backend ausgelieferte Route ist deklariert | `tests/test_rbac.py` |
| Spec → Code | jeder deklarierte Endpunkt wird ausgeliefert | `tests/test_rbac.py` |
| Spec → Frontend | die committeten TypeScript-Typen entsprechen der Spec | `npm run check` |

Daraus folgen zwei Regeln:

- **Der Frontend-Client wird vollständig aus der Spec typisiert** (`openapi-typescript` erzeugt `schema.d.ts`, `openapi-fetch` typisiert Pfad, Methode, Body und Antwort). Handgepflegte API-Typen sind damit ausgeschlossen — eine Vertragsänderung bricht den Build.
- **Ein deklarierter Endpunkt existiert immer**, notfalls als Platzhalter mit `501 Not Implemented` und einem `TODO`, das sein Ticket nennt. Bewusst kein Beispielinhalt: ADR-008 ist fail-closed, und eine erfundene Antwort mit erfundenen Quellenangaben ist genau das, was nie ausgeliefert werden darf. Der ehrliche `501` ist für das Frontend zudem unterscheidbar von «kaputt».

Der frühere Weg — Frontend gegen einen Mock-Server aus der Spec — entfällt damit: der Platzhalter im Backend *ist* der Mock, und er kann nicht von der Spec abweichen.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Frontend und Backend können parallel entwickeln — das Frontend arbeitet gegen den `501`-Platzhalter des Backends, der per Konstruktion zur Spec passt (kein separater Mock-Server, der auseinanderlaufen kann).
- **+** Claude Code erhält mit der Spec präzisen Kontext für Typen, Fehlerformate und Validierungsregeln → weniger halluzinierte APIs, weniger Korrekturrunden.
- **+** Automatisch generierbare TypeScript-Typen (Frontend) und Pydantic-Schemas (Backend) aus einer einzigen Quelle.
- **+** Swagger UI als interaktive Doku für alle Teammitglieder ohne zusätzlichen Aufwand.

### Negative Konsequenzen

- **−** Spec-Änderungen brauchen Abstimmung zwischen Frontend und Backend — kein «schnell mal Endpoint anpassen». Bewusst akzeptiert: das ist der Punkt.
- **−** Ein neuer Endpunkt kostet drei Artefakte statt einem (Spec, Platzhalter-Route, regenerierte Typen) und ist ohne alle drei nicht mergebar. Der Aufwand ist gering (`make generate-api`), aber er fällt bei *jeder* Schnittstellenänderung an.
- **−** Wer die Spec ändert, muss die Typen regenerieren, auch wenn er nur Backend macht. Dafür gibt es `make generate-api`, das dieselbe Container-Umgebung nutzt wie die CI — ein lokales Node ist nicht nötig.

---

## Abgewogene Alternativen

| Alternative                               | Warum verworfen                                                                                                                                                                    |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Code-First** (Spec aus Code generieren) | FastAPI kann Spec auto-generieren — aber dann ist die Implementierung der Vertrag, nicht die Spec. Für parallele Entwicklung ungeeignet: Frontend wartet auf fertiges Backend.     |
| **Kein formaler API-Vertrag**             | Bei KI-generiertem Code ohne Spec entstehen inkonsistente Endpunktstrukturen und Fehlerformate zwischen Modulen — Maintainability-NFA (austauschbare Komponenten) nicht erfüllbar. |
| **AsyncAPI**                              | Nicht relevant — kein SSE-Streaming im System (ADR-002, aktualisiert 2026-06-03). OpenAPI 3.0 deckt alle Batch-Response-Endpoints vollständig ab.                                  |

---

*Abhängigkeiten: ADR-002 (FastAPI generiert Spec auto — bewusst deaktiviert zugunsten Spec-First) · Ergebnis aus Modul 3 Tag 2 Übung 2*
