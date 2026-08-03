# Chatverlauf — Definition of Done & CI-Setup

*Projekt: LearnFlow · Modul 4 Tag 1 · 2026-06-10*

Dieser Verlauf dokumentiert die Erarbeitung der Definition of Done (`Docs/07_Definition-of-Done.md`)
und des zugehörigen CI-Scaffolds (`src/backend`, `src/frontend`, `.github/workflows/ci.yml`,
`Makefile`, `Ops/09_CI-Runbook.md`). Prompts sind wörtlich, Antworten zusammengefasst.

---

## 1 · Prompt (Frank)

> Wir sind ein Team von 2-3 Entwicklern, 3 Monate Zeit. Tech-Stack: siehe docs-Verzeichnis
>
> Hilf uns eine Definition of Done zu erstellen. Sie soll:
> - Realistisch für ein kleines Team sein
> - Qualität sichern ohne uns zu lähmen
> - Konkret und überprüfbar sein
>
> Schlage 6-8 Kriterien vor. Für jedes: warum ist es wichtig?

### Antwort (Zusammenfassung)

Nach Sichtung der `Docs/` (ADR-002 Stack, Quality Attributes, ADR-009 Eval-Strategie) drei
prägende Rahmenbedingungen identifiziert: Code wird KI-generiert (Claude Code), das Team
reviewt; Reliability ist existenziell (Halluzinationsrate 0 %, Gold-Dataset als CI-Gate);
Budget knapp (360 h). Daraus 7 Kriterien vorgeschlagen:

1. Review durch eine zweite Person (nicht Autor/Prompter)
2. CI grün: Lint + Type-Check + Tests
3. Unit-Tests für neue Logik; RAG-Komponenten isoliert testbar
4. Eval-Gate nicht verschlechtert (bei RAG-Changes)
5. Akzeptanzkriterien erfüllt + einmal manuell durchgespielt
6. Security-/DSGVO-Pfad geprüft
7. Schwellenwerte/Konfiguration nicht hartcodiert

Plus optional: ADR/Docs aktualisiert. Bewusst weggelassen: feste Coverage-Quoten, zwei
Reviewer, Doku-Pflicht pro PR, separate QA-Phase.

---

## 2 · Prompt (Frank)

> Punkte 6 und 7 weglassen. Dafür ein Punkt für die Code-Qualität ergänzen

### Antwort (Zusammenfassung)

Punkte 6 und 7 entfernt, neuer Punkt 6 ergänzt: **Code-Qualität aktiv geprüft** — kein
toter/ungenutzter Code, dem Modulschnitt folgend, keine unnötige Komplexität. Begründung:
Claude Code produziert oft plausibel aussehenden Ballast; im modularen Monolithen erodiert
das schnell die Wartbarkeit; Lint/Typing fangen das nicht ab — bewusste Review-Frage.

Resultierende DoD: 6 Kriterien + optional ADR/Docs-Aktualisierung.

---

## 3 · Prompt (Frank)

> was bedeutet CI grün? Wie soll das verifiziert werden?

### Antwort (Zusammenfassung)

Erklärt: „CI" = bei jedem Push/PR läuft automatisch ein Satz Checks auf einem Server
(GitHub Actions); „grün" = alle Checks Exit-Code 0. Für den Stack (ADR-002) konkret:
Backend `ruff`/`mypy`/`pytest`, Frontend `eslint`/`tsc --noEmit`/`vitest`. Zwei
Verifikationsebenen: lokal vor dem Push (ein `make check`/`npm run check`) und in der CI
als erzwungenes Merge-Gate (Branch Protection). Hinweis: Repo enthielt noch keine CI.

---

## 4 · Prompt (Frank)

> Bitte erstellen und ganz konkret zeigen, wie es verwendet werden kann.

### Antwort (Zusammenfassung)

CI-Scaffold angelegt: `.github/workflows/ci.yml` (Jobs `backend`/`frontend`), root
`Makefile` (`make check`), minimale Beispielmodule mit Tests plus Tool-Configs. Grün→rot
am Beispiel `should_answer` demonstriert: 4 Tests grün (Exit 0); `>=` zu `>` geändert →
rot (Exit 1); zurückgenommen → grün. Hinweis: PyPI/npm in der Sandbox gesperrt, daher
Demo über Pythons Standard-Testrunner; Lockfile muss committet werden.

---

## 5 · Prompt (Frank)

> wieso `runs-on: ubuntu-latest` — spielt es eine Rolle, wenn Windows verwendet wird oder
> ist es egal?

### Antwort (Zusammenfassung)

`runs-on` = OS des CI-Runners in der GitHub-Cloud, unabhängig vom lokalen Entwickler-OS.
Linux ist richtig, weil Prod in Docker/Linux läuft (CI testet, was ausgeliefert wird).
Für die CI ist Windows-Entwicklung egal; drei lokale Stolpersteine genannt: `make` nicht
nativ auf Windows, Zeilenenden (CRLF/LF), Case-Sensitivity bei Importen.

