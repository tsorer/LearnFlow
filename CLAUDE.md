# CLAUDE.md — LearnFlow

> **Dieses File** enthält alle für das Projekt relevanten Informationen:
> Quick Reference → vollständiges Anforderungsdokument → alle 7 ADRs.

---

## Quick Reference

### MVP-Eckdaten

| | |
|---|---|
| **Deadline** | 30. September 2026 |
| **Budget** | 4 Personen × 15 Wochen × 1 Tag/Woche = 480 Stunden |
| **Pilot-Bereich** | 1 (hartcodiert) |
| **Sprache** | Deutsch |
| **Target** | Desktop-Browser |

### Tech-Stack

| Schicht | Entscheidung | ADR |
|---|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript | ADR-007 |
| BFF / API-Routes | Next.js API-Routes (Node.js) | ADR-007 |
| RAG-Backend | Python-Service (sentence-transformers, pdfplumber) | ADR-007 |
| LLM-Provider | Azure OpenAI (EU) **oder** Anthropic Claude — Compliance-Entscheid ausstehend | ADR-004 |
| Vektor-DB | pgvector (PostgreSQL-Extension) | ADR-005 |
| Embedding-Modell | multilingual-e5-large-instruct (lokal, MIT) | ADR-005 |
| Authentifizierung | JWT + HTTP-only Cookie, SSO-ready Interface | ADR-006 |
| Konfiguration | PostgreSQL + In-Process-Cache (TTL 30 s) + Audit-Log | ADR-003 |
| RAG-Ergebnistyp | Discriminated Union (TypeScript) | ADR-002 |
| Konfidenz-Scoring | Strategy Pattern (ConfidenceScorer Interface) | ADR-001 |

### Personas

- **Lara** — Lernende (Junior Developer): stellt Fragen, absolviert Quizze, gibt Feedback
- **Stefan** — Bereichsverantwortlicher: verwaltet Dokumente, prüft Quiz-Fragen, überwacht Wissenslücken
- **Admin** — konfiguriert Systemparameter über Admin-Seite

### User Stories (MoSCoW)

| ID | Titel | Priorität |
|---|---|---|
| US-01 | Quellenbelegte Frage-Antwort | **MUST** |
| US-02 | Unsichere Antworten erkennen | **MUST** |
| US-03 | Feedback zu Antworten | **MUST** |
| US-04 | Inhalte in den Lernkorpus aufnehmen | **MUST** |
| US-05 | Authentifizierung und Bereichszuordnung | **MUST** |
| US-06 | Veraltete Inhalte erkennen und re-validieren | **SHOULD** |
| US-07 | KI-generierte Quiz-Fragen prüfen und freigeben | **SHOULD** |
| US-08 | Quiz absolvieren | **SHOULD** |
| US-11 | Systemkonfiguration über Admin-Seite | **SHOULD** |
| US-09 | Folgefragen im Gesprächskontext | **COULD** |
| US-10 | Wissenslücken im Bereich erkennen | **COULD** |

### Konfigurierbare Parameter

| Parameter | Standard | Config-Key |
|---|---|---|
| Konfidenz-Schwellenwert | TBD nach Spike | `min_confidence_score` |
| Suppress-Schwellenwert | 0.50 | `suppress_threshold` |
| Limited-Schwellenwert | 0.80 | `limited_threshold` |
| Stale-Schwellenwert | 90 Tage | `stale_days` |
| LLM-Modell | per Provider | `llm_model` |
| LLM-Timeout | 15 000 ms | `llm_timeout_ms` |

### Konfidenz-Unterdrückung (Entscheid 2026-05-20, Vorrang-Reihenfolge)

1. **Quellenprüfung** — kein Retrieval-Treffer → `{ kind: 'no_source' }`
2. **Konfidenz-Score** — Score < `min_confidence_score` → `{ kind: 'dont_know', hint }`
3. **Self-Check-Anteil** — < 0.50 → `{ kind: 'suppressed' }` / < 0.80 → `{ kind: 'answer', label: 'limited' }`

### ADR-Implementierungsreihenfolge

```
ADR-004 entscheiden (Compliance-Frage) → Quota beantragen
ADR-005 Spike durchführen (Go/No-Go Risiko 1)
ADR-003 implementieren (Config-Tabellen, Seed)
ADR-006 implementieren (Auth, Login)
ADR-001 + ADR-002 implementieren (RAG-Pipeline)
ADR-007 implementieren (Frontend-Scaffolding)
```

### Offene Entscheidungsblockierer

| ADR | Blockierer | Frist |
|---|---|---|
| ADR-004 | Datenresidenz-Anforderung (EU/EWR?) von Legal/IT | Ende Sprint 0 |
| ADR-004 | API-Quota-Anfrage beim gewählten Provider | Sofort nach Entscheid |
| ADR-005 | RAG-Spike Go/No-Go auf echten Dokumenten | Vor Sprint 1 |
| ADR-006 | Auth.js vs. eigene JWT-Impl. (abhängig von ADR-007) | Gleichzeitig mit ADR-007 |

### Out of Scope (MVP)

- SSO / IdP-Anbindung
- Mehr als 1 Bereich
- Passwort-Reset UI / Self-Service-Registrierung
- Mobile / responsive UI
- Mehrsprachigkeit (nur Deutsch)
- Audit-Log für Dokument-Operationen
- DSGVO-Löschantrag-Workflow
- Diff-Ansicht bei Dokumenten-Updates

---

# Anforderungsdokument — LearnFlow Requirements v1

*Product Owner · Mai 2026*

---

## 1. Projektzusammenfassung

LearnFlow ist eine interne Lernplattform, die neuen Mitarbeitenden erlaubt, Fragen zu fachlichen Prozessen in natürlicher Sprache zu stellen und quellenbelegte Antworten aus einem kuratierten Wissenskorpus zu erhalten. Das Problem: Domänenwissen steckt in den Köpfen erfahrener Kolleg:innen und in verstreuten, schlecht gepflegten Dokumenten — neue Mitarbeitende werden nicht produktiv, Wissensträger werden täglich unterbrochen. Das MVP liefert einen lauffähigen Piloten für einen einzigen Bereich bis 30. September 2026 — kein Vollprodukt, sondern ein validiertes Fundament.

---

## 2. Personas

### Lara — Lernende

| | |
|---|---|
| **Job** | Junior Developer, erste Wochen im Unternehmen |
| **Problem** | Fachprozesse und historisch gewachsene Systeme sind nicht verständlich dokumentiert; das Wissen steckt bei erfahrenen Kolleg:innen |
| **Ziel** | Eigenständig Antworten zu Domänenfragen finden, ohne jedes Mal jemanden zu unterbrechen — und der Antwort vertrauen können |

### Stefan — Bereichsverantwortlicher

