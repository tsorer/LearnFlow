# Protokoll — Modul 5B · Tag 1: Custom Tool & Agent-Loop für LearnFlow

*Session mit Claude Code · 2026-08-12 · Branch `feat/T-24-config-confidence-threshold` · Arbeitsverzeichnis `Artefakten/Modul5BTag1`*

---

## 1. Auftrag

Ausgangspunkt war das Lab-Handout `ADAI_Modul5B_Tag1_Lab (2).docx` und die Frage:
**„Was für ein Tool könnten wir für LearnFlow schreiben?"**

Deliverables laut Handout:

| # | Deliverable |
|---|---|
| 1 | Laufender Agent (`first_agent.py`, mit API-Key statt `/login`) |
| 2 | Eigenes Custom Tool via `@tool` + `create_sdk_mcp_server` |
| 3 | Eigene Agent-Loop mit `max_turns`, `max_budget_usd`, `permission_mode` |
| 4 | Kurzpräsentation (3 Min) |

---

## 2. Analyse

Gelesen wurden: das Lab-Handout, `CLAUDE.md`, die ADRs 008 (Konfidenz-Pipeline) und
009 (Eval-Strategie), `Src/backend/app/services/` (config, chunking) sowie die vier
Gold-Eval-Datasets in `LearningCorpus/`.

Zahlenstand der Datasets zum Zeitpunkt der Analyse: 105 Einträge über vier Dateien,
davon 87 mit `TBD`-Platzhaltern, teils als `.md`, teils als `.yaml`.

### Vier Tool-Kandidaten

| # | Tool | Was es tut | Bezug |
|---|---|---|---|
| 1 | `gold_dataset_lint` | Prüft Gold-Eval-Einträge gegen das Schema | ADR-009, EVAL-1 |
| 2 | `citation_coverage` | Anteil belegter Antwort-Segmente, Verdikt `ok`/`suppressed` | ADR-008, Stufe 2 |
| 3 | `chunk_preview` | Ruft `chunking.py` auf: Chunk-Anzahl, Tokenzahlen, Satzgrenzen | ADR-007 |
| 4 | `confidence_band` | Score + Schwellen → `Hoch`/`Mittel`/`unterdrückt` | ADR-008 |

### Entscheid: Kandidat 1

Begründung:

- **Lebt nach dem Lab weiter** — EVAL-1 muss konsolidiert werden, bevor das
  CI-Gate EVAL-3 verbindlich wird. Die anderen drei wären Demo-Code.
- **Beste Demo der Agent-Loop** — mit `Read` in `allowed_tools` liest der Agent
  die Dataset-Datei selbst und schickt den YAML-Teil durch das Tool. Damit ist der
  `ToolUseBlock`-Check aus L3 sichtbar erfüllt.
- **Sichtbares Ergebnis für die Präsentation** statt einer einzelnen Zahl.

---

## 3. Umsetzung

Vier Dateien in `Artefakten/Modul5BTag1/`:

| Datei | Rolle |
|---|---|
| `gold_lint.py` | Regelmenge, reine Logik **ohne** SDK-Import |
| `my_agent.py` | `@tool` + `create_sdk_mcp_server` + Agent-Loop mit Guardrails |
| `test_gold_lint.py` | 27 Tests, ohne Netz und ohne API-Kosten |
| `README.md` | Ausführung, Regelübersicht, Befundtabelle |

**Bewusste Trennung:** Die Lint-Logik hat keine Abhängigkeit zum
`claude_agent_sdk`. Damit ist die Regelmenge isoliert testbar (DoD-Kriterium 3) und
später auch ausserhalb des Agenten nutzbar — etwa als CI-Vorprüfung.

### Regeln (pro Eintrag)

- Pflichtfelder `id`, `category`, `question`, `expected_refusal`
- `category` ∈ `in_corpus` · `out_of_corpus` · `adversarial`
- `out_of_corpus` muss `expected_refusal: true` haben — sonst misst das
  Refusal-Gate (≥ 90 %, ADR-009) am eigenen Testfall vorbei
- beantwortbare Frage ohne `reference_answer` → Befund
- `expected_refusal: true` **mit** `reference_answer` → Widerspruch zu fail-closed
  (ADR-008: unterdrückte Antworten liefern nie generierten Inhalt)
- beantwortbare Frage mit `expected_source_id: TBD` → nicht CI-tauglich

### Regeln (dateiweit)

- doppelte IDs
- Kategorie-Verteilung gegen ~60/25/15 (±10 Prozentpunkte)
- Umfang gegen den Pilot-Zielwert ~80–100 Fragen

### Guardrails (L3)

