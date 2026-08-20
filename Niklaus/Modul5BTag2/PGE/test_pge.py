"""Praxis-Test 2 (Tag 2): Planner -> Generator -> Evaluator als drei Subagenten.

    python test_pge.py

Vorher waren es drei getrennte `query()`-Aufrufe, die eine Python-Schleife
zusammengehalten hat. Jetzt ist es EIN Lauf: ein Orchestrator, der an drei
Spezialisten delegiert.

Der Unterschied ist nicht kosmetisch — er verschiebt die Kontrolle:

    vorher   Python haelt die Schleife   Reihenfolge und Abbruch sind garantiert
    jetzt    das Modell haelt sie        Reihenfolge und Abbruch stehen im Prompt

Das ist der Preis der Uebung. Als Gegengewicht bleiben harte Deckel
(`max_turns`, `max_budget_usd`, `maxTurns` je Subagent) und eine
deterministische Auswertung am Schluss: Python liest die letzte Zeile und setzt
den Exit-Code, statt dem Fliesstext zu glauben.

Minimalrechte (Lehre aus dem CommentChecker):
  - `allowed_tools` ist die ERLAUBNIS, `tools` die VERFUEGBARKEIT
  - `None` heisst bei `skills`/`setting_sources` nicht "aus", sondern "alles"
  - `agents=` ohne "Agent" in `tools` waere tote Konfiguration
Die drei Subagenten brauchen ueberhaupt kein Tool: sie denken und schreiben
Text. Deshalb `tools=[]` — und zusaetzlich eine Sperrliste.
"""

import asyncio
import sys

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

sys.stdout.reconfigure(encoding="utf-8")

AUFGABE = "Eine Funktion is_schaltjahr(jahr: int) -> bool nach gregorianischen Regeln."

# Kein Subagent braucht hier ein Werkzeug — keiner liest Dateien, keiner fuehrt
# etwas aus. Die Sperrliste steht trotzdem: `tools=[]` ist eine Positivliste,
# und im CommentChecker tauchte einmal ein `bash` auf, wo keines sein sollte.
# "Agent" ist mitgesperrt, damit kein Subagent weiterdelegiert.
KEINE_TOOLS = ["Bash", "bash", "Read", "Write", "Edit", "Grep", "Glob", "Agent"]


# ── Die drei Spezialisten ──────────────────────────────────────
# `description` steuert die AUSWAHL durch den Orchestrator,
# `prompt` steuert das VERHALTEN, sobald der Subagent laeuft.
# Zwei verschiedene Leser, zwei verschiedene Texte.

PLANNER = AgentDefinition(
    description=(
        "Zerlegt eine Programmieraufgabe in eine knappe Spec. IMMER als Erstes "
        "nutzen, bevor Code entsteht."
    ),
    prompt=(
        "Du bist Planner. Zerlege die Aufgabe in eine knappe Spec: Inputs, "
        "Outputs, Edge Cases, und je Edge Case den erwarteten Wert.\n\n"
        "Kein Code, keine Implementierungshinweise — was gelten soll, nicht wie "
        "es gebaut wird. Nenne die Faelle konkret mit Zahlen, damit spaeter "
        "pruefbar ist, ob sie erfuellt sind."
    ),
    tools=[],
    disallowedTools=KEINE_TOOLS,
    skills=[],
    model="sonnet",
    maxTurns=4,
)

GENERATOR = AgentDefinition(
    description=(
        "Setzt eine fertige Spec in Python um. Nutzen, sobald eine Spec "
        "vorliegt — auch fuer Nachbesserungen nach einem Evaluator-Befund."
    ),
    prompt=(
        "Du bist Generator. Setze die Spec exakt um: nur Python, kein "
        "Fliesstext, keine Erklaerung, kein Markdown-Rahmen.\n\n"
        "Liegt ein Evaluator-Befund bei, behebe genau das Genannte und "
        "veraendere sonst nichts. Die Spec ist verbindlich, auch wenn dir eine "
        "andere Loesung besser gefiele."
    ),
    tools=[],
    disallowedTools=KEINE_TOOLS,
    skills=[],
    model="sonnet",
    maxTurns=4,
)

