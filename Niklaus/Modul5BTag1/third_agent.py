import asyncio
import json
import sys
from typing import Annotated

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

from confidence import assess

# Windows-Konsole auf UTF-8 umstellen (siehe first_agent.py)
sys.stdout.reconfigure(encoding="utf-8")


# ── Schritt 1: Tool definieren ─────────────────────────────────
# Der Wrapper enthält bewusst KEINE Logik — nur Schema, Aufruf und
# Fehlerbehandlung. Die Berechnung steht in confidence.py und ist dort ohne
# SDK, ohne API-Key und ohne Kosten testbar (test_confidence.py).
#
# Annotated[...] hängt eine Beschreibung an einen Parameter; das Modell sieht
# sie im Schema und weiss dadurch, welchen Wert es wo einsetzen muss.

@tool(
    "confidence_score",
    "Beurteilt fail-closed, ob eine RAG-Antwort ausgeliefert werden darf. "
    "Nimmt die Retrieval-Signale entgegen und liefert Score, Band "
    "(grounded / limited / suppressed) und Unterdrückungs-Entscheid. "
    "IMMER aufrufen, bevor über die Auslieferung einer Antwort geurteilt wird — "
    "die Schwellenwerte dürfen nicht selbst geschätzt werden.",
    {
        "max_similarity": Annotated[
            float, "Similarity des besten Chunks, 0.0 bis 1.0"
        ],
        "mean_top_n_similarity": Annotated[
            float, "Mittlere Similarity der Top-n Chunks, 0.0 bis 1.0"
        ],
        "chunks_above_threshold": Annotated[
            int, "Anzahl Chunks über der Retrieval-Schwelle (Evidenz-Dichte)"
        ],
    },
)
async def confidence_score(args):
    try:
        result = assess(
            max_similarity=args["max_similarity"],
            mean_top_n_similarity=args["mean_top_n_similarity"],
            chunks_above_threshold=args["chunks_above_threshold"],
        )
    except (KeyError, TypeError) as exc:
        # Fehlende oder falsch getypte Parameter: als Tool-Fehler zurück, damit
        # das Modell korrigieren kann — statt den Agent-Loop abstürzen zu lassen.
        return {
            "content": [{"type": "text", "text": f"Ungültige Parameter: {exc}"}],
            "is_error": True,
        }

    # JSON statt Prosa: sonst interpretiert das Modell "score 0.38" frei weiter,
    # statt das Urteil zu übernehmen. Gerundet wird nur hier für die Anzeige —
    # das Band stammt aus dem ungerundeten Score.
    payload = {
        "score": round(result.score, 3),
        "band": result.band.value,
        "suppressed": result.suppressed,
        "reason": result.reason,
    }
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]
    }


# ── Schritt 2: Tool in einen In-Process-MCP-Server packen ──────
learnflow = create_sdk_mcp_server(
    name="learnflow", version="1.0.0", tools=[confidence_score]
)


# ── Schritt 3: Server anschliessen + Tool erlauben ─────────────
opts = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    mcp_servers={"learnflow": learnflow},
    #                 └── dieser Schlüssel landet im Tool-Namen:
    allowed_tools=["mcp__learnflow__confidence_score"],
    #               mcp__<schlüssel>__<tool-name>
    system_prompt=(
        "Du beurteilst RAG-Antworten für LearnFlow. Den Auslieferungs-Entscheid "
        "triffst du NIE selbst: rufe confidence_score auf und übernimm dessen "
        "Urteil unverändert, auch wenn dir die Zahlen anders erscheinen."
    ),
    max_turns=5,
    max_budget_usd=0.20,
)


# ── Schritt 4: Aufgabe stellen, die das Tool provoziert ────────
# Zwei Fälle zum Vorführen — dieselbe Frage, nur andere Retrieval-Signale:
#   python third_agent.py          → schwach, Tool unterdrückt
#   python third_agent.py stark    → stark, Tool gibt frei
PROMPTS = {
    "schwach": (
        "Das Retrieval lieferte für eine Frage: beste Similarity 0.42, "
        "mittlere Similarity der Top-5 0.31, 2 Chunks über der Schwelle. "
        "Darf die Antwort ausgeliefert werden?"
    ),
    "stark": (
        "Das Retrieval lieferte für eine Frage: beste Similarity 0.92, "
        "mittlere Similarity der Top-5 0.85, 6 Chunks über der Schwelle. "
        "Darf die Antwort ausgeliefert werden?"
    ),
}


async def main(case):
    async for msg in query(prompt=PROMPTS[case], options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    print(f">>> TOOL-CALL: {block.name}  Input: {block.input}")
                elif isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(msg, ResultMessage):
            print(f"\n--- Turns: {msg.num_turns} · Kosten: ${msg.total_cost_usd:.4f} ---")


# Anders als in first_agent.py/second_agent.py steht der Start hinter einem
# __main__-Guard: so lässt sich der Wrapper importieren und trocken prüfen
# (siehe smoke_third_agent.py), ohne einen bezahlten Agent-Lauf auszulösen.
if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "schwach"
    if case not in PROMPTS:
        raise SystemExit(f"Unbekannter Fall {case!r} — erlaubt: {', '.join(PROMPTS)}")
    print(f"── Fall: {case} ──")
    asyncio.run(main(case))
