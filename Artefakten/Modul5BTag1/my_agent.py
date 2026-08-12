"""L2 + L3: eigenes Custom Tool plus Agent-Loop mit Guardrails.

Das Tool `gold_lint` prüft Einträge des Gold-Eval-Datasets (ADR-009) gegen das
Schema. Der Agent liest die Dataset-Datei selbst (Tool `Read`) und schickt den
YAML-Teil durch das Tool — so sieht man im Stream beide Bausteine zusammen-
arbeiten.

Start aus dem Anaconda Prompt (conda env "adai", ANTHROPIC_API_KEY gesetzt):

    python Artefakten/Modul5BTag1/my_agent.py
"""

import asyncio
import sys
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

# Artefakten/Modul5BTag1/my_agent.py -> Repo-Wurzel, dort liegt CLAUDE.md
REPO_ROOT = Path(__file__).resolve().parents[2]

DATASET = "LearningCorpus/Eval-Gold-Dataset-Frank.md"


# ── Schritt 1: Tool definieren ─────────────────────────────────
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


# ── Schritt 2: Tool in einen In-Process-MCP-Server packen ──────
learnflow = create_sdk_mcp_server(name="learnflow", version="1.0.0", tools=[gold_lint])


# ── Schritt 3: Guardrails setzen ───────────────────────────────
opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",          # explizit, sonst greift ein teurerer Default
    cwd=str(REPO_ROOT),                 # damit relative Pfade und CLAUDE.md passen
    system_prompt={"type": "preset", "preset": "claude_code"},
    mcp_servers={"learnflow": learnflow},
    allowed_tools=["mcp__learnflow__gold_lint", "Read"],
    permission_mode="default",          # kein Schreibzugriff, nichts wird bestätigt-übersprungen
    max_turns=10,                       # Schleifen-Grenze
    max_budget_usd=0.50,                # Kosten-Grenze
)

PROMPT = f"""Lies die Datei {DATASET} und übergib den kompletten YAML-Block aus
dieser Datei an dein Tool gold_lint. Fasse das Ergebnis danach in maximal fünf
Sätzen zusammen: wie viele Einträge sind ohne Befund, welcher Regelverstoss
kommt am häufigsten vor, und was müsste als Erstes korrigiert werden, damit das
Dataset CI-tauglich wird. Erfinde keine Befunde, die das Tool nicht gemeldet hat."""


async def main():
    async for msg in query(prompt=PROMPT, options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    # Input gekürzt — sonst steht das halbe Dataset in der Konsole
                    print(f">>> TOOL-CALL: {block.name}  Input: {_shorten(block.input)}")
                elif isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(msg, ResultMessage):
            cost = msg.total_cost_usd or 0.0
            print(f"\n--- Turns: {msg.num_turns} · Kosten: ${cost:.4f} ---")


def _shorten(value, limit: int = 120) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else f"{text[:limit]}… ({len(text)} Zeichen)"


asyncio.run(main())