| | |
|---|---|
| **Job** | Senior-Mitarbeitender, fachlich verantwortlich für einen Bereich, Knowledge Owner |
| **Problem** | Neue Mitarbeitende stellen dieselben Fragen immer wieder; Dokumentation ist verstreut, veraltet, aufwändig zu pflegen |
| **Ziel** | Wissen einmalig aufbereiten und dauerhaft zugänglich halten, ohne täglich als Auskunftsperson gebraucht zu werden |

---

## 3. MVP-Constraints

| Constraint | Wert |
|---|---|
| Anzahl Bereiche | 1 (Pilot-Bereich, hartcodiert) |
| User-Management | DB-Script — kein Admin-UI; Felder: username, passwort, Rolle |
| Authentifizierung | Username / Passwort (lokal); post-MVP SSO via IdP |
| Rollen | Lernende / Bereichsverantwortlicher / Admin |
| Budget | 4 Personen × 15 Wochen × 1 Tag/Woche = 480 Stunden |
| Deadline | 30. September 2026 |

---

## 4. User Stories

### US-01 · Quellenbelegte Frage-Antwort

**Persona:** Lara

*Als Lernende möchte ich eine Frage in natürlicher Sprache stellen und eine quellenbelegte Antwort erhalten, damit ich Fachprozesse verstehen kann, ohne erfahrene Kolleg:innen zu unterbrechen.*

**Akzeptanzkriterien:**
- ✓ Jede Antwort enthält mindestens einen klickbaren Quellenverweis (Dokumenttitel + Abschnitt + Upload-Datum).
- ✓ Ein Klick auf eine Quellenangabe öffnet das Originaldokument und hebt den belegenden Abschnitt visuell hervor.
- ✓ Antworten ohne identifizierbare Quelle werden nicht angezeigt.
- ✓ Eingaben unter 3 Zeichen oder über 1.000 Zeichen werden clientseitig abgewiesen mit einem verständlichen Hinweis.
- ✓ Ist der LLM- oder Retrieval-Service nicht erreichbar, erscheint eine klare Fehlermeldung — keine erfundene Antwort.
- ✓ Antwortzeit im 95. Perzentil maximal 10 Sekunden.

---

### US-02 · Unsichere Antworten erkennen

**Persona:** Lara

*Als Lernende möchte ich klar erkennen, wenn das System sich seiner Antwort nicht sicher ist, damit ich keinen halluzinierten Inhalten vertraue.*

**Akzeptanzkriterien:**
- ✓ Unterschreitet der Konfidenz-Score einen konfigurierten Schwellenwert, zeigt das System: „Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden."
- ✓ Nach „Ich weiss es nicht" gibt das System einen Hinweis zur Präzisierung (z. B. „Versuche, einen konkreten Prozess oder ein Dokument zu nennen").
- ✓ Liegt der Anteil belegter Aussagen im Self-Check unter 80 %, wird die Antwort als „Eingeschränkt belegt" markiert (Farbe + Icon + Hinweistext).
- ✓ Liegt der Anteil unter 50 %, wird die Antwort vollständig unterdrückt.
- ✓ Der Konfidenz-Score ist in der Antwort-Metainfo einsehbar.
- ✓ Schwellenwert ist per DB-Script oder Admin-Seite (US-11) änderbar — kein Code-Deployment erforderlich.
- ✓ Das System gibt bei Out-of-Corpus-Testfragen in mindestens 90 % der Fälle „Weiss ich nicht" zurück.

> **Entscheid 2026-05-20:** Vorrang-Reihenfolge: (1) Quellenprüfung (US-01) — keine identifizierbare Quelle → Antwort wird nicht angezeigt. (2) Konfidenz-Score-Schwellenwert — Score zu tief → „Ich weiss es nicht". (3) Self-Check-Anteil — unter 80 % → „Eingeschränkt belegt"; unter 50 % → unterdrückt.

---

### US-03 · Feedback zu Antworten geben

**Persona:** Lara

*Als Lernende möchte ich jede Antwort als hilfreich oder nicht hilfreich markieren und einen Grund angeben, damit unklare oder falsche Antworten erkannt werden können.*

**Akzeptanzkriterien:**
- ✓ Jede Antwort enthält eine Bewertungsmöglichkeit (👍 / 👎).
- ✓ Bei 👍: Kategorie wählen — verständlich / vollständig / hilfreich für Code / Quelle passt gut.
- ✓ Bei 👎: Kategorie wählen — faktisch falsch / unvollständig / veraltet / unverständlich / Quelle stimmt nicht.
- ✓ Optional: Freitext-Ergänzung bei beiden Varianten.
- ✓ Nach dem Speichern: Bestätigung für Lara; Feedback erscheint im Dashboard von Stefan.
- ✓ Feedback wird pseudonymisiert erfasst — keine Rückverfolgung auf einzelne Lernende.

---

### US-04 · Inhalte in den Lernkorpus aufnehmen

**Persona:** Stefan

*Als Bereichsverantwortlicher möchte ich Dokumente in den Lernkorpus meines Bereichs aufnehmen können, damit nur von mir verwaltete Inhalte als Wissensgrundlage für KI-Antworten dienen.*

**Akzeptanzkriterien:**
- ✓ Upload in den Formaten PDF, Word (.docx) und Markdown.
- ✓ Dokumente bis 50 Seiten / 10 MB sind nach maximal 5 Minuten als Quelle verfügbar.
- ✓ Maximale Dateigrösse: 100 MB; Dateien über 100 MB werden mit einer Fehlermeldung abgewiesen.
- ✓ Alle hochgeladenen Dokumente zeigen eine Fortschrittsanzeige während der Verarbeitung.
- ✓ Eine neue Version (gleicher Dateiname) ersetzt automatisch das bestehende Dokument.
- ✓ Stefan kann ein Dokument jederzeit löschen.
- ✓ Hochgeladene Dokumente erhalten einen Zeitstempel, der für Lara sichtbar ist.
- ✓ Nur Dokumente des eigenen Bereichs sind sichtbar und verwaltbar.

---

### US-05 · Authentifizierung und Bereichszuordnung

**Persona:** Lara & Stefan

*Als Plattformnutzer:in möchte ich mich sicher anmelden und automatisch den Bereich sehen, dem ich zugeordnet bin, damit nur autorisierte Mitarbeitende Zugang haben.*

**Akzeptanzkriterien:**
- ✓ Authentifizierung per Username/Passwort; Accounts per DB-Script angelegt (Felder: username, passwort, Rolle: Lernende / Bereichsverantwortlicher / Admin) — keine Self-Service-Registrierung.
- ✓ Post-MVP: SSO-Anbindung via Unternehmens-IdP (z. B. Azure AD / SAML 2.0).
- ✓ Nicht authentifizierte Nutzer werden auf die Login-Seite weitergeleitet.
- ✓ Nach dem Login sieht jede Person den Pilot-Bereich (hartcodiert).
- ✓ Rollen werden beim Account-Anlegen gesetzt; post-MVP aus dem IdP übernommen.