---

## 6 · Prompt (Frank)

> nein ist gut so. Bitte die DoD im Docs-Verzeichnis erstellen

### Antwort (Zusammenfassung)

`Docs/09_Definition-of-Done.md` erstellt — 6 Kriterien + optionaler 7., Kriterium 2 um die
„grün"-Präzisierung ergänzt, referenziert auf ADRs/Docs und das Runbook.
*(Datei später von Frank umbenannt zu `Docs/07_Definition-of-Done.md`.)*

---

## 7 · Prompt (Frank)

> Die Datei wurde in 07_Definition-of-Done.md umbenannt. Bei Punkt 5 verallgemeinern und
> nicht auf die Datei verweisen (da es in GitHub sein wird)

### Antwort (Zusammenfassung)

Punkt 5 verallgemeinert: Verweis auf `Docs/07_Backlog.md` ersetzt durch „alle
Akzeptanzkriterien der Story".

---

## 8 · Prompt (Frank)

> lösche wieder die Testdaten, so dass nur die notwendigen Config-Dateien für die Tests
> bleiben. Erstelle ein Unterzeichnis 'src', wo dann backend und frontend vorhanden sind

### Antwort (Zusammenfassung)

Beispiel-/Testdaten gelöscht (Dateilöschung im Ordner freigegeben), nur Configs behalten
und nach `src/backend` bzw. `src/frontend` verschoben. Pfade in `Makefile`, `ci.yml` und
Runbook auf `src/...` angepasst.

---

## 9 · Prompt (Frank)

> wieso `runs-on: ubuntu-latest` … (Rückfrage zu Windows — siehe oben)

*(Im Verlauf: erneute Bestätigung, dass für die CI das lokale OS irrelevant ist.)*

---

## 10 · Prompt (Frank) — CI-Fehler

> Run mypy — mypy: can't read file 'app': No such file or directory — Error: Process
> completed with exit code 2.

### Antwort (Zusammenfassung)

Ursache: Configs zeigten noch auf die gelöschten Ordner `app/`/`tests/`. Checks so
umgestellt, dass ein reines Config-Repo grün ist und automatisch greift, sobald Code
kommt: `mypy` läuft erst bei vorhandener `.py`-Datei (Guard), `pytest` wertet Exit 5
(„keine Tests") als grün, `tsc` läuft erst bei vorhandener `.ts`/`.tsx`
(`scripts/check-types.mjs`), `vitest --passWithNoTests`, eslint-Node-Globals ergänzt.
Guard-Logik in der Sandbox verifiziert.

---

## 11 · Prompt (Frank)

> braucht es check-types.mjs oder kann die Datei wieder gelöscht werden?

### Antwort (Zusammenfassung)

Nur nötig, solange das Frontend leer ist (`tsc` bricht sonst mit TS18003 ab). Optionen:
liegen lassen (schaltet sich automatisch auf echten `tsc` um, kein Pflegeaufwand) oder
nach der ersten `.ts`-Datei löschen und `typecheck` auf `tsc --noEmit` zurücksetzen.
Empfehlung: vorerst liegen lassen.

---

## 12 · Prompt (Frank)

> liegen lassen

### Antwort (Zusammenfassung)

`check-types.mjs` bleibt; schaltet sich selbst auf den echten `tsc`-Lauf um, sobald Code
dazukommt.

---

## 13 · Prompt (Frank) — CI-Fehler

> npm error code EUSAGE … The `npm ci` command can only install with an existing
> package-lock.json … Muss noch was auf GitHub konfiguriert werden?

### Antwort (Zusammenfassung)

Kein GitHub-Setting, sondern fehlender Lockfile. Sauberer Fix: einmal `npm install` in
`src/frontend`, `package-lock.json` committen und pushen — danach läuft `npm ci`.
Alternative Übergangslösung: in `ci.yml` `npm ci` → `npm install`. Empfehlung: Lockfile
committen.

---

## 14 · Prompt (Frank)

> bitte den Chatverlauf inklusive Prompts nach Frank/Modul4Tag1/DoD_Chatverlauf.md
> exportieren

### Antwort

Dieser Export.

---

## Resultierende Artefakte

| Datei | Zweck |
|---|---|
| `Docs/07_Definition-of-Done.md` | Definition of Done (6 Kriterien + optional) |
| `Ops/09_CI-Runbook.md` | Anleitung „CI grün" lokal + als Merge-Gate |
| `.github/workflows/ci.yml` | CI-Jobs backend/frontend |
| `Makefile` | `make check` (lokal identisch zur CI) |
| `src/backend/` | `pyproject.toml`, `requirements-dev.txt` |
| `src/frontend/` | `package.json`, `tsconfig.json`, `eslint.config.js`, `scripts/check-types.mjs` |

### Offener Punkt

`src/frontend/package-lock.json` muss noch per `npm install` erzeugt und committet werden,
damit der Frontend-CI-Job (`npm ci`) grün läuft.
