# BandFor — Praxis-Test 2 (Modul 5B, Tag 2)

Ein Orchestrator, der an drei Spezialisten delegiert — **planner → generator →
evaluator** — um ein Feature aus dem eigenen Sprint-Backlog zu bauen. Gewähltes
Feature: **`band_for(score, medium, high)`** aus T-23 / ADR-008
(`src/backend/app/services/confidence.py`), die Funktion, die einen
Konfidenz-Score in `hoch` / `mittel` / `niedrig` einordnet.

Muster übernommen vom `PGE`-Ordner (dort baut dieselbe Pipeline `is_schaltjahr`).

## Die drei Rollen (die Abgabe der Übung)

Jede Rolle ist ein Subagent mit einem `system_prompt` in 1–2 Sätzen (`prompt=` in
`test_band_for.py`) und **schreibt ihr Ergebnis als Datei** ins aktuelle
Verzeichnis:

- **planner** → `spec.md` — Inputs, Output (`hoch`/`mittel`/`niedrig`), Grenzfälle
  mit Zahlen. Kein Code. (`tools=["Write"]`)
- **generator** → `code.py` — liest `spec.md`, setzt die Spec als reine
  Python-Funktion `band_for` um. (`tools=["Read","Write"]`)
- **evaluator** → `report.md` — liest `spec.md` + `code.py`, urteilt `PASS`/`FAIL`.
  (`tools=["Read","Write"]`)

Die anschaulichen Grenzfälle: Score genau auf `medium` bzw. `high` gehört ins
höhere Band (`>=`), und `medium == high` lässt das Mittelband wegfallen (`high`
wird zuerst geprüft).

## Dateien

| Datei | Was | Kosten |
|---|---|---|
| `test_band_for.py` | der echte Lauf: Orchestrator + drei Subagenten, ruft das Modell | ~$ (Deckel 0.60) |
| `smoke_band_for.py` | Trockenlauf der Konfiguration (Rechte, Rollen, Deckel, **Pfad-Guard**), **kein** Modellaufruf | gratis |

Der echte Lauf **erzeugt** dabei `spec.md`, `code.py` und `report.md` in diesem
Ordner — die Artefakte der drei Rollen.

---

## Tools + Permissions: der pfadgenaue Guard

Der Kern des Beispiels: die Subagenten benutzen **echte Tools** (`Read`/`Write`),
und ein **PreToolUse-Hook** setzt durch, dass sie damit **nur genau die drei
Artefakte** im aktuellen Verzeichnis anfassen. Die Aufgabe — **(a) jeden
Tool-Aufruf loggen, (b) mindestens eine gefährliche Aktion blockieren** — ist so
an einem realen Fall gezeigt.

Zwei Ebenen mit klarer Rollenteilung:

| | `can_use_tool` (`gate`) | PreToolUse-Hook (`log_and_guard`) |
|---|---|---|
| Wann | nur wenn die CLI eine **Berechtigung** anfragt | vor **jedem** Tool-Aufruf |
| Sieht die Delegation (Task/Agent)? | **nein** – auto-genehmigt | **ja** |
| Lückenloses Loggen (a) | nein | **ja** → `audit_log` + `>>> HOOK …` |
| Blockieren (b) | ja (`PermissionResultDeny`) | ja (`permissionDecision: "deny"`) |

**Warum der Hook und nicht nur `can_use_tool`:** `can_use_tool` ist ein
*Berechtigungs*-Callback. Die Subagent-Delegation wird von der CLI auto-genehmigt
und fragt gar keine Berechtigung an — also erreicht sie `gate` nie und würde nicht
geloggt. Die SDK-Warnung sagt es wörtlich: *„To gate every tool call, use a
PreToolUse hook."* Deshalb ist der Hook die eigentliche Instanz; `gate` bleibt als
zweiter Riegel.

**Die Regel** steckt in `_verletzung(tool_name, tool_input)`:

- `Agent` (Delegation) → erlaubt.
- `Read`/`Write` → nur wenn der `file_path` auf **`spec.md`, `code.py` oder
  `report.md`** im aktuellen Verzeichnis zeigt. `_erlaubter_pfad` löst den Pfad mit
  `resolve()` auf, also fällt jeder Ausbruch durch: `..`-Traversal, ein absoluter
  Fremdpfad (`/etc/passwd`, `C:\…`), eine andere Datei im selben Ordner.
- **jedes andere Werkzeug** (`Bash`, `Edit`, …) → gesperrt.

So lässt sich, wie gewünscht, **genau der Pfad prüfen** — nicht nur der Tool-Name.

**Sicherheitshinweis:** Der Guard ist der Schutz, nicht das Risiko. Er entscheidet
`deny` **bevor** das Tool läuft. Der Smoke-Test ruft die Callback-Funktionen nur
mit einem **Text** auf (z. B. einem Pfad eine Ebene höher) und prüft die
Entscheidung — **es wird keine Datei angefasst, keine Shell gestartet, nichts
ausgeführt.** Zusätzliche Riegel: `allowed_tools=[]` (nichts auto-genehmigt) und
die `disallowedTools`-Sperrliste je Subagent (`Bash`, `Edit`, `Agent`, …).

