"""Trockenlauf der beiden Tools — ohne Agent, ohne API-Key, ohne Kosten.

    python smoke_comment_checker.py

Prueft Rueckgabeformat, Fehlerfall und ob die Tool-Namen in `allowed_tools`
zum Schluessel in `mcp_servers` passen (ein Vertipper dort fuehrt dazu, dass
das Modell das Tool stumm nie aufruft — siehe smoke_third_agent.py).

Braucht ein Git-Repo, aber kein Modell.
"""

import asyncio
import json

import comment_checker
from comment_checker import language_signals, opts, staged_comments

TOOLS = [staged_comments, language_signals]


def call(werkzeug, **kwargs):
    return asyncio.run(werkzeug.handler(kwargs))


def text(antwort):
    return antwort["content"][0]["text"]


def main() -> None:
    # ── 1. Namen ───────────────────────────────────────────────
    key = next(iter(opts.mcp_servers))
    for w in TOOLS:
        erwartet = f"mcp__{key}__{w.name}"
        assert erwartet in opts.allowed_tools, f"{erwartet} fehlt in allowed_tools"
    assert len(opts.allowed_tools) == len(TOOLS), f"Fremdes in allowed_tools: {opts.allowed_tools}"
    print(f"Namen ok  : {len(TOOLS)} Tools unter mcp__{key}__*, sonst nichts erlaubt")

    # ── 2. staged_comments gegen das echte Repo ────────────────
    antwort = call(staged_comments)
    assert not antwort.get("is_error"), text(antwort)
    funde = json.loads(text(antwort))
    print(f"Staging   : {len(funde)} Fund(e)")
    for f in funde[:3]:
        print(f"            {f['einstufung']:11} {f['ort']}  {f['text'][:50]}")

    # ── 3. language_signals ────────────────────────────────────
    deutsch = json.loads(text(call(language_signals, text="Prueft, ob die Datei geaendert wurde")))
    englisch = json.loads(text(call(language_signals, text="Checks whether the file changed")))
    zweifel = json.loads(text(call(language_signals, text="The Rückfall applies here")))
    print(f"Signale   : deutsch={deutsch['einstufung']} englisch={englisch['einstufung']} zweifel={zweifel['einstufung']}")
    assert deutsch["einstufung"] == "sicher"
    assert englisch["einstufung"] == "unauffaellig"
    assert zweifel["einstufung"] == "verdaechtig"

    # ── 4. Fehlerfall ──────────────────────────────────────────
    leer = call(language_signals, text="")
    assert leer.get("is_error") is True, "Leerer Text muss ein Tool-Fehler sein"
    print("Fehler    : leerer Text meldet is_error")

    print(f"\nModul     : {comment_checker.__name__} importiert, ohne den Agent zu starten")
    print("Alles ok.")


if __name__ == "__main__":
    main()
