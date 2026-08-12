"""Zwei Tools an EINEM In-Process-MCP-Server.

`second_agent.py` (celsius_to_f) und `my_agent.py` (gold_lint) hatten je einen
eigenen Server. Hier hängen beide Tools an derselben `create_sdk_mcp_server`-
Instanz: die Liste `tools=[...]` nimmt beliebig viele Tools, und der
Server-Schlüssel aus `mcp_servers` wird zum gemeinsamen Präfix —

    mcp__learnflow__celsius_to_f
    mcp__learnflow__gold_lint

Der didaktische Punkt: der Agent bekommt beide Beschreibungen zu sehen und
entscheidet pro Teilaufgabe selbst, welches Tool passt. Der Prompt unten stellt
darum bewusst zwei unzusammenhängende Aufgaben.

Start aus dem Anaconda Prompt (conda env "adai", ANTHROPIC_API_KEY gesetzt):

    python Artefakten/Modul5BTag1/combined_agent.py
"""

import asyncio
import sys
from collections import Counter
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

from gold_lint import format_report, lint_dataset, parse_entries

# Windows-Konsole auf UTF-8 umstellen (siehe first_agent.py)
sys.stdout.reconfigure(encoding="utf-8")

# Artefakten/Modul5BTag1/combined_agent.py -> Repo-Wurzel, dort liegt CLAUDE.md
REPO_ROOT = Path(__file__).resolve().parents[2]

SERVER_KEY = "learnflow"
DATASET = "LearningCorpus/Eval-Gold-Dataset-Frank.md"


# ── Tool 1: aus second_agent.py ────────────────────────────────

@tool("celsius_to_f", "Rechnet Celsius in Fahrenheit um", {"c": float})
async def celsius_to_f(args):
    result = args["c"] * 9 / 5 + 32
    return {"content": [{"type": "text", "text": str(result)}]}


# ── Tool 2: aus my_agent.py ────────────────────────────────────
# Die Beschreibung ist das, woran das Modell entscheidet, ob es das Tool
# aufruft — sie nennt darum Format (YAML) und Zweck (ADR-009-Schema).

@tool(
    "gold_lint",
    "Prüft Einträge des LearnFlow Gold-Eval-Datasets gegen das ADR-009-Schema. "
    "Eingabe ist der YAML-Teil der Dataset-Datei (eine Liste von Einträgen mit "
    "id/category/question/expected_refusal/...). Liefert pro Eintrag die "
    "Regelverstösse sowie dateiweite Befunde (doppelte IDs, Kategorie-Verteilung, Umfang).",
    {"entry_yaml": str},
)
async def gold_lint(args):
    try:
        entries = parse_entries(args["entry_yaml"])
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"FEHLER: {exc}"}]}

    if not entries:
        return {"content": [{"type": "text", "text": "Keine Einträge im übergebenen YAML gefunden."}]}

    report = format_report(lint_dataset(entries))
    return {"content": [{"type": "text", "text": report}]}


# ── Ein Server für beide Tools ─────────────────────────────────
learnflow = create_sdk_mcp_server(
    name=SERVER_KEY,
    version="1.0.0",
    tools=[celsius_to_f, gold_lint],
)

# Der Schlüssel in mcp_servers bildet das Präfix — beide Tools tragen ihn.
TOOL_NAMES = [f"mcp__{SERVER_KEY}__{name}" for name in ("celsius_to_f", "gold_lint")]


# ── Guardrails wie in my_agent.py ──────────────────────────────
opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",          # explizit, sonst greift ein teurerer Default
    cwd=str(REPO_ROOT),                 # damit relative Pfade und CLAUDE.md passen
    system_prompt={"type": "preset", "preset": "claude_code"},
    mcp_servers={SERVER_KEY: learnflow},
    effort="low",
    thinking={"type": "disabled"},	
    tools=["Read"],                     # Grundsätzlich erlaubt  
    allowed_tools=[*TOOL_NAMES, "Read"],# Ausführen ohne Nachfrage
    permission_mode="default",          # kein Schreibzugriff, nichts wird bestätigt-übersprungen
    max_turns=10,                       # Schleifen-Grenze
    max_budget_usd=0.50,                # Kosten-Grenze
)

# Zwei unzusammenhängende Aufgaben: nur wenn der Agent pro Teilaufgabe das
# richtige Tool wählt, tauchen unten beide Tool-Namen im Stream auf.
PROMPT = f"""Zwei Aufgaben, nutze für jede das passende Tool:

1. Wie viel Grad Celsius ind 75 Grad Fahrenheit?
2. Was steht in ADR-009?
"""

PROMPT2 = f"""Zwei Aufgaben, nutze für jede das passende Tool:

1. Wie viel Grad Celsius ind 75 Grad Fahrenheit?
2. Lies die Datei {DATASET} und übergib den kompletten YAML-Block aus dieser
   Datei an dein Tool gold_lint.

Fasse danach in maximal fünf Sätzen zusammen: das Umrechnungsergebnis, wie viele
Dataset-Einträge ohne Befund sind, welcher Regelverstoss am häufigsten vorkommt
und was als Erstes korrigiert werden müsste. Erfinde keine Befunde, die das Tool
nicht gemeldet hat."""


async def main():
    calls: Counter[str] = Counter()

    async for msg in query(prompt=PROMPT, options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    calls[block.name] += 1
                    # Input gekürzt — sonst steht das halbe Dataset in der Konsole
                    print(f">>> TOOL-CALL: {block.name}  Input: {_shorten(block.input)}")
                elif isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(msg, ResultMessage):
            cost = msg.total_cost_usd or 0.0
            used = ", ".join(f"{name} ×{count}" for name, count in sorted(calls.items())) or "keine"
            print(f"\n--- Tool-Aufrufe: {used}")
            print(f"--- Turns: {msg.num_turns} · Kosten: ${cost:.4f} ---")


def _shorten(value, limit: int = 120) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else f"{text[:limit]}… ({len(text)} Zeichen)"


asyncio.run(main())
