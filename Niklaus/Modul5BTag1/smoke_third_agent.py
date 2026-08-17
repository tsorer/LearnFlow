"""Trockenlauf des Tool-Wrappers — ohne Agent, ohne API-Key, ohne Kosten.

    python smoke_third_agent.py

Prüft, was am Wrapper schiefgehen kann, bevor man Geld für einen Agent-Lauf
ausgibt: Handler-Rückgabeformat, Fehlerfall, und ob der Name in `allowed_tools`
wirklich zum Schlüssel in `mcp_servers` passt (ein Vertipper dort führt dazu,
dass das Modell das Tool stumm nie aufruft).
"""

import asyncio
import json

import third_agent
from third_agent import confidence_score, opts


def call(**kwargs):
    """Den Handler hinter dem @tool-Dekorator direkt aufrufen."""
    return asyncio.run(confidence_score.handler(kwargs))


def main():
    weak = call(max_similarity=0.42, mean_top_n_similarity=0.31, chunks_above_threshold=2)
    strong = call(max_similarity=0.92, mean_top_n_similarity=0.85, chunks_above_threshold=6)
    broken = call(max_similarity=0.42)

    print("schwach :", weak["content"][0]["text"])
    print("stark   :", strong["content"][0]["text"])
    print("kaputt  :", broken["content"][0]["text"], "| is_error =", broken.get("is_error"))

    assert json.loads(weak["content"][0]["text"])["suppressed"] is True
    assert json.loads(strong["content"][0]["text"])["band"] == "grounded"
    assert broken.get("is_error") is True

    server_key = next(iter(opts.mcp_servers))
    expected = f"mcp__{server_key}__{confidence_score.name}"
    assert expected in opts.allowed_tools, (
        f"allowed_tools enthält {opts.allowed_tools}, erwartet wäre {expected}"
    )
    print("\nTool-Name :", expected)
    print("Modul     :", third_agent.__name__, "- importiert, ohne den Agent zu starten")
    print("\nAlles ok.")


if __name__ == "__main__":
    main()
