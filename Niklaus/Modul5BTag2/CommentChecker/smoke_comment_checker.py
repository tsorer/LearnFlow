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
    # Der Haupt-Agent bekommt staged_comments und Agent, der Subagent
    # language_signals. Ein Vertipper im mcp__-Namen faellt zur Laufzeit nicht
    # auf: das Tool wird dann stumm nie aufgerufen.
    key = next(iter(opts.mcp_servers))
    voll = {w.name: f"mcp__{key}__{w.name}" for w in TOOLS}

    # `allowed_tools` gilt fuer die ganze Session, Subagent eingeschlossen.
    # Fehlt language_signals hier, darf der Uebersetzer seine Gegenprobe nicht
    # aufrufen — das kostete den ersten scharfen Lauf.
    assert set(opts.allowed_tools) == {*voll.values(), "Agent"}, \
        f"Haupt-Agent hat andere Rechte als erwartet: {opts.allowed_tools}"
    print("Namen ok  : Session erlaubt staged_comments + language_signals + Agent")

    # ── 1a. Subagent ───────────────────────────────────────────
    assert opts.agents, "kein Subagent registriert"
    assert "uebersetzer" in opts.agents, f"Subagenten: {list(opts.agents)}"
    sub = opts.agents["uebersetzer"]
    # `agents` ohne `Agent` in `tools` waere tote Konfiguration: sieht nach
    # Faehigkeit aus, ist aber unerreichbar.
    assert "Agent" in (opts.tools or []), "agents= gesetzt, aber Agent-Tool nicht verfuegbar"
    assert sub.tools == [voll["language_signals"]], f"Subagent-Tools: {sub.tools}"
    assert voll["staged_comments"] not in (sub.tools or []), \
        "Subagent kann den Staging-Bereich sehen — soll er nicht"
    assert sub.mcpServers == [key], f"Subagent kennt den Server nicht: {sub.mcpServers}"
    assert sub.model == "haiku", f"Subagent laeuft auf {sub.model}, nicht auf dem billigen Modell"
    # Sein Tool muss auch erlaubt sein, nicht nur sichtbar — sonst laeuft er in
    # die Rueckfrage und liefert ohne Gegenprobe.
    assert sub.tools[0] in opts.allowed_tools, \
        f"{sub.tools[0]} ist dem Subagenten sichtbar, aber nicht erlaubt"
    # Sperrliste: `bash` tauchte im ersten scharfen Lauf auf, obwohl `tools` es
    # nicht vorsah. Bis die Ursache geklaert ist, steht der Riegel.
    for verboten in ("Bash", "bash", "Agent"):
        assert verboten in (sub.disallowedTools or []), f"{verboten} nicht gesperrt"
    print(f"Subagent  : uebersetzer auf {sub.model}, nur {sub.tools[0].split('__')[-1]}, "
          f"{len(sub.disallowedTools)} Tools gesperrt")

    # ── 1b. Minimalrechte ──────────────────────────────────────
    # Der Docstring behauptet, das Modell bekomme kein Read und kein Bash. Das
    # haengt an vier Feldern, und ein leeres `[]` sieht aus wie ein
    # vergessenes `None` — nur bedeutet `None` bei `skills` und
    # `setting_sources` das Gegenteil: CLI-Standard, also alles. Deshalb wird
    # hier auf die leere Liste geprueft und nicht bloss auf "falsy".
    # `tools` ist wegen des Subagents nicht mehr leer — aber genau einen Eintrag
    # lang. Read, Bash und Write duerfen nicht dazukommen.
    assert opts.tools == ["Agent"], f"mehr als das Delegations-Tool: {opts.tools}"
    assert opts.skills == [], f"Skills aktiv: {opts.skills!r} (None heisst NICHT aus)"
    assert sub.skills == [], f"Subagent hat Skills: {sub.skills!r}"
    assert opts.setting_sources == [], f"laedt von der Platte: {opts.setting_sources!r}"
    assert opts.strict_mcp_config is True, "fremde MCP-Server koennen dazukommen"
    assert opts.cwd, "ohne cwd laufen Tools im Startverzeichnis"
    print("Rechte ok : tools=['Agent'] skills=[] setting_sources=[] strict_mcp_config=True")

    # ── 1c. Deckel ─────────────────────────────────────────────
    assert opts.max_turns and opts.max_turns <= 10, f"max_turns={opts.max_turns}"
    assert opts.max_budget_usd, "kein Budget-Limit gesetzt"
    assert sub.maxTurns and sub.maxTurns <= 10, f"Subagent ohne Turn-Deckel: {sub.maxTurns}"
    print(f"Deckel ok : max_turns={opts.max_turns} max_budget_usd={opts.max_budget_usd} "
          f"sub.maxTurns={sub.maxTurns}")

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
