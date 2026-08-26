"""Praxis-Test 2 (Tag 2), eigenes Feature: Konfidenz-Band aus dem Sprint-Backlog.

    python test_band_for.py

Gewaehltes Feature: band_for(score, medium, high) aus T-23 / ADR-008
(src/backend/app/services/confidence.py) — die Funktion, die einen
Konfidenz-Score in 'hoch' / 'mittel' / 'niedrig' einordnet.

Gleiche Idee wie im PGE-Muster: EIN Lauf, ein Orchestrator, der an drei
Spezialisten delegiert — planner -> generator -> evaluator. Reihenfolge und
Abbruch stehen im Prompt, als Gegengewicht harte Deckel und eine
deterministische Auswertung am Schluss (Python liest die letzte Zeile).

Echte Tools unter echten Permissions: jede Rolle schreibt ihr Ergebnis als
Datei ins aktuelle Verzeichnis (planner -> spec.md, generator -> code.py,
evaluator -> report.md). Der PreToolUse-Hook loggt jeden Aufruf und laesst
Read/Write NUR auf genau diese drei Pfade zu — jeder andere Pfad oder jedes
andere Werkzeug (Bash, Edit, ...) wird gesperrt (siehe _verletzung).

Warum band_for ein gutes Beispiel ist: reine Funktion, keine I/O, und die
Grenzfaelle sind anschaulich und mit Zahlen pruefbar —
  - Score genau auf `high`     -> gehoert ins hoehere Band ('hoch'), weil `>=`
  - Score genau auf `medium`   -> 'mittel', ebenfalls `>=`
  - Score unter `medium`       -> 'niedrig'
  - `medium == high`           -> das Mittelband faellt weg, `high` zuerst
                                  gepruaeft (sonst waere ein Score doppeldeutig)
"""

import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
    ToolUseBlock,
    query,
)

sys.stdout.reconfigure(encoding="utf-8")

AUFGABE = (
    "Eine Funktion band_for(score: float, medium: float, high: float) -> str, die "
    "einen Konfidenz-Score in eines der Baender 'hoch', 'mittel' oder 'niedrig' "
    "einordnet (ADR-008)."
)

# ── Artefakte: jede Rolle schreibt ihr Ergebnis als Datei ──────
# Der eigentliche Zweck dieses Beispiels: echte Tools (Read/Write) unter echten
# Permissions. Der Hook prueft pfadgenau, dass NUR diese drei Dateien im
# aktuellen Verzeichnis gelesen/geschrieben werden — alles andere wird gesperrt.
CWD = Path(__file__).resolve().parent
ARTEFAKTE = {
    "planner": "spec.md",      # die Spec
    "generator": "code.py",    # die Implementierung
    "evaluator": "report.md",  # der Pruefbericht
}
ERLAUBTE_PFADE = {(CWD / name).resolve() for name in ARTEFAKTE.values()}

# Die einzigen Subagenten, an die delegiert werden darf. Der Orchestrator darf
# NICHT auf einen eingebauten Typ (z.B. `claude`, der alle Tools haette)
# ausweichen — der Hook sperrt jede andere Delegation.
ROLLEN = tuple(ARTEFAKTE)  # ("planner", "generator", "evaluator")

# Die einzigen eingebauten Tools, die ein Subagent hier braucht. Alles andere
# (Bash, Edit, ...) ist in dieser Pipeline eine gefaehrliche Aktion.
DATEI_TOOLS = {"Read", "Write"}

# Sperrliste je Subagent: alles ausser den Datei-Tools, die die Rolle per
# `tools=` gezielt bekommt. Edit ist gesperrt (es wird geschrieben, nicht
# in-place editiert), Agent auch, damit kein Subagent weiterdelegiert.
SUB_DISALLOW = ["Bash", "bash", "Edit", "MultiEdit", "NotebookEdit", "Grep", "Glob", "Agent"]

