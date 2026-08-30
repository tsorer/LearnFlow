"""P -> G -> E-Loop, aber E = pytest (deterministisch) statt LLM-Subagent.

    python orchestrator_pytest.py

Unterschied zu test_band_for.py: dort haelt ein LLM-Orchestrator die Schleife und
delegiert an drei Subagenten (planner/generator/evaluator). Hier haelt PYTHON die
Schleife — nur so laesst sich der Evaluator durch einen deterministischen
pytest-Lauf ersetzen (die Uebung von Tag 1: "vorher hat eine Python-Schleife die
drei query()-Aufrufe zusammengehalten").

Ablauf:
  planner   -> schreibt spec.md            (SDK-Call, mit Hook/Permissions)
  Runde 1..2:
      generator -> schreibt code.py         (SDK-Call, bekommt bei FAIL den pytest-Output)
      verdict = pytest_evaluator("test_code.py")   # <- kein LLM, harte Wahrheit
      PASS -> fertig; FAIL -> Befund zurueck an den generator

Tools + Permissions bleiben: der PreToolUse-Hook (log_and_guard) loggt jeden
Aufruf und laesst Read/Write nur auf die Artefakt-Pfade zu (aus test_band_for
importiert, damit die Regel an einer Stelle steht).
"""

import asyncio
import os
import shutil
import subprocess
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    TextBlock,
    ToolUseBlock,
    query,
)

# Guard, Pfade und Aufgabe aus dem Original wiederverwenden — gleiche Tools +
# Permissions, nur ohne den LLM-Orchestrator obendrueber.
from test_band_for import AUFGABE, CODE_PATH, CWD, SPEC_PATH, gate, log_and_guard

sys.stdout.reconfigure(encoding="utf-8")

TEST_FILE = "test_code.py"  # das Gate: laeuft gegen das vom Generator geschriebene code.py


# ── Der pytest-Evaluator (aus der Uebung) ──────────────────────
# Warum das __pycache__-Aufraeumen? Python cached kompilierte Module; ohne
# Aufraeumen testet pytest womoeglich die ALTE Version von code.py und meldet
# PASS fuer Code, der laengst ueberschrieben wurde. PYTHONDONTWRITEBYTECODE=1 und
# -p no:cacheprovider verhindern das zusaetzlich.
def pytest_evaluator(test_file: str) -> str:
    """Exit-Code 0 = PASS, sonst FAIL mit Test-Output als Feedback."""
    shutil.rmtree(CWD / "__pycache__", ignore_errors=True)  # WICHTIG!
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-q",
         "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True, timeout=60, env=env, cwd=str(CWD),
    )
    if result.returncode == 0:
        return "PASS"
    return f"FAIL:\n{result.stdout[-800:]}"


# ── Die zwei LLM-Rollen (planner, generator) ───────────────────
# Kurze System-Prompts; der Generator wird ausdruecklich auf REINEN Code
# festgelegt (keine Tests, kein import pytest) — Tests sind ein eigener Schritt.
PLANNER_PROMPT = (
    "Du bist Planner. Zerlege die Aufgabe band_for(score, medium, high) in eine "
    f"knappe Spec und schreibe sie mit Write nach genau diesem Pfad: {SPEC_PATH}. "
    "Inputs, Output ('hoch'/'mittel'/'niedrig'), die Grenzfaelle mit konkreten "
    "Zahlen und das Verhalten bei ungueltigen Schwellen. Kein Code."
)
GENERATOR_PROMPT = (
    f"Du bist Generator. Lies die Spec aus {SPEC_PATH} und schreibe eine reine "
    f"Python-Funktion band_for mit Write nach genau diesem Pfad: {CODE_PATH}. "
    "NUR Code — keine Tests, kein 'import pytest', kein Markdown-Rahmen. Liegt "
    "unten ein pytest-Befund, behebe genau die fehlgeschlagenen Faelle und aendere "
    "sonst nichts."
)


async def run_agent(system_prompt: str, task: str, tools: list[str], label: str) -> None:
    """Ein einzelner Rollen-Lauf: eigenstaendiger query()-Aufruf mit dem Guard.

    Kein `agents=` und kein Delegations-Tool — dieser Agent IST die Rolle. Die
    Python-Schleife unten ruft ihn der Reihe nach auf.
    """
    opts = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        cwd=str(CWD),
        tools=tools,            # was diese Rolle nutzen darf (Read/Write)
        skills=[],
        setting_sources=[],
        strict_mcp_config=True,
        allowed_tools=[],       # nichts auto-genehmigt; der Hook/gate entscheidet
        hooks={"PreToolUse": [HookMatcher(hooks=[log_and_guard])]},
        can_use_tool=gate,
        system_prompt=system_prompt,
        max_turns=8,
        max_budget_usd=0.30,
    )
    print(f"\n=== {label} ===")
    async for msg in query(prompt=task, options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(f">>> TOOL: {block.name}  {str(block.input)[:80]}")


async def main() -> int:
    # Frischer Lauf: spec.md und code.py entfernen, damit wirklich neu erzeugter
    # Code getestet wird (nicht ein Rest vom letzten Lauf). test_code.py bleibt.
    for name in ("spec.md", "code.py"):
        (CWD / name).unlink(missing_ok=True)

    # 1. Planner -> spec.md
    await run_agent(PLANNER_PROMPT, f"Aufgabe: {AUFGABE}", ["Write"], "PLANNER")
    if not (CWD / "spec.md").exists():
        print("\n*** Planner hat spec.md nicht geschrieben — Abbruch. ***")
        return 2

    # 2. Generator + pytest-Evaluator, hoechstens zwei Runden
    feedback = ""
    for runde in (1, 2):
        aufgabe = f"Lies {SPEC_PATH} und schreibe {CODE_PATH}."
        if feedback:
            aufgabe += f"\n\npytest-Befund der letzten Runde (behebe genau das):\n{feedback}"
        await run_agent(GENERATOR_PROMPT, aufgabe, ["Read", "Write"], f"GENERATOR (Runde {runde})")

        print(f"\n=== EVALUATOR: pytest {TEST_FILE} (Runde {runde}) ===")
        verdict = pytest_evaluator(TEST_FILE)
        print(verdict)
        if verdict == "PASS":
            print(f"\n*** ERGEBNIS: PASS in Runde {runde} ***")
            return 0
        feedback = verdict

    print("\n*** ERGEBNIS: FAIL nach 2 Runden ***")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
