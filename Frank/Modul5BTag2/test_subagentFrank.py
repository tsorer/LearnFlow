"""Praxis-Test 1 (Tag 2): Delegiert der Haupt-Agent an den Subagent?
Ausführen im Ordner mit check_encoding.py. Erwartung: im Stream taucht
ein Task-/Subagent-Aufruf auf, dann das Encoding-Ergebnis vom encodingVerifier."""
import asyncio, sys
from pathlib import Path
from claude_agent_sdk import (
    query, ClaudeAgentOptions, AgentDefinition,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage,
)
sys.stdout.reconfigure(encoding="utf-8")

# Arbeitsverzeichnis = Ordner dieses Skripts. Damit sehen Haupt-Agent und
# Subagent nur dieses Verzeichnis, und check_encoding.py prüft genau die
# nicht committeten Dateien darunter.
HERE = Path(__file__).resolve().parent

encodingVerifier = AgentDefinition(
    description="Prüft das Encoding der noch nicht committeten Dateien. Nutze IMMER, wenn Code committed werden soll",
    prompt=(
        "Du prüfst Datei-Encodings. Führe dafür python check_encoding.py "
        "Das Skript liegt im Arbeitsverzeichnis, ermittelt die noch nicht "
        "committeten Dateien selbst und konvertiert sie bei Bedarf nach UTF-8 ohne BOM. "
        "Berichte danach: wie viele Dateien geprüft wurden, welche geändert "
        "wurden und ob der Exit-Code 0 war."
    ),
    #prompt=(
    #    "Du prüfst Datei-Encodings. Führe dafür python check_encoding.py "
    #    "Das Skript liegt im Arbeitsverzeichnis, ermittelt die noch nicht "
    #    "committeten Dateien selbst und konvertiert sie bei Bedarf nach UTF-8 "
    #    "ohne BOM. Schreibe kein eigenes Skript und ändere keine Datei von Hand. "
    #    "Berichte danach: wie viele Dateien geprüft wurden, welche geändert "
    #    "wurden und ob der Exit-Code 0 war."
    #),
    tools=["Bash", "Read"],
    model="haiku",   # Billig-Modell für die Routine-Rolle
)

opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    cwd=str(HERE),
    agents={"encodingVerifier": encodingVerifier},
    tools=["Read", "Grep", "Bash", "Task", "Agent"],
    allowed_tools=[
        "Read", "Grep", "Task", "Agent",
        "Bash(python check_encoding.py)",
        "Bash(git status:*)", "Bash(git diff:*)",
        #"Bash(git add:*)", "Bash(git commit:*)",
    ],
    disallowed_tools=["Bash(git push:*)"],
    max_turns=15,
    max_budget_usd=0.50,
)

async def main():
    async for msg in query(
        prompt="Prüfe das Encoding der neuen Dateien",
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
