# Dialogverlauf — Modul 5B · Tag 1: Custom Tool & Agent-Loop für LearnFlow

*Session mit Claude Code · 2026-08-12*

> Roher Verlauf der Konversation. Enthalten ist der Dialogtext beider Seiten in
> Reihenfolge, inklusive der Zwischenbemerkungen während der Arbeit. Nicht
> enthalten sind die Werkzeugaufrufe selbst (Dateien lesen, Skripte ausführen,
> Tests starten) sowie die abschliessende Export-Anweisung.

---

## Nutzer

> `@"C:\Users\MoritzFrank\Downloads\ADAI_Modul5B_Tag1_Lab (2).docx"`
>
> was für ein Tool könnten wir für LearnFlow schreiben?

---

## Claude

*(Zwischenbemerkung vor dem Lesen des Handouts:)*

> I'll read the lab document first to see what it asks for.

*(Antwort nach Analyse von Handout, ADRs und Datasets:)*

Ich habe das Lab und den LearnFlow-Stand gelesen. Vier Kandidaten, die zum Projekt passen und klein genug für 45 Minuten sind:

### Die Kandidaten

| # | Tool | Was es tut | Warum es passt |
|---|------|-----------|----------------|
| **1** | `gold_dataset_lint` | Prüft einen Gold-Eval-Eintrag (YAML) gegen das ADR-009-Schema: Pflichtfelder, `category ∈ {in_corpus, out_of_corpus, adversarial}`, Konsistenz `expected_refusal` ↔ `reference_answer`, offene `TBD`s, Verteilung ~60/25/15 | Reales, ungelöstes Problem: 4 Datasets von 4 Personen, 105 Einträge, 87 × `TBD`, teils `.md` / teils `.yaml` |
| **2** | `citation_coverage` | Nimmt Antworttext + Liste gelieferter Chunk-IDs → Anteil belegter Segmente, ungültige Referenzen, Verdikt `ok`/`suppressed` | Ist wörtlich Stufe 2 aus ADR-008 — das Kernversprechen „0 % Halluzination" |
| **3** | `chunk_preview` | Ruft das bestehende `chunking.py` auf: Text + `chunk_size`/`overlap` → Anzahl Chunks, Tokenzahlen, ob Chunks mitten im Satz enden | Bindet echten, getesteten Projektcode ein statt Spielzeug-Logik |
| **4** | `confidence_band` | Score + Schwellen → `Hoch`/`Mittel`/`unterdrückt` (fail-closed, `>=`) | Sehr klein — eher Aufwärm-Übung als Deliverable |

### Empfehlung: #1 `gold_dataset_lint`

Gründe: Es ist das einzige davon, das **nach** dem Lab weiterlebt (EVAL-1 muss vor dem CI-Gate konsolidiert werden), und es demonstriert die Agent-Loop am besten — mit `Read` in `allowed_tools` liest der Agent selbständig `LearningCorpus/Eval-Gold-Dataset-Frank.md`, ruft euer Tool pro Eintrag auf und fasst zusammen. Das ist genau der „ToolUseBlock im Stream beobachten"-Check aus L3, und für die Präsentation habt ihr ein sichtbares Ergebnis statt einer Zahl.

Skizze:

```python
@tool("gold_lint", "Prüft einen Gold-Eval-Eintrag gegen das ADR-009-Schema",
      {"entry_yaml": str})
async def gold_lint(args):
    entry = yaml.safe_load(args["entry_yaml"])
    problems = []
    for field in ("id", "category", "question", "expected_refusal"):
        if field not in entry:
            problems.append(f"Pflichtfeld fehlt: {field}")
    if entry.get("category") not in {"in_corpus", "out_of_corpus", "adversarial"}:
        problems.append(f"ungültige category: {entry.get('category')!r}")
    if entry.get("expected_refusal") is False and not entry.get("reference_answer"):
        problems.append("beantwortbare Frage ohne reference_answer")
    if entry.get("expected_source_id") in (None, "TBD"):
        problems.append("expected_source_id noch TBD — nicht CI-tauglich")
    verdict = "OK" if not problems else "; ".join(problems)
    return {"content": [{"type": "text", "text": f"{entry.get('id','?')}: {verdict}"}]}
```