---

### US-06 · Veraltete Inhalte erkennen und re-validieren

**Persona:** Stefan

*Als Bereichsverantwortlicher möchte ich eine Übersicht über veraltete Inhalte erhalten und diese aktiv re-validieren können, damit der Lernkorpus stets aktuell bleibt.*

**Akzeptanzkriterien:**
- ✓ Dashboard zeigt alle Dokumente, die seit mehr als 90 Tagen nicht re-validiert wurden, sortiert nach Alter.
- ✓ Stefan kann einen Eintrag als „aktuell", „ersetzt durch …" oder „entfernen" markieren.
- ✓ Stale-Schwellenwert (Standard: 90 Tage) ist per DB-Script oder Admin-Seite (US-11) änderbar.

> **Entscheid 2026-05-20:** Die Stale-Uhr wird zurückgesetzt durch (a) Upload eines Dokuments und (b) explizite Re-Validierung per Klick im Dashboard.

---

### US-07 · KI-generierte Quiz-Fragen prüfen und freigeben

**Persona:** Stefan

*Als Bereichsverantwortlicher möchte ich vom LLM vorgeschlagene Multiple-Choice-Fragen prüfen und freigeben oder ablehnen, damit nur validierte Quizfragen verwendet werden.*

**Akzeptanzkriterien:**
- ✓ Stefan löst die Quiz-Generierung manuell per Klick aus.
- ✓ Review-Dashboard zeigt alle nicht freigegebenen Fragen inklusive Quellen-Passage.
- ✓ Fragen können einzeln freigegeben, abgelehnt oder editiert werden.
- ✓ Abgelehnte Fragen sind für Lernende nicht sichtbar.
- ✓ Freigegebene Fragen erhalten einen Zeitstempel.

**Abhängigkeit:** US-04

---

### US-08 · Quiz absolvieren

**Persona:** Lara

*Als Lernende möchte ich zu einem Thema ein kurzes Quiz absolvieren, damit ich überprüfen kann, ob ich das Gelesene wirklich verstanden habe.*

**Akzeptanzkriterien:**
- ✓ Quiz mit 5 Multiple-Choice-Fragen aus dem Pool freigegebener Quizfragen pro Bereich.
- ✓ Sind keine Quizfragen freigegeben: Button sichtbar mit Hinweis „Es sind noch keine Quizfragen für diesen Bereich freigegeben."
- ✓ Nach Abschluss: pro Frage richtig/falsch, korrekte Antwort mit Erklärung und Direktlink zur belegenden Quelle.
- ✓ Quiz-Ergebnisse werden nicht personenbezogen gespeichert.

**Abhängigkeit:** US-07

---

### US-09 · Folgefragen im Gesprächskontext

**Persona:** Lara

*Als Lernende möchte ich nach einer Antwort Folgefragen im gleichen Kontext stellen können, damit ich ein Thema schrittweise vertiefen kann.*

**Akzeptanzkriterien:**
- ✓ Max. 3 vorherige Frage-Antwort-Paare fliessen als Kontext in Folgefragen ein.
- ✓ Gesprächshistorie der Session ist für Lara sichtbar (Scroll-Verlauf).
- ✓ Lara kann jederzeit eine neue Konversation starten (Context reset).
- ✓ Gesprächshistorie gilt nur für die aktive Browser-Session; beim Schliessen des Browsers verworfen.

---

### US-10 · Wissenslücken im Bereich erkennen

**Persona:** Stefan

*Als Bereichsverantwortlicher möchte ich sehen, welche Fragen häufig gestellt werden oder oft negatives Feedback erhalten, damit ich gezielt Dokumentation ergänzen kann.*

**Akzeptanzkriterien:**
- ✓ Dashboard zeigt Top-10-Themen-Cluster (Embedding-Ähnlichkeit) mit Häufigkeit und aggregierter Feedback-Quote — sobald konfigurierter Schwellenwert erreicht (Standard: 30 Tage / mind. 20 Fragen).
- ✓ Cluster mit weniger als 5 Fragen werden nicht angezeigt (Datenschutz).
- ✓ Klick auf Cluster zeigt Beispielfragen und verwendete Quellen.
- ✓ Direkt aus dem Cluster-Detail: Upload oder Re-Validierung anstossen.

---

### US-11 · Systemkonfiguration über Admin-Seite

**Persona:** Admin

*Als Admin möchte ich Systemparameter über eine geschützte Seite anpassen können, damit ich Konfidenz- und Stale-Schwellenwerte ohne Code-Deployment ändern kann.*

**Akzeptanzkriterien:**
- ✓ Konfidenz-Schwellenwert (US-02) und Stale-Schwellenwert (US-06) über Admin-Seite anpassbar; Änderungen wirken sofort ohne Neustart.
- ✓ Beide Werte alternativ per DB-Script änderbar (Fallback).
- ✓ Konfigurationsänderungen werden mit Zeitstempel und ausführender Person protokolliert.
- ✓ Admin-Seite nur für Admin-Rolle erreichbar; direkter URL-Aufruf ohne Admin-Rechte wird abgewiesen.

---

## 5. MoSCoW-Tabelle

| Story | Titel | Priorität | Begründung |
|---|---|---|---|
| US-01 | Quellenbelegte Frage-Antwort | **MUST** | Kernfunktion; ohne quellenbelegte Antworten ist das Vertrauensversprechen nicht einlösbar |
| US-02 | Unsichere Antworten erkennen | **MUST** | Eine falsch dargestellte Antwort ist schlimmer als gar keine — Fundament des Nutzervertrauens |
| US-03 | Feedback zu Antworten | **MUST** | Ohne Feedback-Loop keine Grundlage für Qualitätskontrolle oder Verbesserungen |
| US-04 | Inhalte aufnehmen | **MUST** | Ohne Korpus-Verwaltung keine Wissensbasis — Voraussetzung für alle anderen Stories |
| US-05 | Authentifizierung | **MUST** | Interne Dokumente ohne Zugangskontrolle sind nicht akzeptabel |
| US-06 | Veraltete Inhalte erkennen | **SHOULD** | Wichtig für langfristige Qualität, aber Pilot kann ohne starten |
| US-07 | Quiz-Fragen prüfen | **SHOULD** | Differenzierendes Feature; für Day-1-Nutzwert nicht blockierend |
| US-08 | Quiz absolvieren | **SHOULD** | Lernpädagogisch wertvoll; setzt US-07 voraus und ist im MVP nicht kritisch |
| US-11 | Systemkonfiguration Admin | **SHOULD** | DB-Script-Fallback vorhanden; Admin-UI ist Komfort, kein Blocker |
| US-09 | Folgefragen im Kontext | **COULD** | Verbessert UX erheblich, erhöht aber Komplexität (Token-Management, Kosten) |
| US-10 | Wissenslücken erkennen | **COULD** | Braucht ausreichend Nutzungsdaten; im Pilotbetrieb noch nicht sinnvoll |

