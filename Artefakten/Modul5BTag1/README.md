# Modul 5B · Tag 1 — Lab-Abgabe: Gold-Eval-Linter

Custom Tool + Agent-Loop für LearnFlow. Das Tool `gold_lint` prüft Einträge des
Gold-Eval-Datasets (ADR-009, Enabler EVAL-1) gegen das Schema — die Vorstufe zum
CI-Gate EVAL-3.

| Datei | Rolle |
|---|---|
| `gold_lint.py` | Regelmenge, reine Logik ohne SDK-Abhängigkeit — isoliert testbar |
| `my_agent.py` | `@tool` + `create_sdk_mcp_server` + Agent-Loop mit Guardrails (L2 + L3) |
| `combined_agent.py` | Beide Tools (`celsius_to_f` aus `second_agent.py` + `gold_lint`) an **einem** Server |
| `test_gold_lint.py` | 27 Tests für die Regeln, ohne Netz und ohne API-Kosten |

## Ausführen

Voraussetzung: conda env `adai`, `ANTHROPIC_API_KEY` im selben Fenster gesetzt
(**nicht** `/login`), und einmalig:

```bash
pip install pyyaml pytest
```

Tests (kosten nichts):

```bash
pytest Artefakten/Modul5BTag1
```

Agent (aus dem Anaconda Prompt, nicht aus einer Claude-Code-Session):

```bash
python Artefakten/Modul5BTag1/my_agent.py
```

Variante mit zwei Tools an einem Server:

```bash
python Artefakten/Modul5BTag1/combined_agent.py
```

## Was das Tool prüft

Pro Eintrag:

- Pflichtfelder `id`, `category`, `question`, `expected_refusal`
- `category` ∈ `in_corpus` · `out_of_corpus` · `adversarial`
- `out_of_corpus` muss `expected_refusal: true` haben — sonst misst das
  Refusal-Gate (≥ 90 %, ADR-009) am eigenen Testfall vorbei
- beantwortbare Frage ohne `reference_answer` → Befund
- `expected_refusal: true` **mit** `reference_answer` → Widerspruch zu
  fail-closed (ADR-008: unterdrückte Antworten liefern nie generierten Inhalt)
- beantwortbare Frage mit `expected_source_id: TBD` → nicht CI-tauglich
- nicht lesbares YAML wird als Befund gemeldet, ohne die übrigen Einträge zu
  blockieren

Dateiweit: doppelte IDs, Kategorie-Verteilung gegen ~60/25/15 (±10 Prozentpunkte,
nur über lesbare Einträge), Umfang gegen den Pilot-Zielwert ~80–100 Fragen.

## Befund auf dem aktuellen Stand (Stand 2026-08-12)

| Dataset | Einträge | ohne Befund | häufigster Befund |
|---|---|---|---|
| `Eval-Gold-Dataset-Frank.md` | 26 | 7 | 19 × `expected_source_id: TBD` |
| `Eval-Gold-Dataset-Reto.md` | 27 | 7 | 17 × `TBD`, 3 × YAML nicht lesbar |
| `Eval_Gold-Dataset-Christoph.md` | 26 | 7 | 19 × `expected_source_id: TBD` |
| `Eval_Gold-Dataset-Christoph.yaml` | 26 | 7 | 19 × `expected_source_id: TBD` |

Die drei nicht lesbaren Einträge in Retos Datei sind typografische
Anführungszeichen (`„…"`) innerhalb eines `"…"`-YAML-Strings — ein echter Fund,
kein Lint-Artefakt.

## Guardrails (L3)

```python
model="claude-sonnet-4-6"   # explizit, sonst greift ein teurerer Default
allowed_tools=["mcp__learnflow__gold_lint", "Read"]
permission_mode="default"
max_turns=10
max_budget_usd=0.50
```

Für das Experiment aus dem Lab (`max_turns=1`): der Agent kommt nach dem `Read`
nicht mehr dazu, das Tool aufzurufen — der Lauf endet ohne Ergebnis, aber ohne
Fehler. Das ist der Grund, warum das Limit oberhalb der erwarteten
Werkzeugkette liegen muss.

## Zwei Tools an einem Server (`combined_agent.py`)

`create_sdk_mcp_server(..., tools=[celsius_to_f, gold_lint])` nimmt beliebig
viele Tools; der Schlüssel aus `mcp_servers` wird zum gemeinsamen Präfix:
`mcp__learnflow__celsius_to_f` und `mcp__learnflow__gold_lint`. Beide müssen
einzeln in `allowed_tools` stehen — der Server-Eintrag allein erlaubt nichts.

Der Prompt stellt bewusst zwei unzusammenhängende Aufgaben (Umrechnung +
Dataset-Prüfung), damit sichtbar wird, dass das Modell pro Teilaufgabe selbst
das passende Tool wählt. Am Ende des Laufs zählt das Skript die Tool-Aufrufe
nach Namen — dieser Zähler ist der Beleg für die Präsentation.

## Hausaufgabe bis Tag 2

Zweiter Parameter `strict: bool` — im strikten Modus zusätzlich prüfen, dass
`expected_source` gesetzt ist und dass `version_sensitive` bei Beträgen `true`
ist (die Teuerungsanpassung ist der häufigste Grund für veraltete
Referenzantworten).