# Absolute Pfade der Artefakte — direkt in die Subagent-Prompts gesetzt. Grund:
# ein Subagent laeuft nicht zwingend im CWD, ein relativer Name ("spec.md")
# landete sonst im CLI-Projektordner (~/.claude/projects/...) und wuerde vom Hook
# als Pfad ausserhalb der Artefakte geblockt. Mit dem absoluten Pfad schreibt
# jede Rolle sofort an die richtige, erlaubte Stelle.
SPEC_PATH = str(CWD / "spec.md")
CODE_PATH = str(CWD / "code.py")
REPORT_PATH = str(CWD / "report.md")


# ── Sicherheits-Callbacks: Audit + pfadgenaue Sperre ───────────
# Zwei Aufgaben: (a) JEDEN Tool-Aufruf protokollieren, (b) gefaehrliche Aktionen
# sperren. "Gefaehrlich" heisst hier konkret: ein anderes Werkzeug als Read/Write,
# oder ein Read/Write auf einen Pfad ausserhalb der drei Artefakte.
#
# In dieser SDK-Version genuegt der String-`query()` unten: das SDK faehrt intern
# immer Streaming und wickelt die Permissions ueber das Control-Protokoll ab.

# Jeder Aufruf landet hier: (tool_name, gekuerzte Eingabe, agent_id). Am Ende des
# Laufs als Audit ausgegeben — der Beweis fuer (a).
audit_log: list[tuple[str, str, str | None]] = []


def _erlaubter_pfad(roh: str) -> bool:
    """True, wenn `roh` genau auf eines der drei Artefakte im CWD zeigt.

    resolve() loest '..' und relative Pfade auf, so faellt ein Ausbruchsversuch
    ('../../etc/passwd', ein absoluter Fremdpfad) hier zuverlaessig durch.
    """
    if not roh:
        return False
    p = Path(roh)
    if not p.is_absolute():
        p = CWD / p
    try:
        return p.resolve() in ERLAUBTE_PFADE
    except (OSError, RuntimeError):
        return False


def _verletzung(tool_name: str, tool_input: dict) -> str | None:
    """Begruendung, wenn dieser Aufruf gesperrt gehoert — sonst None.

    Regel: die Delegation (`Agent`) nur an unsere drei Rollen; Read/Write nur auf
    die drei Artefakt-Pfade; jedes andere Werkzeug ist in dieser Pipeline verboten.
    """
    if tool_name == "Agent":
        ziel = str(tool_input.get("subagent_type", ""))
        if ziel not in ROLLEN:
            return f"Delegation an unerlaubten Subagenten: {ziel!r}"
        return None
    if tool_name in DATEI_TOOLS:
        roh = str(tool_input.get("file_path", ""))
        if not _erlaubter_pfad(roh):
            return f"Pfad ausserhalb der erlaubten Artefakte: {roh!r}"
        return None
    return f"Werkzeug in dieser Pipeline nicht erlaubt: {tool_name}"


