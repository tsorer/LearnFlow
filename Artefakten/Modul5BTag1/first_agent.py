import asyncio
import sys
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage

# Windows-Konsole auf UTF-8 umstellen, sonst crasht print() bei Zeichen wie ✓
sys.stdout.reconfigure(encoding="utf-8")

async def main():
    opts = ClaudeAgentOptions(
        model="claude-haiku-4-5",
        cwd=".",
        system_prompt={"type": "preset", "preset": "claude_code"},  # lädt CLAUDE.md!
	#permission-mode="plan",
        allowed_tools=["Read"],
	max_turns=10,
        max_budget_usd=0.20,
    )
    async for msg in query(
        prompt="Lies Src/backend/seed_users.py. Hält sich die Datei an unsere Projekt-Konventionen aus CLAUDE.md? Kurz begründen.",
        options=opts,
    ):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Kosten: ${msg.total_cost_usd:.4f} ---")

asyncio.run(main())
