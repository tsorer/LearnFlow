# LearnFlow — Definition of Done (DoD)

*Modul 3 · Juni 2026 · Team: Frank, Niklaus, Reto, Christoph*

---

## Zweck

Ein gemeinsamer, überprüfbarer Standard dafür, wann eine Aufgabe *fertig* ist —
zugeschnitten auf ein 2–3-Personen-Team mit knappem Budget (360 h Umsetzung) und
auf das Implementierungsmodell aus ADR-002: **Code wird KI-gestützt mit Claude Code
erzeugt; die Teammitglieder sind primär Reviewer und Verifizierer.** Daraus folgt das
Leitprinzip dieser DoD — das **menschliche Review und die automatisierten Gates sind
die Qualitätssicherung**, nicht das Schreiben des Codes.

Die DoD sichert Qualität, ohne zu lähmen: bewusst keine festen Coverage-Quoten, keine
zwei Reviewer, keine Doku-Pflicht pro PR, keine separate QA-Phase.

---

## Kriterien

Eine Aufgabe gilt als *Done*, wenn **alle** zutreffenden Kriterien erfüllt sind.

### 1. Review durch eine zweite Person — nicht Autor/Prompter des Codes

**Überprüfbar:** PR von genau einer Person approved, die ihn nicht selbst erzeugt hat.

**Warum:** Bei KI-generiertem Code *ist* das menschliche Review die Qualitätssicherung
(ADR-002). Genau die Fehlerklasse von Claude Code — erfundene Signaturen, falsche
Props, veraltete APIs — fällt nur im Review auf. Zwei Approver wären für ein Team
dieser Größe Overkill.

### 2. CI grün: Lint + Type-Check + Tests

**Überprüfbar:** Grüner Haken am PR. Lokal liefert `make check` denselben Stand
(Backend: `ruff` · `mypy` · `pytest` — Frontend: `eslint` · `tsc --noEmit` · `vitest`).
„Grün" heißt: jeder Check hat Exit-Code 0. In CI als Merge-Gate erzwungen (Branch
Protection auf `main`). Details: `Ops/09_CI-Runbook.md`.

**Warum:** TypeScript- und Python-Typing sind das Compile-Zeit-Netz gegen genau die
KI-Fehler aus Kriterium 1 — aber nur, wenn sie maschinell und für alle gleich erzwungen
werden statt „lief bei mir".

### 3. Unit- und Integrationstests für neue Logik; RAG-Komponenten isoliert testbar

**Überprüfbar:** Neue Geschäftslogik wird mit Unit- und Integrationstests getestet;
die betroffene RAG-Komponente (Chunking, Embedding, Retrieval, Generierung) ist ohne
die anderen aufrufbar.

**Warum:** RAG-Qualität ist empirisch, nicht per Code-Review validierbar
(Testability-NFA). Ohne Test pro Komponente bleibt unklar, welche Stufe regrediert.
Bewusst *keine* Coverage-Prozentvorgabe — nur das Vorhandensein eines Tests.

### 4. Eval-Gate nicht verschlechtert (bei RAG-relevanten Änderungen)

**Überprüfbar:** CI-Eval-Lauf zeigt keine Regression der harten Gates —
Halluzinationsrate = 0 %, Out-of-Corpus-Refusal ≥ 90 % auf dem Gold-Dataset
(ADR-009). Gilt nur für Änderungen an der Pipeline; reine UI-/Infra-Changes nicht.

**Warum:** Das ist das Alleinstellungs-Kriterium des Produkts. Eine halluzinierte
Antwort mit echter Quellenangabe ist unsichtbar und bricht das Vertrauen irreparabel
(Reliability, Rang 1). Jede Pipeline-Änderung kann das still kaputtmachen.

### 5. Akzeptanzkriterien erfüllt und einmal manuell durchgespielt

**Überprüfbar:** Alle Akzeptanzkriterien der Story abgehakt; Feature einmal im
laufenden System ausgeführt.

**Warum:** Grüne Tests heißen nicht „macht das Richtige". Ein manueller Durchlauf des
Happy Path fängt, was Tests nicht abbilden.

### 6. Code-Qualität aktiv geprüft: kein Ballast, Modulschnitt, keine Überkomplexität

**Überprüfbar:** Reviewer-Checkliste — kein auskommentierter/ungenutzter Code, Änderung
liegt im richtigen Modul ohne Querschnitt-Leaks, keine Abstraktion ohne zweiten
Aufrufer.

**Warum:** Claude Code produziert oft plausibel aussehenden Ballast (ungenutzte
Scaffolding-Reste, überflüssige Abstraktionen, Copy-Paste). Weil das Team reviewt statt
schreibt, ist „sieht okay aus, durchgewunken" ein reales Risiko; im modularen Monolithen
(ADR-001) erodiert das schnell die Wartbarkeit. Lint/Typing (Kriterium 2) fangen das
*nicht* — es ist eine bewusste Review-Frage.

---

## Optional

### 7. ADR/Docs aktualisiert, wenn ein Architekturentscheid berührt ist

**Warum:** `Docs/` ist die Single Source of Truth (CLAUDE.md). Wird ein Entscheid
geändert, ohne die Doku nachzuziehen, driftet die Quelle — der teuerste Fehler in einem
dokumentengetriebenen Projekt.

---

## Bewusst weggelassen (würde das Team lähmen)

Feste Coverage-Quoten · zwei Reviewer · Doku-Pflicht pro PR · separate manuelle
QA-Phase · hartkodierte Schwellenwerte als Blocker (stattdessen organisch über
Maintainability-NFA und Code-Review abgedeckt).