# ── (1) can_use_tool: die PERMISSION-Ebene ─────────────────────
# Wird NUR gefragt, wenn die CLI fuer ein Tool eine Berechtigung einholt. Tools,
# die sie ohnehin freigibt — die Subagent-Delegation (Task/Agent) etwa — laufen
# daran vorbei: dieser Callback sieht sie NICHT. Deshalb taugt can_use_tool zum
# Sperren, aber nicht zum lueckenlosen Mitschreiben. Bleibt als zweiter Riegel.
async def gate(
    tool_name: str, input_data: dict, context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    grund = _verletzung(tool_name, input_data)
    if grund:
        print(f"    !!! BLOCKIERT (can_use_tool): {tool_name} — {grund}")
        return PermissionResultDeny(message=f"{tool_name} blockiert: {grund}")
    return PermissionResultAllow()


# ── (2) PreToolUse-Hook: die LIFECYCLE-Ebene ───────────────────
# Feuert vor JEDEM Tool-Aufruf — auch der Delegation. Das ist der Mechanismus
# fuers Audit (a) und die eigentliche Sperre (b); die SDK-Doku nennt ihn
# ausdruecklich, um "jeden Tool-Aufruf zu gaten".
#
# Der Hook entscheidet EXPLIZIT allow/deny, statt mit '{}' durchzuwinken: nur so
# wird ein erlaubter Subagent-Write deterministisch genehmigt (bei allowed_tools=[]
# darf man sich nicht auf einen CLI-Default verlassen), und nur so ist die Sperre
# unabhaengig von der Reihenfolge der Permission-Ebenen.
async def log_and_guard(input_data: dict, tool_use_id: str | None, context: dict) -> dict:
    tool_name = input_data.get("tool_name", "?")
    tool_input = input_data.get("tool_input", {}) or {}
    agent_id = input_data.get("agent_id")  # None auf dem Haupt-Thread (Orchestrator)
    audit_log.append((tool_name, str(tool_input)[:80], agent_id))
    print(f">>> HOOK  {agent_id or 'orchestrator'}: {tool_name}  {str(tool_input)[:80]}")

    grund = _verletzung(tool_name, tool_input)
    if grund:
        print(f"    !!! BLOCKIERT (PreToolUse): {tool_name} — {grund}")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": grund,
            }
        }
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }


# ── Die drei Spezialisten ──────────────────────────────────────
# `description` steuert die AUSWAHL durch den Orchestrator,
# `prompt` steuert das VERHALTEN, sobald der Subagent laeuft.

PLANNER = AgentDefinition(
    description=(
        "Zerlegt eine Programmieraufgabe in eine knappe Spec. IMMER als Erstes "
        "nutzen, bevor Code entsteht."
    ),
    # system_prompt der Rolle (1-2 Saetze) — die Abgabe der Uebung:
    prompt=(
        "Du bist Planner. Zerlege die Aufgabe band_for(score, medium, high) in eine "
        f"knappe Spec und schreibe sie mit Write nach genau diesem Pfad: {SPEC_PATH}. "
        "Inhalt: Inputs, Output ('hoch'/'mittel'/'niedrig') und die Grenzfaelle mit "
        "konkreten Zahlen und erwartetem Band — vor allem Score genau auf `medium` "
        "bzw. `high` (gehoert ins hoehere Band) und `medium == high`. Kein Code, nur "
        "was gelten soll."
    ),
    # Nur Write: der Planner legt spec.md an und liest nichts. Der Pfad wird
    # zusaetzlich vom Hook durchgesetzt.
    tools=["Write"],
    disallowedTools=SUB_DISALLOW,
    skills=[],
    model="sonnet",
    maxTurns=6,
)

GENERATOR = AgentDefinition(
    description=(
        "Setzt eine fertige Spec in Python um. Nutzen, sobald eine Spec "
        "vorliegt — auch fuer Nachbesserungen nach einem Evaluator-Befund."
    ),
    prompt=(
        f"Du bist Generator. Lies die Spec aus {SPEC_PATH} und setze sie exakt als "
        f"reine Python-Funktion band_for um; schreibe NUR den Code nach {CODE_PATH} "
        "(keine Erklaerung, kein Markdown). Pruefe `high` vor `medium`, damit "
        f"`medium == high` das Mittelband zusammenfallen laesst. Liegt in {REPORT_PATH} "
        "ein Evaluator-Befund vor, behebe genau das und aendere sonst nichts."
    ),
    tools=["Read", "Write"],
    disallowedTools=SUB_DISALLOW,
    skills=[],
    model="sonnet",
    maxTurns=6,
)

