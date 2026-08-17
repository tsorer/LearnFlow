"""Dasselbe Tool wie in third_agent.py — aber eine Ebene tiefer.

third_agent.py nutzt das Claude Agent SDK: `async for msg in query(...)` — die
Agent-Schleife ist fertig eingebaut. Hier gibt es kein SDK. Wir sprechen über
LiteLLM direkt mit dem Modell (OpenAI-Interface, wie im LearnFlow-Backend nach
ADR-004) und schreiben die Schleife selbst. Das ist der ganze Unterschied
zwischen den beiden Dateien:

    third_agent.py    async for msg in query(...)      ← SDK hält die Schleife
    fourth_agent.py   while turn < MAX_TURNS: ...      ← wir halten die Schleife

Identisch bleibt: confidence.py. Dieselbe Funktion, zwei Anbindungen — genau
das ist der Grund, die Logik vom Transport zu trennen.

    python fourth_agent.py          → schwacher Fall, Tool unterdrückt
    python fourth_agent.py stark    → starker Fall, Tool gibt frei

Voraussetzung: OPENAI_API_KEY in der Umgebung (oder in einer .env neben dieser
Datei). Der Key aus LearnFlow/src/.env wird bewusst NICHT automatisch gelesen.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import litellm

from confidence import assess

# Windows-Konsole auf UTF-8 umstellen (siehe first_agent.py)
sys.stdout.reconfigure(encoding="utf-8")

MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
MAX_TURNS = 5


# ── Schritt 1: Tool-Schema in OpenAI-Form ──────────────────────
# Beim SDK genügte @tool(name, beschreibung, {"c": float}) — das Schema wurde
# daraus generiert. Hier schreiben wir es von Hand aus, weil genau das über die
# Leitung geht. "description" ist wieder der Teil, der das MODELL steuert.

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "confidence_score",
            "description": (
                "Beurteilt fail-closed, ob eine RAG-Antwort ausgeliefert werden darf. "
                "Nimmt die Retrieval-Signale entgegen und liefert Score, Band "
                "(grounded / limited / suppressed) und Unterdrückungs-Entscheid. "
                "IMMER aufrufen, bevor über die Auslieferung geurteilt wird — die "
                "Schwellenwerte dürfen nicht selbst geschätzt werden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "max_similarity": {
                        "type": "number",
                        "description": "Similarity des besten Chunks, 0.0 bis 1.0",
                    },
                    "mean_top_n_similarity": {
                        "type": "number",
                        "description": "Mittlere Similarity der Top-n Chunks, 0.0 bis 1.0",
                    },
                    "chunks_above_threshold": {
                        "type": "integer",
                        "description": "Anzahl Chunks über der Retrieval-Schwelle",
                    },
                },
                "required": [
                    "max_similarity",
                    "mean_top_n_similarity",
                    "chunks_above_threshold",
                ],
                "additionalProperties": False,
            },
        },
    }
]


# ── Schritt 2: Ausführung — das, was das SDK sonst übernimmt ────
# Das Modell liefert nur einen Namen und ein Argument-JSON. Die Zuordnung
# Name → Funktion müssen wir selbst halten; das SDK macht daraus den
# MCP-Server.

def run_confidence_score(**kwargs):
    result = assess(**kwargs)
    return {
        "score": round(result.score, 3),
        "band": result.band.value,
        "suppressed": result.suppressed,
        "reason": result.reason,
    }


HANDLERS = {"confidence_score": run_confidence_score}


def dispatch(name, arguments_json):
    """Einen Tool-Call ausführen und das Ergebnis als JSON-String liefern.

    Fehler werden zurückgemeldet statt geworfen: das Modell soll korrigieren
    können, und ein Absturz mitten in der Schleife liesse den Verlauf
    unbrauchbar zurück.
    """
    handler = HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"unbekanntes Tool: {name}"})
    try:
        arguments = json.loads(arguments_json)
        return json.dumps(handler(**arguments), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError) as exc:
        return json.dumps({"error": f"ungültige Parameter: {exc}"}, ensure_ascii=False)


# ── Schritt 3: Die Agent-Schleife, von Hand ────────────────────

SYSTEM_PROMPT = (
    "Du beurteilst RAG-Antworten für LearnFlow. Den Auslieferungs-Entscheid "
    "triffst du NIE selbst: rufe confidence_score auf und übernimm dessen "
    "Urteil unverändert, auch wenn dir die Zahlen anders erscheinen."
)


async def run(prompt):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    cost = 0.0

    for turn in range(1, MAX_TURNS + 1):
        response = await litellm.acompletion(
            model=MODEL, messages=messages, tools=TOOLS
        )
        try:
            cost += litellm.completion_cost(response)
        except Exception:
            # Kostenschätzung fehlt für manche Modelle — kein Grund abzubrechen.
            pass

        message = response.choices[0].message
        # Die Antwort MUSS zurück in den Verlauf, sonst weiss das Modell in der
        # nächsten Runde nichts von seinem eigenen Tool-Call.
        messages.append(json.loads(message.model_dump_json(exclude_none=True)))

        if not message.tool_calls:
            print(message.content)
            print(f"\n--- Turns: {turn} · Kosten: ${cost:.4f} ---")
            return

        for call in message.tool_calls:
            print(f">>> TOOL-CALL: {call.function.name}  Input: {call.function.arguments}")
            content = dispatch(call.function.name, call.function.arguments)
            print(f"<<< TOOL-RESULT: {content}")
            # Rolle "tool" + tool_call_id: so ordnet das Modell das Ergebnis
            # seinem Aufruf zu. Beim Anthropic-Protokoll wäre das stattdessen
            # ein tool_result-Block in einer User-Nachricht.
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": content}
            )

    print(f"Abbruch: MAX_TURNS ({MAX_TURNS}) erreicht · Kosten: ${cost:.4f}")


# ── Schritt 4: Dieselben zwei Fälle wie in third_agent.py ──────
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


def load_local_env():
    """Optional eine .env NEBEN dieser Datei laden — nicht die von LearnFlow."""
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


if __name__ == "__main__":
    load_local_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY fehlt. Im Anaconda-Prompt setzen:\n"
            "    set OPENAI_API_KEY=sk-...\n"
            "oder eine .env neben diese Datei legen. Der Key steht bereits in "
            "LearnFlow/src/.env — dort abschreiben, nicht committen."
        )

    case = sys.argv[1] if len(sys.argv) > 1 else "schwach"
    if case not in PROMPTS:
        raise SystemExit(f"Unbekannter Fall {case!r} — erlaubt: {', '.join(PROMPTS)}")

    print(f"── Fall: {case} · Modell: {MODEL} · Schleife: handgeschrieben ──")
    asyncio.run(run(PROMPTS[case]))