EVALUATOR = AgentDefinition(
    description=(
        "Prueft Code gegen eine Spec und urteilt PASS oder FAIL. Nutzen, sobald "
        "Code vorliegt — nie selbst urteilen."
    ),
    prompt=(
        "Du bist Evaluator. Pruefe den Code gegen die Spec, Fall fuer Fall.\n\n"
        "Gehe die Edge Cases der Spec einzeln durch und rechne jeden im Kopf "
        "durch den Code. Ein Fall, den du nicht durchgerechnet hast, gilt als "
        "nicht geprueft.\n\n"
        "Erste Zeile NUR 'PASS' oder 'FAIL: <Grund>'. Danach hoechstens drei "
        "Zeilen Begruendung. Im Zweifel FAIL — ein zu Unrecht abgelehnter "
        "Entwurf kostet eine Runde, ein durchgewunkener Fehler kostet mehr."
    ),
    tools=[],
    disallowedTools=KEINE_TOOLS,
    skills=[],
    model="sonnet",
    maxTurns=4,
)

# Alle drei auf `sonnet`: anders als beim CommentChecker gibt es hier KEINE
# Routine-Rolle. Planen ist Entwurf, Generieren ist Korrektheit, und der
# Evaluator ist die Instanz, die Sicherheit liefern soll — die billigste zu
# machen waere am falschen Ende gespart. Eine kuenstliche Haiku-Rolle haette
# dem Beispiel geschmeichelt und der Sache geschadet.


# ── Der Orchestrator ───────────────────────────────────────────
# Er arbeitet selbst nicht. Sein ganzer Inhalt ist die Reihenfolge — das, was
# vorher die Python-Schleife war.

SYSTEM = """Du steuerst eine Pipeline aus drei Spezialisten.

Du arbeitest NICHT selbst: du planst nicht, schreibst keinen Code und faellst
kein Urteil. Du delegierst und reichst weiter — auch dann, wenn dir die Aufgabe
leichtfaellt.

Ablauf:
1. `planner` mit der Aufgabe beauftragen. Ergebnis ist die Spec.
2. `generator` mit der Spec beauftragen. Ergebnis ist Code.
3. `evaluator` mit Spec UND Code beauftragen. Ergebnis ist PASS oder FAIL.
4. Bei FAIL: `generator` erneut beauftragen — mit derselben Spec plus dem
   Evaluator-Befund als getrenntem Abschnitt. Die Spec selbst bleibt
   unveraendert; sie ist der Massstab und darf nicht mit Kritik vermischt
   werden. Danach wieder `evaluator`.
5. HOECHSTENS ZWEI Generator-Runden. Danach ist Schluss, auch ohne PASS.

Gib am Ende genau diese vier Abschnitte aus:

SPEC
<die Spec des Planners, unveraendert>

CODE
<der finale Code des Generators>

BEFUND
<der letzte Befund des Evaluators>

ERGEBNIS: PASS in Runde <n>

Die letzte Zeile ist entweder `ERGEBNIS: PASS in Runde <n>` oder
`ERGEBNIS: FAIL nach 2 Runden`. Sie wird maschinell gelesen — kein Markdown,
keine Sternchen, kein Text danach."""

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",

    # ── Verfuegbarkeit: was es ueberhaupt gibt ──
    tools=["Agent"],        # nur Delegation. Kein Read, kein Bash, kein Write.
    skills=[],              # None waere NICHT "aus", sondern CLI-Standard.
    setting_sources=[],     # keine CLAUDE.md, keine .claude/agents, keine settings
    strict_mcp_config=True, # kein .mcp.json aus dem Projekt

    # ── Erlaubnis: was davon ohne Rueckfrage laufen darf ──
    agents={"planner": PLANNER, "generator": GENERATOR, "evaluator": EVALUATOR},
    allowed_tools=["Agent"],

    system_prompt=SYSTEM,

    # Planner + 2x (Generator + Evaluator) + Schlussbericht = 6 Delegationen im
    # schlechtesten Fall. 12 laesst Luft, deckelt aber eine Endlosschleife.
    max_turns=12,
    # Frueher galten 0.20/0.30/0.20 je AUFRUF — bei fuenf Aufrufen also bis zu
    # $1.20, nicht die im alten Docstring behaupteten $0.50. Jetzt ist es ein
    # Lauf mit einem Deckel, und der stimmt.
    max_budget_usd=0.60,
)


# ── Ausfuehrung ────────────────────────────────────────────────

async def main() -> int:
    letzte_zeilen: list[str] = []

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