---

## 6. Top 3 Risiken

### Risiko 1 · RAG-Qualität ist nicht garantierbar

Das Kernversprechen — verlässliche, quellenbelegte Antworten — hängt an einem Mechanismus (Retrieval + LLM), dessen Qualität stark von Chunking-Strategie, Embedding-Modell und Prompt-Design abhängt. Ein technischer Spike mit echten Dokumenten und echten Testfragen muss **vor** Implementierungsbeginn zeigen, ob das Qualitätsniveau erreichbar ist.

**Was zu klären ist:** Evaluationsdataset definieren, Qualitätsschwelle festlegen, Spike-Ergebnis als Go/No-Go-Entscheidung behandeln.

### Risiko 2 · Konfidenz-Scoring ist undefiniert

US-02 enthält mehrere Unterdrückungsmechanismen (Konfidenz-Score vs. Self-Check-Anteil) die nicht reconciliert sind. Welcher hat Vorrang? Was ist der Self-Check konkret — LLM-Selbstevaluation oder semantische Ähnlichkeit?

**Was zu klären ist:** Einen einzigen, definierten Mechanismus festlegen (→ ADR-001).

### Risiko 3 · Externe Abhängigkeiten blockieren zum falschen Zeitpunkt

(a) LLM-API-Quota — Anfragen können Wochen dauern, Stack-Entscheidung ist noch offen (→ ADR-004). (b) E-Mail-Service für US-06 — kein Mail-Provider definiert.

**Was zu klären ist:** LLM-Provider und Quota bis Ende Sprint 0 bestätigt; Mail-Service vor US-06.

---

## 7. Out of Scope — Won't Have im MVP

| Feature | Begründung |
|---|---|
| SSO / IdP-Anbindung | Post-MVP explizit geplant (US-05) |
| Mehr als 1 Bereich | Multi-Bereich erfordert vollständiges RBAC-Redesign |
| Passwort-Reset UI | Reset per DB-Script durch Admin |
| Self-Service-Registrierung | Accounts nur per DB-Script |
| Audit-Log für Dokument-Operationen | Post-MVP |
| Mehrsprachigkeit | Nur Deutsch im MVP |
| DSGVO-Löschantrag-Workflow | Post-MVP |
| Diff-Ansicht bei Dokumenten-Updates | Post-MVP (US-06) |
| Mobile / responsive UI | Desktop-Browser als einziges Target |

*Stand: v1 — 2026-05-20*

---

# Architecture Decision Records

---

## ADR-001 · Konfidenz-Scoring: Strategy Pattern mit austauschbarem Scorer

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | Christoph A. Amstutz, MD-PhD |
| **Bezug** | US-02, QA-06 (Testability), QA-04 (Reliability) |
| **Massnahme** | M2 |
| **Abhängigkeit** | ADR-003 (ConfigService), ADR-002 (RAG-Pipeline) |

### Kontext

US-02 schreibt eine dreistufige Unterdrückungslogik vor (Entscheid 2026-05-20):

1. **Quellenprüfung** — kein Retrieval-Treffer → Antwort nicht anzeigen
2. **Konfidenz-Score** — Score unter Schwellenwert → „Ich weiss es nicht"
3. **Self-Check-Anteil** — unter 80 % → „Eingeschränkt belegt"; unter 50 % → unterdrückt

Risiko 2: *wie* der Self-Check-Anteil berechnet wird, ist offen. Die zwei diskutierten Mechanismen — semantische Ähnlichkeit (Antwort-Sätze vs. Chunks) vs. LLM-Selbstevaluation — haben unterschiedliche Qualitäts- und Kostenprofile. Der gewählte Algorithmus muss nachträglich austauschbar bleiben.

### Entscheidung

**Strategy Pattern**: `ConfidenceScorer`-Interface kapselt ausschliesslich die Self-Check-Berechnung. `ConfidenceEvaluator` enthält die unveränderliche Stufenlogik und nimmt `ConfidenceScorer` sowie `ConfigService` als injizierte Abhängigkeiten.

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

```typescript
interface ConfidenceScorer {
  computeSelfCheckRatio(
    llmResponse: string,
    retrievalChunks: Chunk[]
  ): Promise<number>  // 0.0 – 1.0
}

type AnswerDecision =
  | { kind: 'NO_SOURCE'  }
  | { kind: 'DONT_KNOW'; hint: string }
  | { kind: 'SUPPRESSED' }
  | { kind: 'LIMITED'    }
  | { kind: 'OK'         }

class ConfidenceEvaluator {
  constructor(private scorer: ConfidenceScorer, private config: ConfigService) {}

  async evaluate(hits: Chunk[], score: number, response: string): Promise<AnswerDecision> {
    const t = await this.config.getThresholds()
    if (hits.length === 0) return { kind: 'NO_SOURCE' }
    if (score < t.minConfidenceScore)
      return { kind: 'DONT_KNOW', hint: 'Versuche, einen konkreten Prozess oder ein Dokument zu nennen.' }
    const ratio = await this.scorer.computeSelfCheckRatio(response, hits)
    if (ratio < t.suppressThreshold) return { kind: 'SUPPRESSED' }
    if (ratio < t.limitedThreshold)  return { kind: 'LIMITED' }
    return { kind: 'OK' }
  }
}
```

**MVP-Scorer:** `SemanticSimilarityScorer` — jeder Satz der LLM-Antwort wird vektorisiert, Cosinus-Ähnlichkeit zu Retrieval-Chunks berechnet. Überschreitet ein Satz den Schwellenwert, gilt er als „belegt". Self-Check-Anteil = belegte Sätze / Gesamtsätze.

### Konsequenzen

**Positiv:** Self-Check-Algorithmus ohne Änderung der Stufenlogik austauschbar. `FixedRatioScorer` + `InMemoryConfigService` ermöglicht vollständige Unit-Tests. Keine Magic-Number-Schwellenwerte im Code.

**Risiken:** `SemanticSimilarityScorer` hat konzeptionellen Zirkelschluss-Bias (LLM paraphrasiert Chunks → Ähnlichkeit immer hoch). Qualität erst durch RAG-Evaluierungs-Harness validierbar. Sentence-Splitting für Deutsch unspezifiziert.

### Offene Punkte