```python
model="claude-sonnet-4-6"   # explizit, sonst greift ein teurerer Default
cwd=REPO_ROOT               # damit relative Pfade und CLAUDE.md passen
allowed_tools=["mcp__learnflow__gold_lint", "Read"]
permission_mode="default"
max_turns=10
max_budget_usd=0.50
```

---

## 4. Zwei Korrekturen während der Umsetzung

**(a) Kaputtes YAML blockierte die ganze Datei.** Der erste Lauf gegen die echten
Datasets brach mit einem `yaml.parser.ParserError` ab. Ursache war kein Fehler im
Lint, sondern ein echter Fund: typografische Anführungszeichen (`„…"`) innerhalb
eines `"…"`-YAML-Strings in Retos Datei. Konsequenz — das Parsen fällt jetzt
satzweise zurück: lesbare Einträge werden geprüft, kaputte als eigener Befund
gemeldet. Ein falsches Anführungszeichen darf nicht 24 andere Einträge ungeprüft
lassen.

**(b) Verteilung wurde durch kaputte Einträge verzerrt.** Retos Datei meldete
zunächst „Verteilung in_corpus: 44 %" — ein Artefakt, weil die drei nicht lesbaren
Einträge keine Kategorie haben, aber im Nenner standen. Der Nenner zählt jetzt nur
noch eingeordnete Einträge; der falsche Befund ist verschwunden. Zusätzlich werden
Verteilungs-Befunde erst ab 10 Einträgen gemeldet — bei einem einzelnen Eintrag ist
ein Anteil keine Aussage.

---

## 5. Befund auf dem aktuellen Stand

| Dataset | Einträge | ohne Befund | häufigster Befund |
|---|---|---|---|
| `Eval-Gold-Dataset-Frank.md` | 26 | 7 | 19 × `expected_source_id: TBD` |
| `Eval-Gold-Dataset-Reto.md` | 27 | 7 | 17 × `TBD`, **3 × YAML nicht lesbar** |
| `Eval_Gold-Dataset-Christoph.md` | 26 | 7 | 19 × `expected_source_id: TBD` |
| `Eval_Gold-Dataset-Christoph.yaml` | 26 | 7 | 19 × `expected_source_id: TBD` |

Alle vier Dateien melden zusätzlich den Umfang (26–27 statt ~80–100 Fragen laut
ADR-009). Die drei nicht lesbaren Einträge sind ein echter Fund, kein Lint-Artefakt.

---

## 6. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `pytest` in conda-env `adai` | 27/27 grün |
| `py_compile` über alle drei Skripte | ok |
| Tool-Verdrahtung gegen echtes SDK (`@tool`-Handler, `create_sdk_mcp_server`) | ok, ohne API-Aufruf |
| Lint gegen alle vier echten Datasets | läuft durch, Befunde plausibel |
| **`my_agent.py` End-to-End** | **nicht ausgeführt** |

Der Agent-Lauf wurde bewusst **nicht** gestartet: Das Handout verlangt den Start aus
dem Anaconda Prompt, damit der API-Key-Weg getestet wird. Aus einer
Claude-Code-Session heraus würde der Agent die Abo-Anmeldung erben und genau das
verfehlen. Der erste echte Lauf gehört ins Lab.

---

## 7. Kommandos

```bash
pip install pyyaml pytest
```

```bash
pytest Artefakten/Modul5BTag1
```

```bash
python Artefakten/Modul5BTag1/my_agent.py
```

---

## 8. Offene Punkte

1. **Erster Agent-Lauf** aus dem Anaconda Prompt — `total_cost_usd` und `num_turns`
   für die Präsentation notieren.
2. **Experiment aus L3:** `max_turns=1` setzen und beobachten, dass der Agent nach
   dem `Read` nicht mehr zum Tool-Aufruf kommt.
3. **Retos drei kaputte Einträge** reparieren (Anführungszeichen).
4. **Branch:** Die Dateien sind angelegt, aber nicht committet. Das Lab-Material
   gehört auf einen eigenen Branch, nicht auf `feat/T-24-config-confidence-threshold`.
5. **Hausaufgabe bis Tag 2:** zweiter Parameter `strict: bool` — zusätzlich prüfen,
   dass `expected_source` gesetzt ist und `version_sensitive` bei Beträgen `true` ist.

---

## 9. Umgebungs-Notizen

- conda-env `adai`: Python 3.12.13, `claude_agent_sdk` vorhanden; `pyyaml` und
  `pytest` fehlten und wurden in dieser Session nachinstalliert.
- Der Standard-Python auf dem PATH ist **nicht** die `adai`-Umgebung — Skripte und
  Tests mit dem Interpreter aus `miniconda3/envs/adai` starten.