Für die Guardrails in L3 (`my_agent.py`): `allowed_tools=["mcp__learnflow__gold_lint", "Read"]`, `permission_mode="default"`, `max_turns=10`, `max_budget_usd=0.50` — und `cwd` auf das Repo-Root, damit `CLAUDE.md` greift. Als Hausaufgabe („zweiter Parameter") bietet sich `strict: bool` an, das zusätzlich die 60/25/15-Verteilung über die ganze Datei prüft.

Zwei Hinweise zum Lab-Handout: die Model-ID `claude-sonnet-4-6` daraus solltet ihr gegen die aktuell gültige Sonnet-ID prüfen, sonst fällt der Agent auf den Default zurück — genau die Kostenfalle, die das Handout beschreibt. Und startet das Skript wie dort verlangt aus dem Anaconda Prompt, nicht aus dieser Session heraus.

Soll ich #1 als lauffähiges `my_agent.py` plus Tool-Modul anlegen (auf einem Feature-Branch, mit einem kleinen pytest für die Lint-Regeln)?

---

## Nutzer

> ja mach das. Verwende das Verzeichnis Artefakten/Modul5Tag2. claude-sonnet-4-6 ist gültig.

---

## Claude

*(Zwischenbemerkung vor dem Anlegen der Dateien:)*

> Jetzt lege ich die Dateien an.

*(Zwischenbemerkung nach dem ersten Lauf gegen die echten Datasets:)*

> Der Lint hat direkt einen echten Fehler in einem der Datasets gefunden (kaputtes YAML). Das darf aber nicht die ganze Datei blockieren — ich mache das Parsen satzweise robust.

*(Zwischenbemerkung vor der Ergänzung:)*

> Jetzt die satzweise Parse-Funktion:

*(Zwischenbemerkung nach dem zweiten Lauf:)*

> Ein Detail stimmt noch nicht: die Verteilung wird durch nicht lesbare Einträge verzerrt.

*(Abschliessende Antwort:)*

Fertig — vier Dateien in `Artefakten/Modul5Tag2`:

| Datei | Inhalt |
|---|---|
| `gold_lint.py` | Regelmenge, reine Logik ohne SDK-Import — isoliert testbar |
| `my_agent.py` | `@tool` + `create_sdk_mcp_server` + Agent-Loop mit Guardrails (L2 + L3) |
| `test_gold_lint.py` | 27 Tests, ohne Netz und ohne API-Kosten — **alle grün** |
| `README.md` | Ausführung, Regelübersicht, Befundtabelle, Hausaufgaben-Ansatz |

### Was der Lint auf euren echten Datasets findet

Ich habe die Logik gegen alle vier Gold-Datasets laufen lassen (ohne Agent, also gratis):

| Dataset | Einträge | ohne Befund | häufigster Befund |
|---|---|---|---|
| Frank.md | 26 | 7 | 19 × `expected_source_id: TBD` |
| Reto.md | 27 | 7 | 17 × TBD, **3 × YAML nicht lesbar** |
| Christoph.md | 26 | 7 | 19 × TBD |
| Christoph.yaml | 26 | 7 | 19 × TBD |

Die drei kaputten Einträge in Retos Datei sind echt: typografische Anführungszeichen (`„…"`) innerhalb eines `"…"`-YAML-Strings, PyYAML bricht dort ab. Das hat mich dazu gebracht, das Parsen satzweise robust zu machen — ein kaputter Eintrag blockiert nicht mehr die Prüfung der übrigen 24. Für die Präsentation ist das euer bester Moment: das Tool hat beim ersten Lauf einen Fehler gefunden, den niemand gesehen hat.

### Was ich verifiziert habe — und was nicht

- `pytest` in der conda-Umgebung `adai`: 27/27 grün.
- Tool-Verdrahtung gegen das echte SDK geprüft (`@tool`-Handler + `create_sdk_mcp_server`), ohne API-Aufruf.
- **Nicht ausgeführt: `my_agent.py`.** Das Handout verlangt ausdrücklich den Start aus dem Anaconda Prompt, damit der API-Key-Weg getestet wird — aus dieser Session heraus würde der Agent die Abo-Anmeldung erben und genau das verfehlen. Der erste echte Lauf gehört euch:

```bash
python Artefakten/Modul5Tag2/my_agent.py
```

Zwei Hinweise: In der `adai`-Umgebung fehlten `pyyaml` und `pytest` — die habe ich dort per pip nachinstalliert. Und die vier Dateien sind bewusst nur angelegt, nicht committet; ihr steht gerade auf `feat/T-24-config-confidence-threshold`, das Lab-Material gehört auf einen eigenen Branch.

---

*Ende des Verlaufs. Die Dateien liegen inzwischen in `Artefakten/Modul5BTag1/`; die im Dialog genannten Pfade `Artefakten/Modul5Tag2/...` sind entsprechend zu lesen.*