EVALUATOR = AgentDefinition(
    description=(
        "Prueft Code gegen eine Spec und urteilt PASS oder FAIL. Nutzen, sobald "
        "Code vorliegt — nie selbst urteilen."
    ),
    prompt=(
        f"Du bist Evaluator. Lies die Spec aus {SPEC_PATH} und den Code aus {CODE_PATH} "
        "und rechne jeden Grenzfall der Spec einzeln durch den Code (besonders die "
        "Gleichheit auf den Schwellen und `medium == high`). Deine Arbeit ist ERST "
        "erledigt, wenn du mit dem Write-Tool einen Bericht nach genau diesem absoluten "
        f"Pfad geschrieben hast: {REPORT_PATH}. Erste Zeile der Datei NUR 'PASS' oder "
        "'FAIL: <Grund>', darunter hoechstens drei Zeilen Begruendung. Rufe Write "
        "wirklich auf — ohne diese Datei gilt die Aufgabe als nicht erledigt. Antworte "
        "danach nur mit der ersten Zeile. Im Zweifel FAIL."
    ),
    tools=["Read", "Write"],
    disallowedTools=SUB_DISALLOW,
    skills=[],
    model="sonnet",
    maxTurns=6,
)

# Alle drei auf `sonnet`: Planen ist Entwurf, Generieren ist Korrektheit, und der
# Evaluator ist die Instanz, die Sicherheit liefern soll — die billigste zu
# machen waere am falschen Ende gespart.


# ── Der Orchestrator ───────────────────────────────────────────
# Er arbeitet selbst nicht. Sein ganzer Inhalt ist die Reihenfolge.

SYSTEM = """Du steuerst eine Pipeline aus drei Spezialisten.

Du arbeitest NICHT selbst: du planst nicht, schreibst keinen Code und faellst
kein Urteil. Du delegierst und reichst weiter — auch dann, wenn dir die Aufgabe
leichtfaellt.

Du delegierst AUSSCHLIESSLICH an die drei Subagenten `planner`, `generator` und
`evaluator`. Weiche NIE auf einen anderen Agenten-Typ aus (etwa `claude`), auch
nicht, wenn ein Subagent scheitert — melde in dem Fall lieber FAIL.

Ablauf (jede Rolle schreibt ihr Ergebnis als Datei):
1. `planner` beauftragen — er schreibt die Spec nach `spec.md`.
2. `generator` beauftragen — er liest `spec.md` und schreibt den Code nach `code.py`.
3. `evaluator` beauftragen — er liest `spec.md` und `code.py` und schreibt den
   Bericht nach `report.md`; sein Urteil ist PASS oder FAIL.
4. Bei FAIL: `generator` erneut beauftragen — er liest `report.md` als Befund und
   korrigiert `code.py`. Die Spec (`spec.md`) bleibt unveraendert. Danach wieder
   `evaluator`.
5. HOECHSTENS ZWEI Generator-Runden. Danach ist Schluss, auch ohne PASS.

Du selbst schreibst keine Datei und rufst kein Werkzeug ausser der Delegation auf.

Gib am Ende genau diese Zeilen aus:

ARTEFAKTE
- spec.md (Planner)
- code.py (Generator)
- report.md (Evaluator)

ERGEBNIS: PASS in Runde <n>

Die letzte Zeile ist entweder `ERGEBNIS: PASS in Runde <n>` oder
`ERGEBNIS: FAIL nach 2 Runden`. Sie wird maschinell gelesen — kein Markdown,
keine Sternchen, kein Text danach."""

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    # Anker fuer die relativen Artefakt-Pfade: Subagenten schreiben `spec.md`
    # usw. hierhin, und der Hook loest genau gegen dieses Verzeichnis auf.
    cwd=str(CWD),

    # ── Verfuegbarkeit: was es ueberhaupt gibt ──
    # Die sessionweite Basismenge der Tools. Ein Subagent kann NUR nutzen, was
    # hier drinsteht — deshalb muessen Read/Write hier stehen, obwohl nur die
    # Subagenten sie brauchen. Der Orchestrator delegiert bloss; sein Prompt und
    # der Hook halten ihn davon ab, selbst zu schreiben.
    tools=["Agent", "Read", "Write"],
    skills=[],              # None waere NICHT "aus", sondern CLI-Standard.
    setting_sources=[],     # keine CLAUDE.md, keine .claude/agents, keine settings
    strict_mcp_config=True, # kein .mcp.json aus dem Projekt

    # ── Erlaubnis: was davon ohne Rueckfrage laufen darf ──
    agents={"planner": PLANNER, "generator": GENERATOR, "evaluator": EVALUATOR},
    # Leer statt ["Agent"]: nichts wird ueber eine Allow-Regel auto-genehmigt.
    allowed_tools=[],
    # Zwei Ebenen: der PreToolUse-Hook sieht JEDEN Aufruf (auch die Delegation)
    # und ist die eigentliche Audit- und Sperr-Stelle; can_use_tool ist der
    # zweite Riegel fuer Tools, die zusaetzlich eine Berechtigung anfragen.
    hooks={"PreToolUse": [HookMatcher(hooks=[log_and_guard])]},
    can_use_tool=gate,

    system_prompt=SYSTEM,

    # Planner + 2x (Generator + Evaluator) + Schlussbericht = 6 Delegationen im
    # schlechtesten Fall. 12 laesst Luft, deckelt aber eine Endlosschleife.
    max_turns=12,
    max_budget_usd=0.60,
)


