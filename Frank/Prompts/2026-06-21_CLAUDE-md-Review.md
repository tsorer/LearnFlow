# Chatverlauf — CLAUDE.md Review & Überarbeitung

**Datum:** 2026-06-21
**Branch (Arbeit):** `docs/claude-md-revision` (von `main` abgezweigt)
**Thema:** Beurteilung und Überarbeitung der `CLAUDE.md`

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> beurteile unsere claude.rm. Ist sie zu ausführlich? Fehlt etwas wichtiges?

### Claude

- Befund vorab: `CLAUDE.md` war im Arbeitsverzeichnis **gelöscht** (`D`), existierte nur im letzten Commit → mit `git restore CLAUDE.md` zurückholbar; eine im Working Tree fehlende Datei wird nicht als Kontext geladen.
- **Gesamturteil:** solide, gut strukturiert, ~90 Zeilen — **nicht zu lang**; Verweise auf `Docs/` als Single Source of Truth statt Inhalte zu duplizieren sind richtig.
- **Zu ausführlich/redundant:** Abschnitt „Was Claude NICHT tun soll" wiederholt Punkte aus „Konventionen" (kein commit auf `main`, `package.json`/Lockfile, Spike-Verzeichnisse). Vorschlag: NICHT-Liste auf echte projektspezifische Tripwires eindampfen (ADR-008/009, OpenAI-Direct-Sperre, Secrets).
- **Ungenauigkeiten:** Backlog-Quelle (GitHub Issues vs. Markdown) prüfen; `Christoph/` als Spike-Dir existierte real nicht.
- **Fehlt:** konkrete Dev-/Test-Befehle (Einzeltests, Backend/Frontend lokal, `.env`), Migrations-Workflow (Alembic), konkretere Coding-Standards.
- **Fazit:** straffbar um ~15 Zeilen (Redundanz), gleichzeitig an einer Stelle zu dünn (fehlende Befehle).

---

## 2 — Nutzer

> erstelle auf Basis vom mail-Branch einen neuen Branch und erstelle dort einen Vorschlag für die Datei

### Claude

- `src/README.md` und `src/Makefile` gelesen, um echte Befehle/Containernamen zu übernehmen.
- Branch `docs/claude-md-revision` von `main` erstellt.
- Backlog-Quelle „GitHub Issues" via `Reto/Modul4Tag1/create-issues.ps1` plausibilisiert → beibehalten.
- Überarbeitete `CLAUDE.md` geschrieben und committet (`630c815`):
  - neuer Abschnitt „Entwicklung (aus `src/`)" mit echten Befehlen
  - NICHT-Liste → „Tripwires" (gekürzt, entdoppelt)
  - QA-Befehle präzisiert (`mypy app worker`, `npm run check`, `ruff check .`)
  - Stil-Regel ergänzt; `Christoph/` (damals) entfernt

---

## 3 — Nutzer

> ein Verzeichnis für Christoph wird es zukünftig geben, bitte belassen. Wird nicht zu oft angegeben, dass das Docs-Verzeichnis massgeblich ist? Reicht es nicht einmal?

### Claude

- `Christoph/` wieder aufgenommen (Struktur + Tripwire-Zeile).
- „Docs ist maßgeblich" stand 4× → auf **eine** Aussage im Header reduziert; übrige Stellen sagen nur noch etwas über die jeweiligen Verzeichnisse aus (veraltet/Spike).
- Commit `30f497b`.

---

## 4 — Nutzer

> stehen in src/readme nicht eh nur Dinge die du schon weisst und ist für menschliche Entwickler gedacht?

### Claude

- Zustimmung, teilweise: `src/README.md` ist menschengedacht; Duplikat = Drift-Risiko.
- Unterscheidung: ableitbares Mensch-Onboarding (`.env`, App-URL, `make up/seed/down/logs`) gehört nur ins README; **nicht ableitbare** Befehle (Containernamen `src-api-1`/`src-db-1`, Einzeltest-Muster, Migrations-Befehl) bringen inline echten Mehrwert.
- Vorschlag: `Entwicklung`-Sektion auf den DoD-/Verifizier-Workflow eindampfen, Setup ans README verweisen.

---

## 5 — Nutzer

> ja

### Claude

- Separate `Entwicklung`-Sektion gestrichen (vermeidet auch interne Doppelung von `make qa`).
- Nicht-ableitbare Befehle (Einzeltests, Migration) in „Qualität & Konventionen" eingefaltet.
- Setup/Logins/psql → Verweis auf `src/README.md`.
- Commit `15de468` (−19/+6).

---

## 6 — Nutzer

> bitte noch den Chatverlauf als md-Datei nach Frank/Prompts exportieren

### Claude

- `Frank/Prompts/` angelegt und diesen Verlauf exportiert.
- Bewusst **nicht** auf dem CLAUDE.md-PR-Branch committet (persönliches Artefakt gehört nicht in den Doc-PR).

---

## Resultierende Commits auf `docs/claude-md-revision`

| Commit    | Inhalt |
|-----------|--------|
| `630c815` | CLAUDE.md straffen + Dev-/Test-Befehle ergänzen |
| `30f497b` | Christoph/ behalten, SSoT-Aussage entdoppeln |
| `15de468` | README-Duplikate raus, Befehle in Qualität-Sektion gefaltet |
