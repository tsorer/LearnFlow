"""Sessions-Demo Teil 1: Lauf starten, session_id einfangen.
Die ID wird in session_id.txt gespeichert - session_2.py liest sie."""
import asyncio, sys
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage
sys.stdout.reconfigure(encoding="utf-8")

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    max_turns=3,
    max_budget_usd=0.10,
)

async def main():
    async for msg in query(
        prompt="Mein Projekt heisst BudgetBuddy und nutzt Spring Boot. Merk dir das — ich frage später danach.",
        options=opts,
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print(b.text)
        elif isinstance(msg, ResultMessage):
            sid = msg.session_id
            with open("session_id.txt", "w") as f:
                f.write(sid)
            print(f"\n--- session_id gespeichert: {sid} ---")
            print(f"--- Kosten: ${msg.total_cost_usd:.4f} ---")

asyncio.run(main())
