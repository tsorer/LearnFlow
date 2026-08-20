"""Praxis-Test 1 (Tag 2): Delegiert der Haupt-Agent an den Subagent?
Ausführen im Ordner mit math_utils.py. Erwartung: im Stream taucht
ein Task-/Subagent-Aufruf auf, dann Review-Ergebnis vom reviewer."""
import asyncio, sys
from claude_agent_sdk import (
    query, ClaudeAgentOptions, AgentDefinition,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage,
)
sys.stdout.reconfigure(encoding="utf-8")

reviewer = AgentDefinition(
    description="Prüft Python-Code auf Bugs und Stilprobleme. Nutze IMMER, wenn Code reviewt werden soll.",
    prompt="Du bist ein strenger Senior-Python-Reviewer. Liste konkrete Funde mit Zeilennummern, dann ein Fazit.",
    tools=["Read", "Grep"],
    model="haiku",   # Billig-Modell für die Routine-Rolle
)

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    agents={"reviewer": reviewer},
    tools=["Read", "Grep"],
    allowed_tools=["Read", "Grep"],
    max_turns=15,
    max_budget_usd=0.50,
)

async def main():
    async for msg in query(
        prompt="Reviewe bitte math_utils.py.",
        options=opts,
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print(f">>> TOOL: {b.name}  Input: {str(b.input)[:80]}")
                elif isinstance(b, TextBlock):
                    print(b.text)
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Turns: {msg.num_turns} · Kosten: ${msg.total_cost_usd:.4f} ---")

asyncio.run(main())
