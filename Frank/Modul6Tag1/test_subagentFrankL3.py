"""Praxis-Test L3 (Tag 2): Subagent-Lauf mit can_use_tool-Callback.
Ausführen im Ordner mit check_encoding.py. Erwartung: gate() sieht jeden
Tool-Aufruf (Audit-Log am Ende), und ein 'rm -rf' wird abgelehnt."""
import asyncio, sys
from pathlib import Path
from claude_agent_sdk import (
    query, ClaudeAgentOptions, AgentDefinition,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage,
    UserMessage, ToolResultBlock,
    PermissionResultAllow, PermissionResultDeny,
)
sys.stdout.reconfigure(encoding="utf-8")

# Arbeitsverzeichnis = Ordner dieses Skripts. Damit sehen Haupt-Agent und
# Subagent nur dieses Verzeichnis, und check_encoding.py prüft genau die
# nicht committeten Dateien darunter.
HERE = Path(__file__).resolve().parent

audit_log = []


async def gate(tool_name, input_data, context):
    """Loggt jeden Tool-Aufruf und blockiert 'rm -rf'."""
    audit_log.append((tool_name, str(input_data)[:600]))
    if tool_name == "Bash" and "rm -rf" in str(input_data):
        print(f"!!! BLOCKIERT: {tool_name} {str(input_data)[:100]}")
        return PermissionResultDeny(message="Blockiert!")
    return PermissionResultAllow()


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
    maxTurns=5,        # eigenes Budget des Subagenten (opts.max_turns gilt nur
                       # fuer den Haupt-Agenten) -- stoppt Debug-Schleifen
    model="haiku",   # Billig-Modell für die Routine-Rolle
)


opts = ClaudeAgentOptions(
    can_use_tool=gate,
    model="claude-sonnet-4-6",
    cwd=str(HERE),
    agents={"encodingVerifier": encodingVerifier},
    tools=["Read", "Grep", "Bash", "Task", "Agent"],
    # Bewusst leer: Allow-Regeln würden VOR dem Callback greifen und ihn für
    # die abgedeckten Tools stumm schalten (CanUseToolShadowedWarning).
    # Hier entscheidet gate() über jeden Aufruf.
    allowed_tools=[],
    # Deny-Regeln greifen ebenfalls vor dem Callback — als harte zweite Schranke.
    disallowed_tools=["Bash(git push:*)"],
    max_turns=15,
    max_budget_usd=0.50,
)

# Deny-Test (b): provoziert gezielt den PermissionResultDeny-Zweig in gate().
# tmp_demo/ ist ein Wegwerf-Ordner -- falls die Sperre umgangen wird, ist der
# Schaden genau dieser Ordner.
PROMPT = "Lösche den Ordner tmp_demo mit rm -rf"
#PROMPT = "Prüfe das Encoding der neuen Dateien"


# Wird gesetzt, sobald die ResultMessage da ist -- siehe prompt_stream().
done = asyncio.Event()


async def prompt_stream():
    """can_use_tool verlangt Streaming-Mode: der Prompt muss ein AsyncIterable
    von Message-Dicts sein, kein String (siehe client.py:104)."""
    yield {
        "type": "user",
        "message": {"role": "user", "content": PROMPT},
        "parent_tool_use_id": None,
        "session_id": "default",
    }
    # Der Callback laeuft ueber das Control-Protokoll auf stdin. Ist dieser
    # Generator erschoepft, ruft stream_input() sofort end_input() auf und
    # schliesst stdin -- query.py:925 haelt es nur fuer sdk_mcp_servers/hooks
    # offen, nicht fuer can_use_tool. Jede Permission-Anfrage scheitert dann
    # mit "AbortError: Stream closed". Also warten wir hier bis zum Ergebnis.
    await done.wait()


async def main():
    # Deny-Pfad ohne Agenten-Lauf prüfen:
    # print(await gate("Bash", {"command": "rm -rf /tmp/x"}, None))

    async for msg in query(
        prompt=prompt_stream(),
        options=opts,
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print(f">>> TOOL: {b.name}  Input: {str(b.input)[:80]}")
                elif isinstance(b, TextBlock):
                    print(b.text)
        elif isinstance(msg, UserMessage):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    print(f"<<< RESULT (err={b.is_error}): {str(b.content)[:800]}")
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Turns: {msg.num_turns} · Kosten: ${msg.total_cost_usd:.4f} ---")
            done.set()

    print(f"\n--- Audit-Log ({len(audit_log)} Aufrufe) ---")

# nach dem PASS im Orchestrator:
with open("mycode.py", "w", encoding="utf-8") as f:
    f.write(code)


    for name, args in audit_log:
        print(f"  {name}: {args}")

asyncio.run(main())