- [ ] Spike: `SemanticSimilarityScorer` gegen Evaluierungs-Dataset ausführen (Go/No-Go für Risiko 1+2)
- [ ] Konkrete Cosinus-Ähnlichkeitsschwelle für „Satz gilt als belegt" definieren
- [ ] `selfCheckRatio` im Response-Objekt für Lara sichtbar oder nur intern?
- [ ] Erster `evaluator.evaluate()`-Aufruf mit leerem `response`-String: Randfall definieren

---

## ADR-002 · Fail-Safe RAG-Pipeline: Discriminated Union als Ergebnistyp

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | Christoph A. Amstutz, MD-PhD |
| **Bezug** | US-01, US-02, QA-04 (Reliability), QA-06 (Testability) |
| **Massnahme** | M5 |
| **Abhängigkeit** | ADR-001 (ConfidenceEvaluator), ADR-004 (LLMAdapter), ADR-005 (Retriever) |

### Kontext

An jedem Pipeline-Schritt kann ein anderer Fehler auftreten, der eine andere UI-Reaktion erfordert. Das Requirements-Dokument formuliert explizit: *„Eine falsch dargestellte Antwort ist schlimmer als gar keine."* Jeder Fehlerpfad muss zu einem definierten, sicheren Ergebnis führen — nicht zu einer unbehandelten Exception oder einem stillen Fehler.

### Entscheidung

Die RAG-Pipeline gibt **immer** einen explizit typisierten `RAGResult`-Wert zurück. Exceptions werden nur für echte Programmierfehler verwendet, nicht als Kontrollfluss.

```typescript
type RAGResult =
  | { kind: 'answer'; content: string; sources: Source[]; confidence: number; label: 'ok' | 'limited' }
  | { kind: 'dont_know'; hint: string }
  | { kind: 'no_source'  }
  | { kind: 'suppressed' }
  | { kind: 'unavailable'; message: string }
  | { kind: 'timeout'    }

type LLMError =
  | { kind: 'timeout'   }
  | { kind: 'api_error'; statusCode: number; detail: string }
  | { kind: 'rate_limit' }

type Result<T, E> = { ok: true; value: T } | { ok: false; error: E }

interface LLMAdapter {
  complete(prompt: string): Promise<Result<LLMResponse, LLMError>>
  stream(prompt: string): AsyncIterable<string>
}
```

```typescript
async function runRAGPipeline(question: string): Promise<RAGResult> {
  const hits = await retriever.search(question)

  const score    = computeRetrievalScore(hits)
  const decision = await evaluator.evaluate(hits, score, '')
  if (decision.kind === 'NO_SOURCE') return { kind: 'no_source' }
  if (decision.kind === 'DONT_KNOW') return { kind: 'dont_know', hint: decision.hint }

  const llmResult = await llmAdapter.complete(buildPrompt(question, hits))
  if (!llmResult.ok) {
    return llmResult.error.kind === 'timeout'
      ? { kind: 'timeout' }
      : { kind: 'unavailable', message: 'KI-Service vorübergehend nicht erreichbar.' }
  }

  const finalDecision = await evaluator.evaluate(hits, score, llmResult.value.text)
  switch (finalDecision.kind) {
    case 'SUPPRESSED': return { kind: 'suppressed' }
    case 'LIMITED':
      return { kind: 'answer', content: llmResult.value.text,
               sources: extractSources(hits), confidence: score, label: 'limited' }
    case 'OK':
      return { kind: 'answer', content: llmResult.value.text,
               sources: extractSources(hits), confidence: score, label: 'ok' }
    default:
      return { kind: 'unavailable', message: 'Unerwarteter Systemzustand.' }
  }
}
```

**Exhaustiveness im UI-Controller** (TypeScript erzwingt vollständige Behandlung aller Varianten):

```typescript
function renderResult(result: RAGResult): ReactNode {
  switch (result.kind) {
    case 'answer':      return result.label === 'limited'
                          ? <LimitedAnswerCard content={result.content} sources={result.sources} />
                          : <AnswerCard content={result.content} sources={result.sources} />
    case 'dont_know':   return <DontKnowCard hint={result.hint} />
    case 'no_source':   return <NoSourceCard />
    case 'suppressed':  return <NoSourceCard />
    case 'unavailable': return <ErrorCard message={result.message} />
    case 'timeout':     return <ErrorCard message="Zeitüberschreitung — bitte erneut versuchen." />
  }
}
```

### Konsequenzen

**Positiv:** Compiler erzwingt vollständige Fehlerbehandlung. Jede Variante ist ohne Netzwerk testbar. Neue Fehlerzustände (z.B. `content_policy_violation`) erzwingen Behandlung an allen Stellen.

**Risiken:** Python-Backend hat keine native Discriminated-Union-Garantie — HTTP-Contract muss explizit definiert werden. `computeRetrievalScore()` ist im ADR undefiniert (black box). Retry-Logik (Anzahl, Backoff) unspezifiziert.

### Offene Punkte

- [ ] HTTP-Contract Next.js ↔ Python definieren: OpenAPI-Spec oder TypeScript-Types
- [ ] `Source`-Typ definieren (Titel, Abschnitt, Upload-Datum, Highlight-Offset)
- [ ] `computeRetrievalScore(hits)` spezifizieren (max/avg Cosinus-Similarity?)
- [ ] Retry-Logik im LLM-Adapter: 1 Retry mit wie viel Backoff?
- [ ] `content_policy_violation` als MVP-Variante evaluieren

---

## ADR-003 · Konfigurationsservice: PostgreSQL mit In-Process-Cache und Audit-Log

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | Christoph A. Amstutz, MD-PhD |
| **Bezug** | US-02, US-06, US-11, QA-04 (Reliability), QA-05 (Maintainability) |
| **Massnahme** | M7 |
| **Abhängigkeit** | ADR-001 (ConfidenceEvaluator liest Schwellenwerte) |

### Kontext

US-11 MUST: Konfigurationsparameter änderbar ohne Code-Deployment und ohne Neustart. ENV-Variablen werden beim Prozessstart eingelesen und scheiden damit aus.

### Entscheidung

Config-Parameter in PostgreSQL, `ConfigService` mit In-Process-Cache (TTL = 30 s) und sofortiger Invalidierung beim Schreiben. Alle Schreiboperationen transaktionssicher ins Audit-Log.

```sql
CREATE TABLE config_params (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO config_params (key, value) VALUES
  ('min_confidence_score', '0.65'),
  ('suppress_threshold',   '0.50'),
  ('limited_threshold',    '0.80'),
  ('stale_days',           '90');

CREATE TABLE config_audit_log (
  id         BIGSERIAL   PRIMARY KEY,
  key        TEXT        NOT NULL,
  old_value  TEXT,
  new_value  TEXT        NOT NULL,
  changed_by TEXT        NOT NULL,   -- Username als Text, kein FK (User könnte gelöscht werden)
  changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Keine DELETE/TRUNCATE-Rechte für App auf config_audit_log
```