Beweis ohne Kosten:
```powershell
..\.venv\Scripts\python.exe smoke_band_for.py
```
zeigt u. a. `hook sperrt Write ausserhalb (Traversal)` und `hook sperrt Read
fremder Datei im CWD`. Im echten Lauf erscheint pro Tool-Aufruf eine
`>>> HOOK …`-Zeile (mit `agent_id`, sobald ein Subagent schreibt).

---

## Beobachtung aus echten Läufen

Live bestätigt — der eigentliche Wert der Übung:

- Der Hook **loggt jeden** Read/Write/Agent-Aufruf mit `agent_id`.
- Er **fängt Ausbrüche ab**: Agenten versuchten real, `spec.md` nach
  `C:\Users\<user>\` bzw. `~/.claude/projects/…` zu schreiben — der Guard hat es
  jedes Mal blockiert, der Agent musste nach BandFor korrigieren.
- Er **beschränkt die Delegation** auf `planner`/`generator`/`evaluator` (kein
  Ausweichen auf den eingebauten `claude`-Agenten).
- `planner` und `generator` schreiben `spec.md`/`code.py` zuverlässig.

**Grenze, bewusst so belassen:** der `evaluator` gibt sein Urteil oft nur als
Antworttext zurück und ruft `Write` **nicht** auf — für ein „Urteil" ist die
Datei aus Modellsicht kein natürliches Produkt, anders als Spec oder Code. Dann
fehlt `report.md`. Darum prüft `main()` die Artefakte am Ende **deterministisch**
(`=== Artefakte ===` mit `[OK]`/`[FEHLT]`), statt dem PASS des Modells zu glauben.
Zuverlässige Alternativen wären, den Befund im Skript zu schreiben oder
`report.md` *load-bearing* zu machen (der Orchestrator liest den Befund daraus) —
hier absichtlich nicht gemacht, weil genau dieses Modellverhalten die Lehre ist.

---

## Ausführen in der Windows-Konsole

Die Übungen laufen in einem **venv** (nicht conda). Das venv liegt eine Ebene
höher unter `Modul5BTag2\.venv` und wird von PGE und BandFor geteilt — es ist
bereits angelegt und `claude-agent-sdk` ist installiert.

Öffne eine Konsole (PowerShell **oder** Eingabeaufforderung/cmd) und wechsle in
den Ordner:

```powershell
cd C:\D\Dev\DotNet\CasAdAi\LearnFlow\Niklaus\Modul5BTag2\BandFor
```

### Variante A — venv aktivieren, dann `python`

**PowerShell:**
```powershell
..\.venv\Scripts\Activate.ps1
python smoke_band_for.py
```
> Falls PowerShell die Aktivierung wegen der Ausführungsrichtlinie blockiert,
> einmalig für die aktuelle Sitzung erlauben:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

**Eingabeaufforderung (cmd):**
```cmd
..\.venv\Scripts\activate.bat
python smoke_band_for.py
```

Aktiv erkennst du am `(.venv)` vorne im Prompt. Beenden mit `deactivate`.

### Variante B — ohne Aktivieren (venv-Python direkt aufrufen)

Funktioniert in jeder Konsole, ohne Ausführungsrichtlinie-Gefummel:

```powershell
..\.venv\Scripts\python.exe smoke_band_for.py
```

### Erwartete Ausgabe des Smoke-Tests

Eine Liste `ok …`-Zeilen und am Ende:

```
band_for-Konfiguration wie erwartet — kein Modell aufgerufen, keine Kosten.
```
Exit-Code `0` = alles gut, `1` = eine Abweichung in der Konfiguration.

---

## Der echte Lauf (kostet Geld)

`test_band_for.py` ruft das Modell (`claude-sonnet-4-6`, Deckel `$0.60`) und
braucht **Auth** — die Claude-Code-CLI und einen API-Key. Setze den Key in
derselben Konsole, bevor du startest:

**PowerShell (nur für diese Sitzung):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-…"
..\.venv\Scripts\python.exe test_band_for.py
```

**cmd (nur für diese Sitzung):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-…
..\.venv\Scripts\python.exe test_band_for.py
```
> Dauerhaft setzen ginge mit `setx ANTHROPIC_API_KEY "sk-ant-…"` — wirkt aber
> erst in **neu** geöffneten Konsolen. Den Key nicht committen.

Am Ende liest das Skript die letzte Zeile deterministisch aus und setzt den
Exit-Code: `0` bei `ERGEBNIS: PASS in Runde <n>`, `1` bei `FAIL`, `2` wenn keine
`ERGEBNIS:`-Zeile kam (dann entscheidet ein Mensch).

---

## Falls das venv mal neu aufgesetzt werden muss

Aus `Modul5BTag2` (eine Ebene über diesem Ordner):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install claude-agent-sdk
```
