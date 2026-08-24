"""Praxis-Test 1 (Tag 2): Delegiert der Haupt-Agent an den api-kritiker-Subagent?

Rolle: API-Kritiker fuer LearnFlow (ADR-010, API-First). Vergleicht die echte
OpenAPI-Spec (src/backend/openapi.yaml) mit einem echten Router
(src/backend/app/routers/documents.py) -- rein lesend, es wird nichts an den
LearnFlow-Dateien veraendert.

Zwei Laeufe zum Vergleich:
  1. MIT explizitem Rollennamen ("Lass den api-kritiker-Subagent ...")
  2. OHNE Rollennamen ("Pruefe bitte ...") -- gewinnt der eigene Subagent
     oder ein Built-in-Skill (z.B. code-review)?

Ausfuehren aus einem beliebigen Ordner (Pfade sind absolut):
    python subagent_api_kritiker.py [--ohne-namen]
"""
import asyncio, sys, os
from claude_agent_sdk import (
    query, ClaudeAgentOptions, AgentDefinition,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage,
)
sys.stdout.reconfigure(encoding="utf-8")

# Abo statt API-Key: ANTHROPIC_API_KEY würde sonst gewinnen
os.environ.pop("ANTHROPIC_API_KEY", None)
if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
    sys.exit("Abo-Token fehlt: claude setup-token")

REPO_ROOT = r"C:\Projekte\BFH\LearnFlow"
OPENAPI_PATH = REPO_ROOT + r"\src\backend\openapi.yaml"
ROUTER_PATH = REPO_ROOT + r"\src\backend\app\routers\documents.py"

api_kritiker = AgentDefinition(
    description=(
        "Prüft ob FastAPI-Router-Code mit der OpenAPI-Spec (openapi.yaml) übereinstimmt "
        "(ADR-010, API-First). Nutze IMMER wenn Endpoints oder openapi.yaml geprüft werden sollen."
    ),
    prompt=(
        "Du bist ein strenger API-Kritiker für ein API-First-Projekt (ADR-010). Vergleiche "
        "Router-Code gegen die OpenAPI-Spec: Pfade, Methoden, Statuscodes, Request-/Response-Felder. "
        "Liste jede Abweichung mit Zeilennummer, dann ein Fazit."
    ),
    tools=["Read", "Grep"],
    model="haiku",   # Billig-Modell für die Routine-Rolle
)

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    agents={"api-kritiker": api_kritiker},
    allowed_tools=["Read", "Grep"],
    max_turns=15,
    max_budget_usd=0.50,
)

MIT_NAMEN = (
    f"Lass den api-kritiker-Subagent {OPENAPI_PATH} gegen {ROUTER_PATH} prüfen."
)
OHNE_NAMEN = (
    f"Prüfe bitte, ob {OPENAPI_PATH} und {ROUTER_PATH} zusammenpassen."
)

async def main():
    ohne_namen = "--ohne-namen" in sys.argv
    prompt = OHNE_NAMEN if ohne_namen else MIT_NAMEN
    print(f"=== Prompt ({'ohne' if ohne_namen else 'mit'} Rollennamen) ===\n{prompt}\n")

    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print(f">>> TOOL: {b.name}  Input: {str(b.input)[:80]}")
                elif isinstance(b, TextBlock):
                    print(b.text)
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Turns: {msg.num_turns} · Kosten: ${msg.total_cost_usd:.4f} ---")

asyncio.run(main())