```typescript
interface ConfigService {
  get(key: string): Promise<string>
  getNumber(key: string): Promise<number>
  getThresholds(): Promise<ConfidenceThresholds>
  set(key: string, value: string, changedBy: string): Promise<void>
}

type ConfidenceThresholds = {
  minConfidenceScore: number
  suppressThreshold:  number
  limitedThreshold:   number
}

class DBConfigService implements ConfigService {
  private cache = new Map<string, { value: string; expiresAt: number }>()
  private readonly TTL_MS = 30_000

  async get(key: string): Promise<string> {
    const cached = this.cache.get(key)
    if (cached && Date.now() < cached.expiresAt) return cached.value
    const row = await this.db.queryOne<{ value: string }>(
      'SELECT value FROM config_params WHERE key = $1', [key]
    )
    if (!row) throw new ConfigKeyNotFoundError(key)
    this.cache.set(key, { value: row.value, expiresAt: Date.now() + this.TTL_MS })
    return row.value
  }

  async set(key: string, newValue: string, changedBy: string): Promise<void> {
    const oldValue = await this.get(key).catch(() => null)
    await this.db.transaction(async (tx) => {
      await tx.execute('UPDATE config_params SET value = $1, updated_at = now() WHERE key = $2', [newValue, key])
      await tx.execute('INSERT INTO config_audit_log (key, old_value, new_value, changed_by) VALUES ($1,$2,$3,$4)',
        [key, oldValue, newValue, changedBy])
    })
    this.cache.delete(key)  // sofortige Invalidierung
  }
}

class InMemoryConfigService implements ConfigService {
  private store: Map<string, string>
  constructor(overrides: Record<string, string> = {}) {
    this.store = new Map({
      'min_confidence_score': '0.65', 'suppress_threshold': '0.50',
      'limited_threshold': '0.80', 'stale_days': '90', ...overrides
    })
  }
}
```

### Konsequenzen

**Positiv:** Keine neue Infrastrukturkomponente. Audit-Log transaktionssicher. `InMemoryConfigService` ermöglicht Tests ohne DB.

**Risiken:** Multi-Instance: bis zu 30 s Inkonsistenz (MVP: Single-Instance, akzeptabel). DB-Ausfall bei leerem Cache → kein Fallback definiert. `set()` validiert Werte nicht (Range-Check, Konsistenzcheck `limited > suppress` fehlt). Race condition bei `oldValue`-Lesen ausserhalb Transaktion.

### Offene Punkte

- [ ] Initiale Schwellenwerte nach RAG-Spike in Seed-Migration eintragen
- [ ] Validierung in `set()`: Range-Check + Konsistenz `limited_threshold > suppress_threshold`
- [ ] Kaltstart-Fallback bei leerem Cache und DB-Ausfall (hardcodierte Defaults?)
- [ ] `old_value` innerhalb der Transaktion lesen (`SELECT FOR UPDATE`) für Race-Condition-Schutz

---

## ADR-004 · LLM-Provider-Wahl: Azure OpenAI Service oder Anthropic Claude API

| | |
|---|---|
| **Status** | Proposed — **BLOCKIEREND** |
| **Datum** | 2026-05-27 |
| **Autor** | Christoph A. Amstutz, MD-PhD |
| **Bezug** | US-01, US-02, QA-03 (Security), QA-04 (Reliability), Risiko 3 |
| **Abhängigkeit** | ADR-002 (LLMAdapter-Interface), ADR-005 (RAG-Stack / Embedding) |

### Kontext

LearnFlow schickt interne Unternehmensdokumente als Kontext an ein LLM. Compliance-Zwang: DSGVO-Datenresidenz kann US-amerikanische Endpoints ausschliessen. API-Quota-Anfragen dauern 2–4 Wochen → Entscheid muss Sprint 0 erfolgen.

### Entscheidung

**Zweistufige Empfehlung abhängig vom Compliance-Entscheid:**

**Pfad A · Azure OpenAI** *(wenn EU/EWR-Datenresidenz gefordert)*
- Modell primär: GPT-4o-mini (niedrige Latenz, günstig)
- Modell fallback: GPT-4o (komplexe Fragen)
- Datenverarbeitungsvertrag Art. 28 DSGVO vorhanden

**Pfad B · Anthropic Claude** *(wenn US-Datenresidenz akzeptiert)*
- Modell primär: Claude 3.5 Haiku (p50 ~2–3 s, günstig)
- Modell fallback: Claude 3.5 Sonnet

```typescript
// config_params:
// 'llm_model'       → 'gpt-4o-mini' | 'claude-3-5-haiku-20241022'
// 'llm_max_tokens'  → '1024'
// 'llm_temperature' → '0.1'
// 'llm_timeout_ms'  → '15000'

// Adapter-Implementierungen:
class AzureOpenAIAdapter  implements LLMAdapter { ... }  // Pfad A
class AnthropicAdapter    implements LLMAdapter { ... }  // Pfad B
class MockLLMAdapter      implements LLMAdapter { ... }  // Tests
```

| | Azure GPT-4o-mini | Claude 3.5 Haiku |
|---|---|---|
| Kosten / 1 000 Anfragen (~3 000 + 500 Token) | ~$0.75 | ~$4.40 |

### Konsequenzen

**Positiv:** LLMAdapter-Interface hält Provider aus Business-Logik heraus. Modellwechsel ohne Deployment möglich.

**Risiken:** Quota-Risiko blockiert Sprint-1-Start. Rate-Limit trifft alle 20 User gleichzeitig. Modell-Deprecation erfordert Prompt-Re-Evaluierung. Prompt-Engineering unspezifiziert (kritisch für Qualität).

### Offene Punkte

- [ ] **Ende Sprint 0:** Legal/IT bestätigt Datenresidenz-Anforderung → Pfad A oder B
- [ ] **Sofort nach Entscheid:** Quota-Anfrage stellen
- [ ] Prompt-Template für RAG mit Quellenangabe ausarbeiten und im Spike testen
- [ ] Rate-Limit-Werte dokumentieren → Circuit-Breaker-Konfiguration ableiten
- [ ] API-Key-Rotation-Prozess definieren

---

## ADR-005 · RAG-Stack: pgvector + Multilinguales Embedding-Modell

| | |
|---|---|
| **Status** | Proposed — **BLOCKIEREND** |
| **Datum** | 2026-05-27 |
| **Autor** | Christoph A. Amstutz, MD-PhD |
| **Bezug** | US-01, US-04, QA-06 (Testability), Risiko 1 |
| **Abhängigkeit** | ADR-001 (ConfidenceScorer), ADR-002 (RAG-Pipeline), ADR-004 (LLM-Provider) |

### Kontext

Drei gekoppelte Entscheidungen: Vektor-DB, Embedding-Modell, Chunking-Strategie. Risiko 1 stuft RAG-Qualität als existenzielles Go/No-Go ein.

