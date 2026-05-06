# LearnFlow — Requirements-Dokument

| Feld | Inhalt |
|---|---|
| Projekt | LearnFlow — KI-gestützte Lernplattform für die fachliche Einarbeitung |
| Kontext | CAS Application Development with AI 2026 · BFH Biel |
| Auftraggeber / PO | Frank Moritz |
| Verfasser | Frank Moritz mit Claude (BA/RE-Sparring) |
| Status | **Draft v1.0** — Konsolidierung der Kickoff-Artefakte |
| Stand | 2026-05-06 |
| Quellen | `LearnFlow_Kickoff_Doku.docx`, `LearnFlow_Chatverlauf.md`, `LearnFlow_Plan_15Wochen.md`, `LearnFlow_Pitch.pptx` (alle in `Artefakten/Modul1Tag2/`) |
| Zweck | Verbindliche Grundlage für Sprint-0-Entscheidungen, Backlog-Pflege und MVP-Abnahme |

---

## Inhaltsverzeichnis

1. [Vision und Projektidee](#1-vision-und-projektidee)
2. [Systemkontext und Scope](#2-systemkontext-und-scope)
3. [Stakeholder und Personas](#3-stakeholder-und-personas)
4. [Funktionale Anforderungen (User Stories)](#4-funktionale-anforderungen-user-stories)
5. [Nicht-funktionale Anforderungen](#5-nicht-funktionale-anforderungen)
6. [Constraints](#6-constraints)
7. [Risiken und Mitigationen](#7-risiken-und-mitigationen)
8. [Annahmen und Abhängigkeiten](#8-annahmen-und-abhängigkeiten)
9. [Offene Punkte](#9-offene-punkte)
10. [Glossar](#10-glossar)
11. [Anhang A — Entscheidungs-Log](#anhang-a--entscheidungs-log)
12. [Anhang B — Versionierung](#anhang-b--versionierung)

---

## 1. Vision und Projektidee

### 1.1 Vision (3-Satz-Form)

1. Wir bauen eine interne, im Firmennetz betriebene Lernplattform für neue Entwickler:innen, Requirements-Engineers und Tester:innen, die ihnen das fachliche Domänen- und Systemwissen unserer historisch gewachsenen Fachanwendungen (z.B. Sozialdienste) zugänglich macht.
2. Sie stellen Fragen in natürlicher Sprache und erhalten quellenbelegte KI-Antworten aus einem pro Fachbereich kuratierten Lern-Korpus (Auszüge aus Confluence, Jira, Workshop-Protokollen, Code) — und können ihr Verständnis mit adaptiven Quizfragen prüfen.
3. Statt Wissen mühsam aus verstreuten Quellen zusammenzusuchen oder erfahrene Kolleg:innen ständig zu unterbrechen, bekommen Neue einen zentralen, immer verfügbaren Lernzugang — und die erfahrenen Kolleg:innen Zeit für die wirklich anspruchsvollen Fragen.

### 1.2 Geschäftliches Problem

Wissen über die Fachdomäne (z.B. Sozialdienste-Recht, Prozesslogik) und über die historisch gewachsene Fachanwendung ist über mehrere Systeme verteilt (Confluence, Jira, Code, Workshop-Protokolle). Inhalte sind oft veraltet oder schwer auffindbar. Folge: Neue Mitarbeiter:innen verlieren Wochen mit Suchen oder Nachfragen; erfahrene Kolleg:innen werden 5–8× täglich zu denselben Themen unterbrochen.

### 1.3 Erfolgsmessung

| Kennzahl | Quelle | Zielsetzung |
|---|---|---|
| Anfragen pro aktive:r Nutzer:in / Woche | Anwendungs-Telemetrie | aussagekräftiger Wert ab W12 messbar |
| Anteil positiver Feedbacks (Story 3) | Feedback-Mechanik | Trend > 60 % nach 4 Wochen Echtbetrieb |
| Self-Reported Zeitersparnis | Mitarbeiter-Umfrage in W12 | qualitative Validierung |
| Goldfragen-Pass-Rate | Eval-Suite (siehe NFR-QUA-1) | ≥ 80 % korrekt + korrekt-unsicher |

> **Hinweis:** Eine harte Vorher/Nachher-Baseline für Einarbeitungs-Zeit ist nicht erhebbar. Ersatz: die obigen quantitativen Signale plus Umfrage.

---

## 2. Systemkontext und Scope

### 2.1 Anwendungsfall (Fokus)

**Variante 1 — Entwickler:innen lernen Fachdomäne.** Andere denkbare Varianten (Sachbearbeiter-Schulung, generischer Lernkurs) sind explizit *nicht* Gegenstand dieses Projekts.

### 2.2 In-Scope (MVP, 8 Slots)

| Slot | Story-ID | Kurzbeschreibung | MoSCoW |
|---:|---|---|---|
| 1 | FR-1 | Q&A mit Quellen | MUST |
| 2 | FR-2 | Korpus aufnehmen (CLI/Skript-Variante) | MUST |
| 3 | FR-3 | Feedback (👍/👎 + Kategorie) | MUST |
| 4 | FR-4 | Unsichere Antworten markieren | MUST |
| 5 | FR-8 | Authentifizierung (im Pilot: Mock-User) | MUST |
| 6 | FR-9 | Bereichsverwaltung (im Pilot: ein hartcodierter Bereich) | MUST |
| 7 | FR-5 | Veraltete Inhalte erkennen | SHOULD |
| 8 | FR-6a | Quiz absolvieren | SHOULD |

> **Zusätzlich (Prozess, ausserhalb der 8 Feature-Slots):** **FR-12** — Goldfragen-Suite und reproduzierbarer Eval-Lauf [MUST]. ~25–30 h, finanziert aus dem Tech-Spike-Block (W1–W2) und während W7–W12 gepflegt. Voraussetzung für die formelle Abnahme von FR-1 und FR-4.

### 2.3 Out-of-Scope (nur konzeptionell dokumentiert)

- FR-6b — Quiz-Freigabe-Workflow
- FR-7 — Wissens-Lücken-Dashboard
- FR-10 — Folgefragen mit Konversationskontext
- FR-11 — Kaputte Quellen erkennen
- Multi-Tenant, horizontale Skalierung, Performance-Tuning
- Echte SSO-Integration (Story 8 nur als Mock im Pilot)
- Echte Admin-UI für Bereichsverwaltung (Story 9 nur hartcodiert im Pilot)
- Stale-Content-Detection als implementiertes Feature (FR-5 ist SHOULD; bei Zeitknappheit fällt es zuerst)

### 2.4 Systemkontext (textuell)

```
            ┌─────────────────────┐
            │ Bereichsverantw.    │
  Korpus →  │ (Stefan)            │ ← Feedback-Liste
            └─────────┬───────────┘
                      │  CLI/Skript-Upload (Story 2)
                      ▼
   ┌──────────────────────────────────┐
   │          LearnFlow               │
   │  ┌───────────────────────────┐   │
   │  │  Frontend (Angular/TS)    │   │
   │  └────────────┬──────────────┘   │
   │               ▼                  │
   │  ┌───────────────────────────┐   │
   │  │  Backend (RAG-Pipeline)   │   │
   │  └────────────┬──────────────┘   │
   │               ▼                  │
   │  ┌───────────┐  ┌────────────┐   │
   │  │ Vector DB │  │ Telemetry  │   │
   │  └─────┬─────┘  └─────┬──────┘   │
   └────────┼──────────────┼──────────┘
            │              │
            ▼              ▼
   Azure OpenAI EU    Feedback-DB
   (Embeddings,
    Completion,
    Self-Check)
                      ▲
                      │ Frage / Antwort / Feedback
              ┌───────┴──────┐
              │ Lerner:in    │
              │ (Lara)       │
              └──────────────┘
```

Externe Abhängigkeiten:
- **Azure OpenAI EU** (LLM-Provider, Embeddings + Completion + Self-Check; in W1 zu bestätigen)
- **AD / Entra ID** (für SSO; im MVP nur als Mock berücksichtigt)
- **Quellsysteme** (Confluence, Jira, Repo) — *nicht* direkt angebunden; Inhalte werden in den Korpus kopiert

---

## 3. Stakeholder und Personas

### 3.1 Stakeholder-Übersicht

| Stakeholder | Rolle im Projekt | Haltung |
|---|---|---|
| Lerner:innen (neue Devs/REs/Tester:innen) | Primärnutzer | Profitieren direkt |
| Bereichsverantwortliche | Korpus-Pflege, Quiz-Freigabe | Mehraufwand kurzfristig — kritischer Stakeholder |
| Geschäftsleitung | Sponsor | Profitieren (kürzere Time-to-Productivity) |
| HR / Personalentwicklung | Onboarding-Owner | Stakeholder, nicht im Projekt |
| Datenschutzbeauftragte:r | Türsteher Korpus-Inhalte | Bremser, nicht Gegner |
| IT-Security | Türsteher Cloud-Verarbeitung | Bremser, nicht Gegner |
| Betriebsrat | Wachsamkeit bei Nutzungsdaten/Quiz-Scores | Berechtigte Kontrolle |
| Schulungsabteilung | Indirekt betroffen | Potenziell Gegner (Geschäftsmodell) |
| Wissens-Gatekeeper | Senior:innen, die Wissen als Macht sehen | Potenziell Gegner |

### 3.2 Persona 1 — Lara Fischer

- **Profil:** 26, Junior Software Engineer, FH-Abschluss Informatik, 6 Wochen im Unternehmen, eingeteilt im Sozialdienste-Modul.
- **Hauptproblem:** Muss Code zu Fachprozessen schreiben, die sie nicht versteht (Grundbedarf, KV-Berechnung, Wohnkosten); findet das nötige Wissen nicht selbst zusammen.
- **Frustration heute:** Confluence-Friedhof. Jira erklärt nur das *Was*, nicht das *Warum*. Traut sich nicht, dieselbe Frage zum dritten Mal zu stellen. Senior-Erklärungen sind 20 min lang, sie versteht 5 davon und fragt nicht nach.
- **Ziel:** In drei Monaten eigene Stories ohne ständige Rückfrage abschliessen.
- **Was sie abhält:** offensichtlich falsche Antworten; Tool langsamer als ein Slack-Ping; Privacy-Sorge (wer liest mit, welche dummen Fragen ich stelle); Antworten ohne Quelle.

### 3.3 Persona 2 — Stefan Brunner

- **Profil:** 51, Senior BA & Bereichsverantwortlicher Sozialdienste, 18 Jahre im Unternehmen, davon 12 in der Domäne. Wandelndes Lexikon.
- **Hauptproblem:** 5–8× täglich von Junior:innen unterbrochen, Wissen bleibt in seinem Kopf.
- **Frustration heute:** Dieselben Fragen immer wieder. Doku schreiben kostet Stunden, niemand liest sie. Pflege steht in keiner Stellenbeschreibung.
- **Ziel:** Wissen so konservieren, dass er weniger unterbrochen wird und vor der Pensionierung sein Wissen extern verfügbar gemacht hat.
- **Was ihn abhält:** Pflegeaufwand höher als versprochen; Tool gibt unter seinem Bereichsnamen falsche Antworten; auto-generierte Quizfragen fachlich Quatsch; Sorge sich wegzurationalisieren.

---

## 4. Funktionale Anforderungen (User Stories)

> Format: jede Story trägt eine ID `FR-n`, eine Story im Format „Als ... möchte ich ... damit ..." und Acceptance Criteria im **Given/When/Then**-Format. MoSCoW gemäss Kickoff-Entscheidung.

### FR-1 — Frage stellen und quellenbelegte Antwort bekommen [MUST]

**Als** Lara **möchte ich** eine Frage in natürlicher Sprache stellen und eine quellenbelegte Antwort bekommen, **damit** ich Fachprozesse verstehen kann, ohne erfahrene Kolleg:innen zu unterbrechen.

- **AC1:** *Given* ich habe eine Frage zu meinem Bereich · *When* ich sie im Eingabefeld absende · *Then* erhalte ich innerhalb von 10 Sekunden eine Antwort mit mindestens einer Quellenangabe (Dokumenttitel + Verweis).
- **AC2:** *Given* die Antwort verweist auf eine Quelle · *When* ich auf die Quellenangabe klicke · *Then* öffnet sich die Originalquelle und der belegende Abschnitt ist visuell hervorgehoben (Highlight + automatisches Scrollen).
- **AC3:** *Given* der LLM- oder Retrieval-Service ist nicht erreichbar · *When* ich eine Frage absende · *Then* erhalte ich eine klare Fehlermeldung „Service vorübergehend nicht verfügbar" — keine erfundene Antwort. Eine Fehlermeldung trägt mindestens die Felder `code`, `klasse` (z.B. `service_unavailable`, `validation`, `internal`), `nutzertext` und eine `correlation_id`.
- **AC4 (Eingabe-Validierung):** *Given* meine Frage ist leer, nur Whitespace oder kürzer als 3 Zeichen · *When* ich sie absende · *Then* wird sie clientseitig abgewiesen mit Hinweis „Bitte formuliere eine Frage". Bei einer Frage länger als 1.000 Zeichen / 500 Token wird sie ebenfalls abgewiesen mit Hinweis auf das Limit. In diesen Fällen wird kein LLM-Call ausgelöst (Schutz gegen unnötige Cloud-Kosten und Prompt-Injection-Vektoren).
- **AC5 (Telemetrie):** *Given* eine Frage wird beantwortet (egal ob inhaltlich oder als „Weiss ich nicht") · *Then* wird in der Telemetrie pseudonymisiert protokolliert: Zeitpunkt, Bereich, Latenz in ms, Konfidenz-Klasse (`belegt` / `eingeschränkt belegt` / `unsicher`), Token-Verbrauch (Embedding + Completion), Feedback-Status (`leer` / `up` / `down`).

### FR-2 — Inhalte in den Lern-Korpus aufnehmen [MUST]

**Als** Stefan **möchte ich** Dokumente und Texte in den Lern-Korpus meines Bereichs aufnehmen, **damit** das System auf aktuelle, von mir freigegebene Inhalte zugreifen kann.

- **AC1:** *Given* ich lade ein Dokument bis 50 Seiten / 10 MB in einem unterstützten Format hoch (PDF, Markdown, DOCX, Confluence-Export) · *When* die Verarbeitung startet · *Then* ist es nach maximal 5 Minuten als Quelle verfügbar; bei grösseren Dokumenten zeigt das System eine Fortschrittsanzeige und bestätigt spätestens nach 30 Minuten.
- **AC2:** *Given* der Verarbeitungsprozess endet · *When* ich das Dashboard öffne · *Then* sehe ich Status (erfolgreich / Fehler), Anzahl extrahierter Abschnitte und das Aufnahmedatum.
- **AC3:** *Given* das Format wird nicht unterstützt oder das Dokument ist beschädigt · *When* ich es hochlade · *Then* sehe ich sofort eine spezifische Fehlermeldung mit Hinweis auf akzeptierte Formate.
- **AC4 (Klassifikations-Gate):** *Given* das Dokument trägt keine dokumentierte Datenklassifikation oder ist als „nicht für Cloud" markiert · *When* die Ingestion startet · *Then* bricht das System mit Fehlercode ab, der Vector-Store wird nicht verändert, und ein Eintrag im Audit-Log erfasst Zeitpunkt, Dokumentname, Grund und auslösende Person.

> **MVP-Abgrenzung:** Story 2 wird im MVP als **CLI/Skript-Variante** umgesetzt, nicht als vollwertige Pflege-UI. Die obigen ACs gelten für die Skript-Variante mit minimaler Status-Seite.

### FR-3 — Feedback zu Antworten geben [MUST]

**Als** Lara **möchte ich** jede Antwort als hilfreich oder nicht hilfreich markieren und einen Grund angeben, **damit** unklare oder falsche Antworten korrigiert werden können.

- **AC1:** *Given* mir wurde eine Antwort angezeigt · *When* ich auf 👎 klicke · *Then* werde ich nach einer strukturierten Kategorie gefragt (faktisch falsch / unvollständig / veraltet / unverständlich / Quelle stimmt nicht) und kann optional Freitext ergänzen.
- **AC2:** *Given* ich habe Feedback gegeben · *When* es gespeichert wurde · *Then* erhalte ich eine Bestätigung „Danke, dein Feedback wurde an die Bereichsverantwortliche:n weitergeleitet" und es erscheint im Bereichs-Dashboard.

### FR-4 — Unsichere Antworten klar erkennen [MUST]

**Als** Lara **möchte ich** klar erkennen, wenn das System sich seiner Antwort nicht sicher ist, **damit** ich keinen halluzinierten Inhalten vertraue.

- **AC1:** *Given* die maximale Retrieval-Similarity der gefundenen Chunks liegt unter dem konfigurierten Schwellwert (zu Projektbeginn empirisch zu kalibrieren) · *When* das System antworten würde · *Then* antwortet es nicht inhaltlich, sondern mit „Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden" und schlägt eine Bereichsverantwortliche:n vor.
- **AC2:** *Given* das Modell führt nach der Generierung einen Self-Check-Pass durch, der jede Antwort-Aussage einzeln gegen die gelieferten Quellen prüft und je Aussage ein Urteil `belegt` / `nicht belegt` zurückgibt · *When* der Anteil belegter Aussagen unter 80 % liegt · *Then* wird die Antwort sichtbar als „Eingeschränkt belegt" markiert (Farbe + Icon + Hinweistext) und Aussagen mit Urteil `nicht belegt` werden im Antworttext visuell abgegrenzt (z.B. graue Schrift + Tooltip „nicht aus Quellen belegt"). Liegt der Anteil unter 50 %, wird die Antwort wie bei AC1 unterdrückt und durch „Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden" ersetzt.
- **AC3:** *Given* eine vordefinierte Liste von Out-of-Corpus-Testfragen existiert · *When* diese gestellt werden · *Then* gibt das System in mindestens 90 % der Fälle ein „Weiss ich nicht" zurück.

### FR-5 — Veraltete Inhalte erkennen und re-validieren [SHOULD]

**Als** Stefan **möchte ich** eine Übersicht über veraltete oder lange nicht validierte Inhalte sehen und sie aktiv prüfen können, **damit** der Korpus aktuell bleibt.

- **AC1:** *Given* ich öffne das Bereichs-Dashboard · *When* in meinem Bereich Dokumente älter als 6 Monate ohne erneute Validierung existieren · *Then* werden sie mir in einer sortierten Liste mit Alter und letztem Validierungsdatum angezeigt.
- **AC2:** *Given* ich öffne einen Eintrag aus der Stale-Liste · *When* ich auf „Validieren" klicke · *Then* werde ich gefragt, ob der Inhalt geprüft und weiterhin aktuell ist (Ja / Nein, ersetzt durch ... / Nein, entfernen).
- **AC3:** *Given* in meinem Bereich werden Inhalte stale · *When* die monatliche Stichtag-Prüfung läuft · *Then* erhalte ich eine zusammenfassende Benachrichtigung per E-Mail oder interner Inbox.

### FR-6a — Wissen mit Quiz überprüfen [SHOULD]

**Als** Lara **möchte ich** zu einem Bereich ein kurzes Quiz absolvieren, **damit** ich überprüfen kann, ob ich das Gelesene wirklich verstanden habe.

- **AC1:** *Given* ich wähle einen Bereich · *When* ich auf „Quiz starten" klicke · *Then* bekomme ich 5 Multiple-Choice-Fragen aus dem Pool freigegebener Quizfragen — jede mit hinterlegter Quelle für die korrekte Antwort.
- **AC2:** *Given* ich habe alle Fragen beantwortet · *When* ich das Quiz abschliesse · *Then* sehe ich pro Frage richtig/falsch, die korrekte Antwort mit Erklärung und einen direkten Link zur belegenden Quelle.

### FR-6b — Auto-generierte Quizfragen reviewen und freigeben [SHOULD] *(out of MVP)*

**Als** Stefan **möchte ich** auto-generierte Quizfragen vor der Veröffentlichung reviewen und freigeben können, **damit** keine fachlich falschen Fragen unter meinem Bereichsnamen verbreitet werden.

- **AC1:** *Given* das System hat aus Korpus-Inhalten neue Quizfragen generiert · *When* ich meine Review-Inbox öffne · *Then* sehe ich jede Frage mit Antwortoptionen, markierter korrekter Antwort und der Quellen-Passage, aus der sie generiert wurde.
- **AC2:** *Given* ich prüfe eine Frage · *When* ich auf „Freigeben / Bearbeiten / Verwerfen" klicke · *Then* wird die Aktion gespeichert und nur freigegebene Fragen erscheinen im Quiz für Lerner:innen.

### FR-7 — Wissens-Lücken pro Bereich erkennen [COULD] *(out of MVP)*

**Als** Stefan **möchte ich** sehen, welche Fragen besonders häufig gestellt werden oder oft negatives Feedback bekommen, **damit** ich gezielt Dokumentation ergänzen oder korrigieren kann.

- **AC1:** *Given* der Beobachtungszeitraum ist 30 Tage und mindestens 50 Fragen wurden gestellt · *When* ich das Dashboard öffne · *Then* sehe ich Top-10 Themen-Cluster (gebildet via Embedding-Ähnlichkeit) mit Häufigkeit und aggregierter Feedback-Quote.
- **AC2:** *Given* ich klicke auf einen Cluster mit hoher Negativ-Quote · *When* sich die Detailansicht öffnet · *Then* sehe ich Beispielfragen sowie die vom System verwendeten Quellen.
- **AC3:** *Given* Cluster werden angezeigt · *When* ein Cluster weniger als 5 Fragen enthält · *Then* wird er nicht angezeigt (Pseudonymitäts-Schutz).

### FR-8 — Authentifizierung und Bereichszuordnung [MUST]

**Als** Lara **möchte ich** mich mit meinen Firmen-Credentials anmelden und automatisch die Bereiche sehen, für die ich freigegeben bin, **damit** ich nur relevante und für mich freigegebene Inhalte zu sehen bekomme.

- **AC1:** *Given* ich öffne die Plattform · *When* ich nicht authentifiziert bin · *Then* werde ich auf den firmeninternen Single-Sign-On weitergeleitet (SSO über Active Directory / Entra ID).
- **AC2:** *Given* ich bin angemeldet · *When* ich die Bereichsauswahl öffne · *Then* sehe ich nur die Bereiche, für die meine Rolle / mein Team in der Bereichszuordnung freigegeben sind.

> **MVP-Abgrenzung — konkrete Mock-Spezifikation:**
> - Beim App-Start ist genau **ein** hartcodierter User aktiv (z.B. `mock-user-lara`, Rolle `Lerner`, Zugriff auf den einzigen Pilot-Bereich).
> - Es gibt **kein** Login-Screen und **keinen** echten SSO-Roundtrip; jede Anfrage wird intern gegen den Mock-User verifiziert.
> - **Kein echtes Logout** und keine Session-Timeouts; die Session lebt so lange wie der Browser-Tab.
> - Die Bereichsauswahl (FR-8 AC2) zeigt im MVP genau einen Eintrag (den Pilot-Bereich) — visuell vorhanden, fachlich trivial.
> - Die obigen produktiven ACs (AC1, AC2) gelten für die spätere Integration ausserhalb des Kursrahmens.

### FR-9 — Bereiche und Verantwortliche verwalten [MUST]

**Als** Admin **möchte ich** Bereiche anlegen, ihnen Verantwortliche zuordnen und Zugriffsregeln definieren, **damit** das System ein sauberes organisatorisches Modell hat.

- **AC1:** *Given* ich bin als Admin angemeldet · *When* ich einen neuen Bereich anlege und Verantwortliche zuordne · *Then* erhalten diese eine Benachrichtigung mit ihren Rechten und Pflichten (inkl. erwartetem Pflegeaufwand).
- **AC2:** *Given* ein Bereich existiert · *When* ich Zugriffsregeln definiere (welche AD-Gruppen / Teams sehen ihn) · *Then* werden diese sofort wirksam.

> **MVP-Abgrenzung:** Im Pilot existiert genau **ein hartcodierter Bereich**. Die obigen ACs sind konzeptionell.

### FR-10 — Folgefragen im Konversationskontext [SHOULD] *(out of MVP)*

**Als** Lara **möchte ich** zu einer erhaltenen Antwort Folgefragen stellen können, **damit** ich Themen iterativ vertiefen kann, ohne den Kontext jedes Mal neu zu erklären.

- **AC1:** *Given* ich habe eine Antwort erhalten · *When* ich eine Folgefrage stelle · *Then* berücksichtigt das System die vorangegangenen 1–3 Frage-Antwort-Paare als Kontext und antwortet konsistent.
- **AC2:** *Given* ich starte eine neue Frage zu einem unverwandten Thema · *When* ich auf „Neues Gespräch" klicke · *Then* wird der Kontext zurückgesetzt.

### FR-11 — Kaputte Quellen erkennen [SHOULD] *(out of MVP)*

**Als** System (im Auftrag der Bereichsverantwortlichen) **möchte ich** erkennen, wenn eine im Korpus referenzierte Originalquelle nicht mehr existiert oder geändert wurde, **damit** Lara keine ins Leere führenden Quellenverweise sieht.

- **AC1:** *Given* eine Quelle im Korpus stammt aus Confluence/SharePoint · *When* die wöchentliche Integritätsprüfung läuft und die Originalquelle nicht mehr erreichbar ist · *Then* wird die Quelle im Korpus als „broken" markiert und nicht mehr für Antworten verwendet.
- **AC2:** *Given* eine Quelle ist als „broken" markiert · *When* Stefan das Dashboard öffnet · *Then* sieht er die Liste betroffener Quellen mit Vorschlag „Re-Upload / Entfernen".

### FR-12 — Goldfragen-Suite und reproduzierbarer Eval-Lauf [MUST — Prozess-Story]

**Als** PO **möchte ich** eine im Repo versionierte Goldfragen-Suite und einen reproduzierbaren Eval-Lauf, **damit** FR-1 und FR-4 objektiv abgenommen und Iterationen messbar verglichen werden können.

- **AC1:** *Given* der Pilot-Bereich existiert · *When* ich die Goldfragen-Suite öffne · *Then* enthält sie ≥ 20 Fragen, davon ≥ 30 % out-of-corpus, je mit Feldern `frage`, `sprache`, `erwartete_eigenschaft` (z.B. „muss Quelle X enthalten" / „muss als unsicher markiert werden") und ist im Repo unter `eval/goldset.yaml` versioniert.
- **AC2:** *Given* die Suite und ein lauffähiges System existieren · *When* ich `npm run eval` (oder gleichwertiges Kommando) ausführe · *Then* erzeugt der Lauf einen Report mit Pass-Rate für drei Kategorien (*korrekt beantwortet* / *falsch beantwortet* / *korrekt als unsicher markiert*) und einem Diff zum letzten Lauf; der Report wird als Artefakt in den Review-Unterlagen abgelegt.
- **AC3:** *Given* eine MVP-Review steht an (W8, W12) · *When* die Reviewer den Eval-Report öffnen · *Then* ist der Report nicht älter als 24 Stunden und gegen den aktuellen Korpus-Stand gefahren.

> **Aufwand:** ~25–30 h, eingeplant aus dem Tech-Spike-Block (W1–W2) und gepflegt während W7–W12. **Voraussetzung für Abnahme** von FR-1 und FR-4 — operationalisiert NFR-QUA-1.

---

## 5. Nicht-funktionale Anforderungen

### 5.1 Performance

| ID | Anforderung | Quelle / Begründung |
|---|---|---|
| **NFR-PER-1** | Antwortzeit FR-1 ≤ 10 s im 95. Perzentil. | FR-1 AC1 |
| **NFR-PER-2** | Korpus-Verarbeitung ≤ 5 min für Dokumente bis 50 S. / 10 MB; ≤ 30 min für grössere mit Fortschrittsanzeige. | FR-2 AC1 |
| **NFR-PER-3** | Stale-Check FR-5 läuft asynchron (Batch); blockiert keine Live-Anfrage. | abgeleitet aus FR-5 AC3 |

### 5.2 Zuverlässigkeit

| ID | Anforderung | Quelle / Begründung |
|---|---|---|
| **NFR-REL-1** | Bei Ausfall LLM oder Retrieval: graceful Fehlermeldung, keine erfundene Antwort. | FR-1 AC3 |
| **NFR-REL-2** | Korpus-Ingestion ist atomar pro Dokument: bei Fehler keine partiell geladene Quelle. | abgeleitet aus FR-2 |

### 5.3 Sicherheit, Datenschutz, Compliance

| ID | Anforderung | Quelle / Begründung |
|---|---|---|
| **NFR-SEC-1** | LLM- und Embedding-Verarbeitung ausschliesslich in EU-gehosteten Diensten (vorzugsweise Azure OpenAI EU). | Constraint TC-2, Risiko 2 |
| **NFR-SEC-2** | Jeder Korpus-Eintrag trägt eine dokumentierte Datenklassifikation und freigebende Person; ohne Klassifikation keine Aufnahme. | offene Lücke aus Kickoff (Türsteher Datenschutz) |
| **NFR-SEC-3** | Authentifizierung gegen AD/Entra-ID (SSO); im MVP via Mock, in der Zielarchitektur produktiv. | FR-8 |
| **NFR-SEC-4** | Admin-Aktionen (Bereichsanlage, Verantwortlichen-Zuordnung, Korpus-Mutation) sind audit-loggable. | abgeleitet aus FR-9, Compliance |
| **NFR-SEC-5** | Im MVP keine personenbezogenen Auswertungen pro Lerner:in (insb. keine Quiz-Score-Verfolgung); Betriebsrats-Konflikt vermieden. | Stakeholder-Analyse, Entscheidungs-Log |

### 5.4 Bedienbarkeit

| ID | Anforderung | Quelle / Begründung |
|---|---|---|
| **NFR-USA-1** | Quellenangabe inline in Antwort; ein Klick öffnet Originalquelle mit Highlight. | FR-1 AC2 |
| **NFR-USA-2** | Antwortsprache = Sprache der Frage (Pilot: deutsch); keine sprachlichen Sprünge in einer Konversation. | abgeleitet aus Persona Lara |
| **NFR-USA-3** | „Eingeschränkt belegt"-Markierung visuell deutlich (Farbe + Icon + Text), nicht nur subtile Indikation. | FR-4 AC2 |

### 5.5 Wartbarkeit und Erweiterbarkeit

| ID | Anforderung | Quelle / Begründung |
|---|---|---|
| **NFR-MAI-1** | LLM-Anbieter und Vector-DB sind hinter einer Abstraktion austauschbar. | Risiko 3 (Build vs. Buy) |
| **NFR-MAI-2** | Korpus-Befüllung via CLI/Skript scriptbar; Ingestion-Schritt im CI/CD reproduzierbar. | FR-2 (MVP-Variante) |
| **NFR-MAI-3** | Tech-Stack-Wahl (Frontend, Backend, LLM-Provider, Vector-DB) ist bis Ende W1 dokumentiert (siehe `docs/`). | Plan §3 (Bedingung 1) |

### 5.6 Qualität / Evaluierbarkeit

| ID | Anforderung | Quelle / Begründung |
|---|---|---|
| **NFR-QUA-1** | Versionierte Goldfragen-Suite (≥ 20 Fragen pro Bereich, davon ≥ 30 % out-of-corpus, mit erwarteter Eigenschaft); reproduzierbarer Eval-Lauf erzeugt Pass-Rate-Report. **Operationalisiert in FR-12.** | abgeleitet aus FR-1, FR-4; Voraussetzung für MVP-Abnahme |
| **NFR-QUA-2** | Antwort enthält Validierungsdatum / Last-Modified der verwendeten Quellen. | Risiko 1 Plan, Vertrauensmechanik |
| **NFR-QUA-3** | Out-of-Corpus-Pass-Rate ≥ 90 % (FR-4 AC3). | FR-4 AC3 |

### 5.7 Beobachtbarkeit

| ID | Anforderung | Quelle / Begründung |
|---|---|---|
| **NFR-OBS-1** | Pro Anfrage werden anonymisiert geloggt: Zeitpunkt, Bereich, Latenz, Konfidenz-Klasse, Feedback-Status. | Erfolgsmessung (siehe §1.3) |
| **NFR-OBS-2** | Cloud-Token-Verbrauch ist tagesgenau auswertbar; Soft-Cap-Warnung bei 70 %, Hard-Cap-Stop bei 100 % des Monats-Budgets. | offene Lücke (siehe §9 OI-6) |

---

## 6. Constraints

### 6.1 Technische Constraints

| ID | Constraint | Anmerkung |
|---|---|---|
| **TC-1** | Frontend in **Angular + TypeScript**. | Per `.gitignore` festgelegt; in W1 final bestätigen. |
| **TC-2** | LLM-Provider: **Azure OpenAI EU** (Vorzugswahl). | Alternative on-prem im Kursrahmen ausgeschlossen. |
| **TC-3** | Vector-DB: **offen**, in W1 zu fixieren. | Kandidaten z.B. Chroma, Qdrant, pgvector. |
| **TC-4** | Betrieb im internen Firmennetz (für Zielsystem); im Kurs-MVP läuft Demo lokal/cloud. | Architektur muss intra-net-fähig sein, ist aber im Pilot nicht zu beweisen. |
| **TC-5** | Korpus-Sprache im Pilot: **deutsch**. | Mehrsprachigkeit nicht im MVP-Scope. |

### 6.2 Organisatorische Constraints

| ID | Constraint | Anmerkung |
|---|---|---|
| **OC-1** | Budget: **3 Personen × 15 effektive Wochen × 8 h = 360 Personenstunden**. | Plan §„Verfügbares Budget". Kein Spielraum nach oben. |
| **OC-2** | Abgabe / Präsentation: **30. September 2026**. | Feste Deadline. |
| **OC-3** | Genau **ein Pilot-Bereich**, hartcodiert. | Skalierung auf mehrere Bereiche ist Story FR-9 (out of MVP). |
| **OC-4** | Pflege-Verantwortung pro Bereich liegt **organisatorisch ausserhalb** des Projekts. | Mindesterwartung: nominelle:r Verantwortliche:r, ~2 h/Monat Pflege. |

### 6.3 Rechtliche und Compliance-Constraints

| ID | Constraint | Anmerkung |
|---|---|---|
| **LC-1** | DSGVO-konforme LLM-Verarbeitung (EU-Hosting). | NFR-SEC-1. |
| **LC-2** | Datenklassifikation pro Korpus-Inhalt; Datenschutzbeauftragte:r ist Türsteher. | NFR-SEC-2. |
| **LC-3** | Kein Personal-Tracking im MVP; Story 8 als Mock, keine Quiz-Scores pro Person. | Vermeidung Betriebsrats-Konflikt. |

---

## 7. Risiken und Mitigationen

| ID | Risiko | W'keit | Schaden | Mitigation |
|---|---|---|---|---|
| **R1** | **Content Rot:** Korpus veraltet, weil niemand pflegt; Antworten basieren auf veralteten Quellen → Vertrauensverlust. | hoch | Totalverlust | (a) verbindliche Pflege-Vereinbarung pro Bereich vor Aufnahme; (b) automatischer Stale-Content-Report (Story 5, sobald implementiert); (c) Validierungsdatum sichtbar an jeder Antwort (NFR-QUA-2); (d) Pilot bewusst klein. |
| **R2** | **Halluzinationen in der Fachdomäne:** Junior:innen können fachliche Plausibilität nicht prüfen; falsche Implementierungen rutschen durch. | mittel | hoch | (a) Quellenbeleg als harte AC in jeder Antwort (FR-1); (b) „Weiss-ich-nicht"-Pfad mit ≥ 90 % Trefferquote auf Out-of-Corpus (FR-4 AC3); (c) Self-Check (FR-4 AC2); (d) Feedback-Mechanik (FR-3) mit kurzem Reaktionsweg. |
| **R3** | **Build statt Buy:** Atlassian Rovo, Glean, Microsoft Copilot decken RAG-auf-eigene-Daten zunehmend ab. | hoch | verlorene Investition | (a) ehrliche Build-vs-Buy-Kurzanalyse vor Sprint 0; (b) klare Differenzierung definieren (Quiz mit Bereichs-Freigabe); (c) NFR-MAI-1: LLM und Vector-DB tauschbar. |
| **R4** | **Tech-Spike länger als W1:** Stack-Entscheidung verzögert sich, Story 1 nicht in W5 fertig, Domino-Effekt. | mittel | hoch | (a) harter W1-Stichtag im Plan; (b) Mitigation: in W4 entscheiden, ob FR-4 fällt. |
| **R5** | **Kein echter Pilot-Korpus bis W2:** Demo-Dokumente bleiben länger im Einsatz; echter Test rutscht zu spät. | mittel | mittel | (a) PO benennt Pilot-Bereich vor W2 (siehe OI-1); (b) Notfall-Korpus mit öffentlichen SKOS-Dokumenten. |
| **R6** | **Cloud-Kosten unerwartet hoch:** Token-Bill überrascht Team, kein Kostenträger geklärt. | mittel | mittel | (a) Kostenmodell + Soft/Hard-Cap (NFR-OBS-2); (b) Klärung Kostenträger in W1 (OI-6). |
| **R7** | **Datenschutz-Freigabe verzögert:** DSB blockiert Upload realer Inhalte. | mittel | hoch | (a) Klassifikations-Workflow vor Korpus-Aufnahme (NFR-SEC-2); (b) Gespräch DSB in W1. |

---

## 8. Annahmen und Abhängigkeiten

### 8.1 Annahmen

- **A1:** Das Team verfügt zu Sprint-Start über grundlegende RAG-Erfahrung; falls nicht, sind +50–80 h Lernkurve einzuplanen, was im 360 h Budget *nicht* abfangbar ist (Konsequenz: weiteres Story raus).
- **A2:** Azure OpenAI EU ist organisatorisch verfügbar (Subscription, Konto, ggf. Quota).
- **A3:** Es gibt mindestens einen Bereich mit interner Bereitschaft, einen Verantwortlichen zu nominieren und ~30 Dokumente bereitzustellen.
- **A4:** 1–2 echte Junior-Devs stehen für MVP-Reviews W8 und W12 zur Verfügung.

### 8.2 Abhängigkeiten

- **D1:** Datenschutzfreigabe für Cloud-LLM (DSB-Sign-off).
- **D2:** Pilot-Bereichsleiter bestätigt Pflege-Verantwortung schriftlich.
- **D3:** Finale Tech-Stack-Entscheidung W1 (siehe NFR-MAI-3).
- **D4:** Eval-Suite (NFR-QUA-1) muss vor erster MVP-Review (W8) existieren.

---

## 9. Offene Punkte

> Status zum 2026-05-06. Alle offenen Punkte gehören in die Sprint-0-Agenda; jeder Punkt blockt bestimmte Folgearbeiten.

| ID | Offener Punkt | Owner | Blockiert | Soll-Klärung |
|---|---|---|---|---|
| **OI-1** | Konkrete Benennung des Pilot-Bereichs | PO Frank | W2-Korpus-Aufbau | bis Ende W1 |
| **OI-2** | Tech-Stack-Workshop: Termin und Teilnehmer | PO Frank | gesamter Sprint 0 | W1 Tag 1 |
| **OI-3** | Skill-Mapping Person A / B / C (wer Backend/Frontend/Domain) | Team | Wochenplan ab W3 | W1 |
| **OI-4** | Echte Junior-Dev-Probanden für MVP-Reviews W8 / W12 | PO Frank | Nutzwert-Validierung | W6 |
| **OI-5** | DSB-Freigabe für Korpus-Inhalte und Cloud-LLM | PO Frank + DSB | Korpus-Befüllung | W2 |
| **OI-6** | Cloud-Kostenträger und Cap-Strategie (Azure OpenAI Token) | PO Frank | Dev-Phase ab W3 | W1 |
| **OI-7** | Definition des „Quelle"-Granularität-Modells (Dokument / Sektion / Chunk); FR-1-Sprint **darf nicht starten**, bevor entschieden | Tech-Lead | FR-1 AC2, FR-2 Chunking, FR-3 „Quelle stimmt nicht" | **bis W2 — vorgezogen** |
| **OI-8** | Goldfragen-Suite ≥ 20 Fragen vorbereiten | Domain-Lead (Person C) | NFR-QUA-1, MVP-Review | bis W7 |
| **OI-9** | Build-vs-Buy-Kurzanalyse | PO Frank + Tech-Lead | Pitch-Glaubwürdigkeit (Risiko 3) | W2 |

---

## 10. Glossar

| Begriff | Bedeutung |
|---|---|
| **Bereich** | Organisatorische Klammer für einen Lern-Korpus (z.B. „Sozialdienste"). Im Pilot genau einer, hartcodiert. |
| **Korpus / Lern-Korpus** | Gesammelte, vom Bereich freigegebene Inhalte (PDFs, Markdown, DOCX, Code-Auszüge), die das System für Antworten verwendet. |
| **RAG** | Retrieval-Augmented Generation: LLM erzeugt Antworten auf Basis abgerufener Dokument-Chunks statt freier Generierung. |
| **Embedding** | Vektor-Repräsentation eines Text-Chunks für semantische Ähnlichkeitssuche. |
| **Chunk** | Indexierbarer Text-Abschnitt eines Quelldokuments (Granularität projekt-intern zu definieren — siehe OI-7). |
| **Self-Check** | Zweiter LLM-Pass, der prüft, ob die generierte Antwort vollständig aus den gelieferten Quellen belegbar ist. |
| **Konfidenz-Schwellwert** | Empirisch kalibrierter Mindestwert der Retrieval-Similarity, unterhalb dessen das System „weiss ich nicht" antwortet. |
| **Stale Content** | Korpus-Inhalt, der älter als 6 Monate ist und seit dem nicht erneut validiert wurde. |
| **Out-of-Corpus** | Frage, deren Antwort nicht aus dem Korpus ableitbar ist; das System soll sie als unsicher zurückweisen. |
| **Halluzination** | Plausibel klingende, aber inhaltlich falsche LLM-Ausgabe. |
| **Goldfragen-Suite** | Versionierte Sammlung von Test-Fragen mit erwarteter Antwort-Eigenschaft; Grundlage objektiver Qualitätsmessung. |
| **MoSCoW** | Priorisierungsschema MUST / SHOULD / COULD / WON'T. |
| **Walking Skeleton** | Lauffähige End-zu-End-Implementierung mit minimalem Funktionsumfang. |
| **SSO** | Single Sign-On (hier via AD / Entra ID). |
| **SKOS** | Schweizerische Konferenz für Sozialhilfe — fachliche Berechnungs-Grundlage im Sozialdienste-Bereich. |
| **DSB** | Datenschutzbeauftragte:r. |

---

## Anhang A — Entscheidungs-Log

| Thema | Entscheidung | Begründung |
|---|---|---|
| Anwendungsfall | Variante 1 (Entwickler:innen lernen Fachdomäne) | Eigene Dogfood-Möglichkeit, kleinerer Scope, niedrigeres Risiko. |
| Korpus-Strategie | Kuratierter Lern-Korpus parallel zu Quellsystemen | Vermeidet Berechtigungsmodell über vier Quellsysteme; klare Pflegeverantwortung. |
| Pflege-Verantwortung | Organisatorisch ausserhalb des Projekts | Kann nicht im Projekt geklärt werden; Mindesterwartung im Canvas. |
| Quellenbelegung | Pflicht — AC in jeder Q&A-Story | Grösste Vertrauens-Mechanik; nicht verhandelbar. |
| Erfolgsmessung | Nutzungszahlen + Anteil positiver Feedbacks + Mitarbeiter-Umfrage | Quantitative Signale + qualitative Validierung; harte Vorher/Nachher-Baseline nicht erhebbar. |
| Personal-Tracking | Im MVP raus | Datenschutz- und Betriebsrats-Risiko; nach Pilot mit anonymen Aggregaten nachschiebbar. |
| LLM-Plattform | Bevorzugte Richtung Azure OpenAI EU | On-Prem-LLM zu aufwendig im Kursrahmen; Datenschutzfreigabe vorab klären (OI-5). |
| Pilot-Bereich | Noch offen (OI-1) | Höchste Priorität in den nächsten Schritten. |
| Quiz im MVP | Nur FR-6a (absolvieren), nicht FR-6b (Freigabe) | Plan §Aufwand: FR-6a = ~80 h, FR-6b organisatorisch im MVP unrealistisch. |

---

## Anhang B — Versionierung

| Version | Datum | Autor | Änderung |
|---|---|---|---|
| 1.0 (Draft) | 2026-05-06 | Frank Moritz / Claude | Erstkonsolidierung der Kickoff-Artefakte zu strukturiertem RE-Dokument. |
| 1.1 (Draft) | 2026-05-06 | Frank Moritz / Claude | Schärfungen nach BA-Review: FR-2 AC4 Klassifikations-Gate; FR-12 Goldfragen-Suite als Prozess-Story (operationalisiert NFR-QUA-1); FR-1 AC4/AC5 (Eingabe-Validierung, Telemetrie); FR-4 AC2 mit messbarem Self-Check-Schwellwert (80 % / 50 %); FR-8 Mock konkret spezifiziert; OI-7 vorgezogen auf W2 als Sprint-Voraussetzung für FR-1. |
