"""Sessions-Demo Teil 2: NEUER Prozess, alte Session fortsetzen.
Erwartung: der Agent kennt Projektname und Stack aus Teil 1."""
import asyncio, sys
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage
sys.stdout.reconfigure(encoding="utf-8")

sid = open("session_id.txt").read().strip()
print(f"Setze Session fort: {sid}\n")

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    resume=sid,                 # <-- DER Schalter
    max_turns=3,
    max_budget_usd=0.10,
)

async def main():
    async for msg in query(
        prompt="Wie heisst mein Projekt und welchen Stack nutzt es?",
        options=opts,
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print(b.text)
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Kosten: ${msg.total_cost_usd:.4f} ---")

asyncio.run(main())