### Entscheidung

**Komponente 1 · Vektor-DB: pgvector** (PostgreSQL-Extension, keine neue Infrastruktur)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
  id          BIGSERIAL    PRIMARY KEY,
  document_id UUID         NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INTEGER      NOT NULL,
  content     TEXT         NOT NULL,
  embedding   vector(1024) NOT NULL,
  page_number INTEGER,
  char_offset INTEGER,
  token_count INTEGER      NOT NULL,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX ON document_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Ähnlichkeitssuche mit Bereichsisolation:
SELECT dc.content, dc.page_number, dc.char_offset,
       d.title AS document_title, d.uploaded_at,
       1 - (dc.embedding <=> $1::vector) AS cosine_similarity
FROM document_chunks dc
JOIN documents d ON d.id = dc.document_id
WHERE d.area_id = $2
ORDER BY dc.embedding <=> $1::vector
LIMIT $3;
```

**Komponente 2 · Embedding: multilingual-e5-large-instruct** (lokal, MIT-Lizenz)

| Eigenschaft | Wert |
|---|---|
| Modell | `intfloat/multilingual-e5-large-instruct` |
| Dimension | 1 024 |
| Max. Input-Token | 512 |
| Sprachen | 100+, inkl. Deutsch |
| Grösse | ~560 MB |
| CPU-Inferenz | ~150–300 ms |

```python
class EmbeddingAdapter:
    def embed_document(self, text: str) -> list[float]: ...  # prefix: "passage: {text}"
    def embed_query(self, query: str) -> list[float]: ...    # prefix: "query: {text}"
```

**Komponente 3 · Chunking: Rekursiver Text-Splitter**

```
Chunk-Grösse: 400 Token  |  Overlap: 50 Token  |  Mindestgrösse: 50 Token
Trennzeichen-Hierarchie: \n\n → \n → Satz → Wort
```

**Retriever-Interface:**

```typescript
interface Retriever {
  search(query: string, areaId: string, topK?: number): Promise<RetrievedChunk[]>
}
type RetrievedChunk = {
  content: string; similarity: number; documentTitle: string;
  uploadedAt: Date; pageNumber: number | null; charOffset: number; documentId: string
}
class PgVectorRetriever  implements Retriever { ... }  // Produktion
class InMemoryRetriever  implements Retriever { constructor(private fixtures: RetrievedChunk[]) {} }  // Tests
```

**Upgrade-Pfad:** pgvector → Qdrant via Retriever-Interface-Swap (transparent für Pipeline).

### Konsequenzen

**Positiv:** Keine neue Infrastruktur. Bereichsisolation nativ in SQL. Kein Embedding-API-Kostenrisiko. `InMemoryRetriever` ermöglicht Tests ohne DB und Modell.

**Risiken:** Tabellen in PDFs schlecht chunked (häufig in Onboarding-Dokumenten!). Re-Indexierung hat Availability-Lücke (delete → embed → insert: gap). Chunk-Overlap erzeugt Duplikate im LLM-Kontext. 560 MB Cold-Start unspezifiziert. Keine Hybrid Search (BM25 + Vektor) — exakte Begriffe/Zahlen werden systematisch schlechter gefunden.

### Offene Punkte

- [ ] **Sprint 0 Spike:** multilingual-e5-large mit echten Pilotdokumenten testen (Go/No-Go Risiko 1)
- [ ] Versioniertes Re-Indexing spezifizieren (neue Chunks mit version N+1, atomischer Switch)
- [ ] PDF-Tabellenextraktion: pdfplumber `extract_tables()` als Fallback evaluieren
- [ ] Hybrid Search (BM25 + pgvector) als Alternative für exakte Begriffe evaluieren
- [ ] Embedding-Modell Warmup beim Server-Start spezifizieren

---

## ADR-006 · Authentifizierungs-Strategie: JWT mit HTTP-only Cookie und SSO-Ready-Middleware

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | Christoph A. Amstutz, MD-PhD |
| **Bezug** | US-05, QA-03 (Security), QA-05 (Maintainability) |
| **Abhängigkeit** | ADR-007 (Frontend-Framework) |

### Kontext

US-05: Username/Passwort (lokal), Post-MVP SSO via Azure AD / SAML 2.0. Die SSO-Anforderung ist Architektur-Treiber: Wechsel zu SSO darf kein Refactoring der Business-Logik erfordern.

### Entscheidung

JWT-basierte Auth mit kurzlebigem Access-Token (15 min) und langlebigem Refresh-Token (7 Tage), beide als HTTP-only Cookies.

| Token | Typ | Lebensdauer | Inhalt |
|---|---|---|---|
| Access-Token | JWT (HS256) | 15 min | `userId`, `role`, `areaId`, `exp` |
| Refresh-Token | Opaque (UUID) | 7 Tage | in DB gespeichert (SHA-256-Hash) |

```typescript
type AccessTokenPayload = { sub: string; role: Role; areaId: string; exp: number }
type Role = 'learner' | 'area_manager' | 'admin'

interface AuthMiddleware {
  authenticate(req: Request, res: Response, next: NextFunction): Promise<void>
}
class LocalJWTAuthMiddleware implements AuthMiddleware { ... }  // MVP
class OIDCAuthMiddleware       implements AuthMiddleware { ... }  // Post-MVP SSO
class MockAuthMiddleware       implements AuthMiddleware {        // Tests
  constructor(private user: AuthUser) {}
  async authenticate(req, res, next) { (req as any).user = this.user; next() }
}

// RBAC-Deklaration pro Route:
router.post('/api/documents/upload', rbac(['area_manager', 'admin']), uploadHandler)
router.get('/api/admin/config',      rbac(['admin']),                 configHandler)