# ── Ausfuehrung ────────────────────────────────────────────────

async def main() -> int:
    letzte_zeilen: list[str] = []

    # Frischer Lauf: alte Artefakte entfernen, damit jede Rolle ihre Datei NEU
    # anlegt. Sonst muesste ein Write-Tool eine bestehende Datei erst lesen, bevor
    # es sie ueberschreibt — der Planner hat aber (bewusst) nur Write. Betrifft
    # ausschliesslich die drei eigenen Artefakte im CWD.
    for name in ARTEFAKTE.values():
        (CWD / name).unlink(missing_ok=True)

    async for msg in query(prompt=f"Aufgabe: {AUFGABE}", options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    if block.name == "Agent":
                        # Sichtbar machen, WELCHE Definition gezogen wird. Ein
                        # falscher subagent_type faellt sonst nicht auf.
                        ziel = block.input.get("subagent_type")
                        print(f"\n>>> DELEGIERT an: {ziel!r}")
                    else:
                        print(f"\n>>> TOOL: {block.name}")
                elif isinstance(block, TextBlock):
                    print(block.text)
                    letzte_zeilen.append(block.text)
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Turns: {msg.num_turns} · Kosten: ${msg.total_cost_usd:.4f} ---")

    # ── Tool-Audit aus dem PreToolUse-Hook (Aufgabe a) ──
    print(f"\n=== Tool-Audit: {len(audit_log)} Aufruf(e) ===")
    for name, arg, agent_id in audit_log:
        print(f"  {name:8} von {agent_id or 'orchestrator':12} {arg}")

    # ── Artefakte deterministisch pruefen, statt dem PASS des Modells zu glauben ──
    # Ein Subagent kann PASS melden, ohne seine Datei geschrieben zu haben.
    print("\n=== Artefakte ===")
    for name in ARTEFAKTE.values():
        p = CWD / name
        groesse = p.stat().st_size if p.exists() else 0
        print(f"  {'[OK]   ' if p.exists() else '[FEHLT]'} {name}  ({groesse} B)")

    # Deterministische Auswertung: der Exit-Code haengt an einer gelesenen
    # Zeile, nicht am Eindruck des Fliesstexts. Faellt die Zeile aus, ist das
    # ein eigener Fehlerfall (2) und nicht stillschweigend "bestanden".
    text = "\n".join(letzte_zeilen)
    ergebnis = next(
        (z.strip() for z in reversed(text.splitlines()) if z.strip().startswith("ERGEBNIS:")),
        None,
    )
    if ergebnis is None:
        print("\n*** Kein ERGEBNIS in der Ausgabe — Mensch entscheidet ***")
        return 2
    print(f"\n*** {ergebnis} ***")
    return 0 if "PASS" in ergebnis.upper() else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
