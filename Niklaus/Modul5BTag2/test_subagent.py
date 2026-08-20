"""Praxis-Test 1 (Tag 2): Delegiert der Haupt-Agent an den Subagent?

Erwartung: im Stream taucht ein `Agent`-Aufruf auf — das ist das
Delegations-Tool — und dessen `subagent_type` nennt die gezogene Definition.
Steht dort `reviewer`, hat er unsere genommen; steht dort etwas anderes, hat er
einen eingebauten Typ erwischt.

Danach dürfen nur noch Read und Grep kommen: das ist die `tools`-Liste des
Subagenten, und die ist — anders als `allowed_tools` — eine echte Schranke."""
import asyncio, sys
from pathlib import Path
from claude_agent_sdk import (
    query, ClaudeAgentOptions, AgentDefinition,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage,
)
sys.stdout.reconfigure(encoding="utf-8")

# Niklaus/Modul5BTag2 -> LearnFlow (gleiches Muster wie comment_checker.py)
REPO = Path(__file__).resolve().parent.parent.parent

reviewer = AgentDefinition(
    description="Prüft Python-Code auf Bugs und Stilprobleme. Nutze IMMER, wenn Code reviewt werden soll.",
    prompt="Du bist ein strenger Senior-Python-Reviewer. Liste konkrete Funde mit Zeilennummern, dann ein Fazit.",
    tools=["Read", "Grep"],
    model="haiku",   # Billig-Modell für die Routine-Rolle
)

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    cwd=str(REPO),   # ohne das laufen relative Pfade gegen Modul5BTag2 ins Leere
    agents={"reviewer": reviewer},
    allowed_tools=["Read", "Grep"],
    disallowed_tools=["Skill"],
    max_turns=15,
    max_budget_usd=0.50,
)

async def main():
    async for msg in query(
        prompt="Reviewe bitte src/backend/app/limiter.py",
        options=opts,
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    if b.name == "Agent":
                        # Der ganze Zweck des Tests: WELCHE Definition zieht er?
                        print(f">>> TOOL: Agent")
                        print(f"    subagent_type = {b.input.get('subagent_type')!r}")
                        print(f"    description   = {b.input.get('description')!r}")
                    else:
                        print(f">>> TOOL: {b.name}  Input: {str(b.input)[:120]}")
                elif isinstance(b, TextBlock):
                    print(b.text)
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Turns: {msg.num_turns} · Kosten: ${msg.total_cost_usd:.4f} ---")

asyncio.run(main())