function rbac(allowedRoles: Role[]): RequestHandler {
  return (req, res, next) => {
    if (!allowedRoles.includes((req as any).user?.role)) return res.status(403).json({ error: 'Forbidden' })
    next()
  }
}
```

**Passwort-Hashing:** Argon2id (`memoryCost: 65536, timeCost: 3, parallelism: 4`)

```sql
CREATE TABLE users (
  id            UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  username      TEXT    NOT NULL UNIQUE,
  password_hash TEXT    NOT NULL,
  role          TEXT    NOT NULL CHECK (role IN ('learner','area_manager','admin')),
  area_id       TEXT    NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_active     BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE refresh_tokens (
  id         UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT    NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ           -- NULL = aktiv
);
```

**Login-Flow:** POST `/api/auth/login` → Argon2id-Verifikation → Access-Token + Refresh-Token als HTTP-only Cookies → 200 `{ role, areaId }` (kein Token im Body)

**Token-Refresh:** Refresh-Token prüfen → neues Access-Token → altes Refresh-Token revoken (Rotation)

**Auth.js (Alternative 1):** Wenn ADR-007 Next.js wählt, Auth.js als bevorzugte Auth-Integration (Post-MVP SSO ohne eigenes Interface-Design).

### Konsequenzen

**Positiv:** SSO-Wechsel: nur neue `AuthMiddleware`-Implementierung nötig. `MockAuthMiddleware` macht alle Endpunkte ohne Login testbar. HTTP-only Cookie verhindert XSS-Token-Diebstahl. Refresh-Token-Rotation erkennt gestohlene Tokens.

**Risiken:** `argon2`-Library (nativer Addon) nicht kompatibel mit Next.js Edge Middleware — Login-Endpoint muss in normaler API-Route implementiert werden (nicht in Middleware). Kein Brute-Force-Schutz auf Login-Endpoint (Rate Limiting fehlt). JWT-Secret-Rotation invalidiert alle aktiven Sessions. Keine Logout-all-Devices-Funktion.

### Offene Punkte

- [ ] ADR-007 abschliessen → Auth.js-Alternative evaluieren
- [ ] Rate Limiting auf `/api/auth/login` (max. 5 Versuche / 15 min / Username+IP)
- [ ] JWT-Secret-Management: Umgebungsvariable, Vault oder Docker Secret?
- [ ] Cookie-Konfiguration Entwicklungsumgebung: `Secure`-Flag nur Produktion, `SameSite=Lax` lokal

---

## ADR-007 · Frontend-Framework: Next.js mit TypeScript und App Router

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | Christoph A. Amstutz, MD-PhD |
| **Bezug** | US-01, US-03, US-07, US-08, US-09, US-11, QA-05 (Maintainability) |
| **Abhängigkeit** | ADR-002 (Discriminated Union / TypeScript), ADR-006 (Auth-Strategie) |

### Kontext

Vier UI-Bereiche: Chat-Interface (Lara), Quiz (Lara), Bereichsverantwortlicher-Dashboard (Stefan), Admin-Seite. TypeScript obligatorisch aus ADR-002 (Exhaustiveness-Check für Discriminated Unions). Post-MVP SSO-Anforderung erfordert Auth-Integration.

### Entscheidung

**Next.js 15 (App Router) + TypeScript.** Next.js übernimmt Frontend (React-Komponenten) und BFF (API-Routes) — kein separater API-Server für MVP. Python-Backend als einzige Service-Grenze für ML/Embedding.

```
app/
  (auth)/login/           → Login (public)
  (learner)/chat/         → Chat-Interface (Lara)
  (learner)/quiz/         → Quiz (Lara)
  (manager)/documents/    → Dokument-Verwaltung (Stefan)
  (manager)/quiz-review/  → Quiz-Freigabe (Stefan)
  (manager)/gaps/         → Wissenslücken (Stefan)
  (admin)/config/         → Admin-Konfiguration
  api/
    auth/login|refresh|logout
    questions/            → POST: RAG-Pipeline aufrufen
    documents/            → GET/POST/DELETE
    quiz/                 → GET/POST
    admin/config/         → GET/POST
```

**Exhaustiveness-Check** (TypeScript erzwingt vollständige Behandlung aller RAGResult-Varianten):

```typescript
function renderResult(result: RAGResult): React.ReactNode {
  switch (result.kind) {
    case 'answer':      return <AnswerCard ... />
    case 'dont_know':   return <DontKnowCard hint={result.hint} />
    case 'no_source':   return <NoSourceCard />
    case 'suppressed':  return <NoSourceCard />
    case 'unavailable': return <ErrorCard message={result.message} />
    case 'timeout':     return <ErrorCard message="Zeitüberschreitung." />
  }
}
```

**LLM-Streaming** (App Router + React 18 ReadableStream):

```typescript
// app/api/questions/route.ts
export async function POST(req: Request) {
  const { question, history } = await req.json()
  const stream = new ReadableStream({
    async start(controller) {
      const ragResult = await runRAGPipeline(question, history)
      if (ragResult.kind !== 'answer') {
        controller.enqueue(JSON.stringify(ragResult)); controller.close(); return
      }
      for await (const chunk of llmAdapter.stream(ragResult.prompt))
        controller.enqueue(chunk)
      controller.close()
    }
  })
  return new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } })
}
```

**Auth.js Integration** (wenn ADR-006 Next.js-Pfad):

```typescript
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Credentials({ async authorize({ username, password }) {
    const user = await verifyUser(username as string, password as string)
    return user ?? null
  }})],
  callbacks: {
    jwt({ token, user }) { if (user) { token.role = user.role; token.areaId = user.areaId } return token },
    session({ session, token }) { session.user.role = token.role as Role; return session }
  }
})
// middleware.ts
export { auth as middleware } from './auth'
export const config = { matcher: ['/((?!login|_next|api/auth).*)'] }
```

**Verzeichnisstruktur:**

```
learnflow/
├── app/            (Route Groups + API-Routes)
├── components/
│   ├── chat/       (AnswerCard, LimitedAnswerCard, DontKnowCard, NoSourceCard, ErrorCard)
│   └── shared/
├── lib/
│   ├── rag/        (RAGResult-Typen, Pipeline-Client)
│   ├── auth/       (AuthMiddleware-Interface + Implementierung)
│   └── config/     (ConfigService-Client)
├── types/
│   └── rag.ts      (RAGResult Discriminated Union)
└── middleware.ts   (Auth-Schutz aller Routen)
```

### Konsequenzen

**Positiv:** Ein Deployment für Frontend und BFF. TypeScript end-to-end. Natives Streaming. Auth.js bietet direkte SSO-Erweiterung. Route-Groups isolieren RBAC.

**Risiken:** HTTP-Contract Next.js ↔ Python ist die kritischste ungelöste Systemgrenze (kein Protokoll definiert). App-Router-API-Instabilität (caching, Server/Client-Component-Boundary). Argon2id inkompatibel mit Edge Middleware → Login in API-Route, nicht Middleware. Konversationshistorie bei Page-Refresh verloren (nur `sessionStorage` als Mitigation). Deployment-Target unspezifiziert.

### Offene Punkte

- [ ] HTTP-Contract Next.js ↔ Python definieren (OpenAPI-Spec oder TypeScript-Types)
- [ ] Docker-Compose: Next.js + Python-Backend + PostgreSQL (pgvector)
- [ ] Styling-Strategie: shadcn/ui oder Tailwind CSS direkt
- [ ] Server-Component / Client-Component-Grenze für Chat-Interface explizit planen
- [ ] Deployment-Target spezifizieren (Docker on-premise vs. Vercel)
- [ ] Streaming p95-Test mit Mock-LLM und realem Netzwerk

---

*Anforderungsstand: v1 — 2026-05-20 | ADRs: 2026-05-27 | Autor: Christoph A. Amstutz, MD-PhD*
